"""Agent creation and execution logic for TechPulse Social.

Creates a single agent with multiple tools and provides streaming execution.
Uses AzureOpenAIResponsesClient from agent-framework-core.
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from agent_framework import AgentResponseUpdate
from agent_framework.azure import AzureOpenAIResponsesClient

from src import config
from src.agentic_retrieval import is_configured as _iq_configured
from src.agentic_retrieval import search_knowledge_base
from src.client import get_client
from src.prompts import get_system_prompt
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
    ab_mode: bool = False,
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
        ab_mode: If True, generate two content variants for A/B comparison.

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

    # Add MCP tool (Microsoft Learn documentation)
    if config.MCP_SERVER_URL:
        mcp_tool = AzureOpenAIResponsesClient.get_mcp_tool(
            name="microsoft_learn",
            url=config.MCP_SERVER_URL,
            description=(
                "Search and retrieve official Microsoft Learn documentation, "
                "code samples, and technical guides. Use for verifying facts, "
                "finding best practices, and latest Azure/Microsoft technology info."
            ),
            approval_mode="never_require",
            allowed_tools=[
                "microsoft_docs_search",
                "microsoft_docs_fetch",
                "microsoft_code_sample_search",
            ],
        )
        tools.append(mcp_tool)
        logger.info("MCP tool enabled (url=%s)", config.MCP_SERVER_URL)
    else:
        logger.info("MCP_SERVER_URL not configured — MCP tool disabled")

    # Add Foundry IQ Agentic Retrieval if configured
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
    system_prompt = get_system_prompt(ab_mode=ab_mode)
    agent = client.as_agent(
        name="techpulse_social_agent",
        instructions=system_prompt,
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

            # ---------------------------------------------------------
            # Detect hosted tool events (web_search, file_search) from
            # the raw OpenAI stream event.  The agent-framework-core SDK
            # does NOT parse these into Content objects — they fall
            # through to `case _: logger.debug(...)`.  However, the raw
            # event is preserved in raw_representation, so we inspect it
            # directly to emit tool events for the frontend.
            # ---------------------------------------------------------
            raw_event = getattr(update, "raw_representation", None)
            if raw_event is not None:
                raw_type = getattr(raw_event, "type", "")
                # Log all raw events for debugging hosted tool detection
                if raw_type and ("search" in raw_type or "mcp" in raw_type):
                    logger.info(
                        "Hosted tool raw event: type=%s",
                        raw_type,
                    )

                # "response.output_item.added" with item.type == web/file search or mcp
                if raw_type == "response.output_item.added":
                    item = getattr(raw_event, "item", None)
                    if item:
                        item_type = getattr(item, "type", "")
                        if item_type in ("web_search_call", "file_search_call"):
                            tool_name = (
                                "web_search"
                                if "web_search" in item_type
                                else "file_search"
                            )
                            item_id = getattr(item, "id", "") or tool_name
                            if item_id not in emitted_tool_starts:
                                emitted_tool_starts.add(item_id)
                                call_id_to_name[item_id] = tool_name
                                yield create_tool_event(tool_name, "started")
                        elif item_type in ("mcp_call", "mcp_list_tools"):
                            item_id = getattr(item, "id", "") or "mcp_search"
                            if item_id not in emitted_tool_starts:
                                emitted_tool_starts.add(item_id)
                                call_id_to_name[item_id] = "mcp_search"
                                yield create_tool_event("mcp_search", "started")

                # "response.web_search_call.*" / "response.file_search_call.*" / "response.mcp_call.*"
                elif "web_search_call" in raw_type or "file_search_call" in raw_type:
                    tool_name = (
                        "web_search" if "web_search_call" in raw_type else "file_search"
                    )
                    item_id = getattr(raw_event, "item_id", "") or tool_name

                    if raw_type.endswith(".completed"):
                        if item_id not in emitted_tool_ends:
                            emitted_tool_ends.add(item_id)
                            yield create_tool_event(tool_name, "completed")
                    elif raw_type.endswith((".in_progress", ".searching")):
                        # Emit started if not already done via output_item.added
                        if item_id not in emitted_tool_starts:
                            emitted_tool_starts.add(item_id)
                            call_id_to_name[item_id] = tool_name
                            yield create_tool_event(tool_name, "started")

                elif "mcp_call" in raw_type or "mcp_list_tools" in raw_type:
                    item_id = getattr(raw_event, "item_id", "") or "mcp_search"
                    if raw_type.endswith(".completed"):
                        if item_id not in emitted_tool_ends:
                            emitted_tool_ends.add(item_id)
                            yield create_tool_event("mcp_search", "completed")
                    elif item_id not in emitted_tool_starts:
                        emitted_tool_starts.add(item_id)
                        call_id_to_name[item_id] = "mcp_search"
                        yield create_tool_event("mcp_search", "started")

            # Fallback: if update has .text but no contents processed
            if not update.contents and update.text:
                yield update.text

            # Additional fallback: inspect raw_representation dict-like objects
            # Some SDK versions serialize raw_event differently
            if raw_event is not None and not isinstance(raw_event, str):
                try:
                    raw_dict = (
                        raw_event
                        if isinstance(raw_event, dict)
                        else (
                            raw_event.model_dump()
                            if hasattr(raw_event, "model_dump")
                            else vars(raw_event)
                            if hasattr(raw_event, "__dict__")
                            else None
                        )
                    )
                    if raw_dict:
                        raw_type_str = str(raw_dict.get("type", ""))
                        if (
                            "web_search" in raw_type_str
                            or "file_search" in raw_type_str
                        ):
                            tool_name = (
                                "web_search"
                                if "web_search" in raw_type_str
                                else "file_search"
                            )
                            item_id = str(
                                raw_dict.get("item_id", raw_dict.get("id", tool_name))
                            )
                            if "completed" in raw_type_str or "done" in raw_type_str:
                                if item_id not in emitted_tool_ends:
                                    emitted_tool_ends.add(item_id)
                                    yield create_tool_event(tool_name, "completed")
                            elif item_id not in emitted_tool_starts:
                                emitted_tool_starts.add(item_id)
                                call_id_to_name[item_id] = tool_name
                                yield create_tool_event(tool_name, "started")
                        elif "mcp" in raw_type_str:
                            item_id = str(
                                raw_dict.get(
                                    "item_id", raw_dict.get("id", "mcp_search")
                                )
                            )
                            if "completed" in raw_type_str or "done" in raw_type_str:
                                if item_id not in emitted_tool_ends:
                                    emitted_tool_ends.add(item_id)
                                    yield create_tool_event("mcp_search", "completed")
                            elif item_id not in emitted_tool_starts:
                                emitted_tool_starts.add(item_id)
                                call_id_to_name[item_id] = "mcp_search"
                                yield create_tool_event("mcp_search", "started")
                except Exception:
                    pass  # best-effort fallback

        # ---- Post-stream fallback: emit tool events for hosted tools ----
        # If the final content references search results but no tool events
        # were emitted, synthesize them so the frontend knows tools were used.
        if "web_search" not in emitted_tool_starts and vector_store_id:
            # No explicit web_search event detected — check if content suggests usage
            pass  # We already have the raw_representation approach; this is a safety net
        if (
            "file_search" not in {call_id_to_name.get(k) for k in emitted_tool_starts}
            and vector_store_id
        ):
            logger.debug(
                "file_search tool was configured but no events detected. "
                "This may indicate the SDK did not expose raw events."
            )

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
