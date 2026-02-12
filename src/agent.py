"""Agent creation and execution logic for TechPulse Social.

Creates a single agent with multiple tools and provides streaming execution.
Uses AzureOpenAIResponsesClient from agent-framework-core.
"""

import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from agent_framework import AgentResponseUpdate
from agent_framework.azure import AzureOpenAIResponsesClient

from src import config
from src.client import get_client
from src.prompts import SYSTEM_PROMPT
from src.tools import generate_content, generate_image, review_content

logger = logging.getLogger(__name__)

# Tool event markers (from fabric-foundry-agentic-starter)
TOOL_EVENT_START = "__TOOL_EVENT__"
TOOL_EVENT_END = "__END_TOOL_EVENT__"
REASONING_START = "__REASONING_REPLACE__"
REASONING_END = "__END_REASONING_REPLACE__"

# Reasoning throttle (only send updates every N ms to avoid flooding)
REASONING_THROTTLE_MS = 100


def create_tool_event(tool_name: str, status: str, message: str | None = None) -> str:
    """Create a JSON-formatted tool event for SSE streaming.

    Args:
        tool_name: Name of the tool (e.g., "generate_content").
        status: "started", "completed", or "error".
        message: Optional message for additional context.

    Returns:
        String with tool event markers for frontend parsing.
    """
    event = {
        "type": "tool_event",
        "tool": tool_name,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if message:
        event["message"] = message
    return f"{TOOL_EVENT_START}{json.dumps(event, ensure_ascii=False)}{TOOL_EVENT_END}"


def _build_query_with_context(
    message: str,
    platforms: list[str],
    content_type: str,
    language: str,
    history: list[dict] | None = None,
) -> str:
    """Build the full query string with context for the agent.

    Args:
        message: User's input message.
        platforms: Target platforms.
        content_type: Content type selection.
        language: Output language.
        history: Previous conversation messages for multi-turn.

    Returns:
        Formatted query string.
    """
    parts = []

    # Add conversation history if available
    if history:
        history_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in history[-6:]
        )
        parts.append(f"Previous conversation:\n{history_text}\n")

    # Build the current request
    platform_list = ", ".join(platforms)
    parts.append(
        f"Create social media content for the following:\n"
        f"- Topic: {message}\n"
        f"- Platforms: {platform_list}\n"
        f"- Content type: {content_type}\n"
        f"- Language: {language}\n"
    )

    return "\n".join(parts)


async def run_agent_stream(
    message: str,
    platforms: list[str],
    content_type: str,
    language: str,
    history: list[dict] | None = None,
    reasoning_effort: str = "medium",
    reasoning_summary: str = "auto",
) -> AsyncIterator[str]:
    """Execute the agent and yield SSE-formatted events.

    Streams reasoning tokens, tool events, and text content via markers:
    - __REASONING_REPLACE__...__END_REASONING_REPLACE__ for thinking
    - __TOOL_EVENT__...__END_TOOL_EVENT__ for tool usage
    - Plain text for content

    Args:
        message: User's input message.
        platforms: Target platforms.
        content_type: Content type.
        language: Output language.
        history: Conversation history for multi-turn.
        reasoning_effort: GPT-5 reasoning depth (low/medium/high).
        reasoning_summary: Thinking display mode (off/auto/concise/detailed).

    Yields:
        SSE-formatted strings for each event type.
    """
    client = get_client()

    # Get hosted tools
    web_search_tool = AzureOpenAIResponsesClient.get_web_search_tool()

    # Build tool list
    tools = [web_search_tool, generate_content, review_content, generate_image]

    # Add file_search if Vector Store is configured
    vector_store_id = config.VECTOR_STORE_ID
    if vector_store_id:
        file_search_tool = AzureOpenAIResponsesClient.get_file_search_tool(
            vector_store_ids=[vector_store_id],
        )
        tools.append(file_search_tool)
        logger.info("File search tool enabled (vector_store_id=%s)", vector_store_id)
    else:
        logger.warning(
            "VECTOR_STORE_ID not set — file_search tool disabled. "
            "Run vector_store.py to create one."
        )

    # Add Foundry IQ Agentic Retrieval if configured
    from src.agentic_retrieval import is_configured as _iq_configured
    from src.agentic_retrieval import search_knowledge_base

    if _iq_configured():
        tools.append(search_knowledge_base)
        logger.info(
            "Foundry IQ tool enabled (endpoint=%s, kb=%s)",
            config.AI_SEARCH_ENDPOINT,
            config.AI_SEARCH_KNOWLEDGE_BASE_NAME,
        )
    else:
        logger.info("Foundry IQ not configured — search_knowledge_base tool disabled")

    # Build reasoning options for gpt-5.2
    reasoning_opts: dict = {}
    if reasoning_effort and reasoning_effort != "off":
        reasoning_opts["effort"] = reasoning_effort
    if reasoning_summary and reasoning_summary != "off":
        reasoning_opts["summary"] = reasoning_summary

    default_options: dict = {}
    if reasoning_opts:
        default_options["reasoning"] = reasoning_opts

    # Create agent with all tools (hosted + custom @tool)
    agent = client.as_agent(
        name="techpulse_social_agent",
        instructions=SYSTEM_PROMPT,
        tools=tools,
        default_options=default_options if default_options else None,
    )

    # Build the full query
    query = _build_query_with_context(
        message, platforms, content_type, language, history
    )
    logger.info("Agent processing: %s... (platforms=%s)", message[:80], platforms)

    # Accumulate reasoning text (SDK sends deltas; we accumulate + REPLACE)
    accumulated_reasoning = ""
    import time

    last_reasoning_send = 0.0

    def _should_send_reasoning() -> bool:
        nonlocal last_reasoning_send
        now = time.time() * 1000
        if now - last_reasoning_send >= REASONING_THROTTLE_MS:
            last_reasoning_send = now
            return True
        return False

    # Track tool calls already emitted to avoid duplicates
    # (each streaming update re-sends the same function_call content)
    emitted_tool_starts: set[str] = set()
    emitted_tool_ends: set[str] = set()
    # Map call_id → tool_name (function_result may not carry the name)
    call_id_to_name: dict[str, str] = {}

    try:
        # stream=True returns ResponseStream[AgentResponseUpdate, AgentResponse]
        stream = agent.run(query, stream=True)

        async for update in stream:
            # Each update is an AgentResponseUpdate with .contents list
            if not isinstance(update, AgentResponseUpdate):
                # Fallback: yield as text
                text = str(update)
                if text:
                    yield text
                continue

            # Process each Content item in the update
            for content in update.contents or []:
                ct = getattr(content, "type", None)
                logger.debug(
                    "Content type=%s, has_text=%s, text_preview=%s",
                    ct,
                    bool(getattr(content, "text", None)),
                    (getattr(content, "text", "") or "")[:80],
                )

                if ct == "text_reasoning" and content.text:
                    # GPT-5 reasoning token — accumulate and throttle
                    if accumulated_reasoning and content.text.startswith(
                        accumulated_reasoning
                    ):
                        # SDK sent cumulative text — replace
                        accumulated_reasoning = content.text
                    elif accumulated_reasoning.endswith(content.text):
                        # Duplicate delta — ignore
                        pass
                    else:
                        # True delta — append
                        accumulated_reasoning += content.text

                    if _should_send_reasoning():
                        yield (
                            f"{REASONING_START}{accumulated_reasoning}{REASONING_END}"
                        )

                elif ct == "function_call":
                    # Tool being invoked — emit only once per call_id
                    tool_name = getattr(content, "name", None) or "unknown_tool"
                    call_id = getattr(content, "call_id", None) or tool_name
                    # Remember for later function_result lookup
                    if tool_name != "unknown_tool":
                        call_id_to_name[call_id] = tool_name
                    if call_id not in emitted_tool_starts:
                        emitted_tool_starts.add(call_id)
                        yield create_tool_event(tool_name, "started")

                elif ct == "function_result":
                    # Tool returned result — emit only once per call_id
                    call_id = getattr(content, "call_id", None) or ""
                    # Resolve name from call_id map (function_result often lacks .name)
                    tool_name = (
                        getattr(content, "name", None)
                        or call_id_to_name.get(call_id)
                        or "unknown_tool"
                    )
                    if call_id and call_id not in emitted_tool_ends:
                        emitted_tool_ends.add(call_id)
                        yield create_tool_event(tool_name, "completed")

                elif ct == "text" and content.text:
                    # Regular text output
                    yield content.text

            # Fallback: if update has .text but no contents processed
            if not update.contents and update.text:
                yield update.text

        # Send final accumulated reasoning
        if accumulated_reasoning:
            yield (f"{REASONING_START}{accumulated_reasoning}{REASONING_END}")

    except Exception as e:
        logger.error("Agent execution error: %s", e, exc_info=True)
        error_event = {
            "type": "error",
            "message": str(e),
        }
        yield f"data: {json.dumps(error_event)}\n\n"
        raise
