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
    # Track which hosted tool NAMES have been detected
    _detected_hosted: set[str] = set()

    # ----- helpers for hosted tool event emission -----
    def _emit_start(tool_name: str, item_id: str) -> str | None:
        if item_id not in emitted_tool_starts:
            emitted_tool_starts.add(item_id)
            call_id_to_name[item_id] = tool_name
            _detected_hosted.add(tool_name)
            return create_tool_event(tool_name, "started")
        return None

    def _emit_end(tool_name: str, item_id: str) -> str | None:
        if item_id not in emitted_tool_ends:
            emitted_tool_ends.add(item_id)
            _detected_hosted.add(tool_name)
            # Ensure start was emitted first
            if item_id not in emitted_tool_starts:
                emitted_tool_starts.add(item_id)
                call_id_to_name[item_id] = tool_name
            return create_tool_event(tool_name, "completed")
        return None

    # Mapping of raw event substrings → canonical tool names
    _HOSTED_PATTERNS: dict[str, str] = {
        "web_search_call": "web_search",
        "web_search": "web_search",
        "file_search_call": "file_search",
        "file_search": "file_search",
        "mcp_call": "mcp_search",
        "mcp_list_tools": "mcp_search",
    }

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

                elif ct in (
                    "web_search_call",
                    "file_search_call",
                    "mcp_call",
                    "mcp_list_tools",
                ):
                    # Hosted tool exposed as a Content item (some SDK versions)
                    tool_name = _HOSTED_PATTERNS.get(ct, "unknown_tool")
                    item_id = (
                        getattr(content, "id", "")
                        or getattr(content, "call_id", "")
                        or tool_name
                    )
                    ev = _emit_start(tool_name, item_id)
                    if ev:
                        yield ev

                elif ct == "text" and content.text:
                    # Regular text output
                    yield content.text

                    # --- Annotation-based hosted tool detection ---
                    # When text contains url_citation or file_citation,
                    # it proves the hosted tool was used even if we
                    # missed the raw events.
                    annotations = getattr(content, "annotations", None) or []
                    for ann in annotations:
                        ann_type = getattr(ann, "type", "")
                        if (
                            "url_citation" in ann_type
                            and "web_search" not in _detected_hosted
                        ):
                            ev = _emit_start("web_search", "ws_annotation")
                            if ev:
                                yield ev
                            ev = _emit_end("web_search", "ws_annotation")
                            if ev:
                                yield ev
                        elif (
                            "file_citation" in ann_type
                            and "file_search" not in _detected_hosted
                        ):
                            ev = _emit_start("file_search", "fs_annotation")
                            if ev:
                                yield ev
                            ev = _emit_end("file_search", "fs_annotation")
                            if ev:
                                yield ev

                elif ct == "usage":
                    # ---- Extract hosted tool usage from ResponseCompletedEvent ----
                    # The SDK sends a "usage" Content item whose raw_representation
                    # contains the full ResponseCompletedEvent with Response.output.
                    # This is our most reliable way to detect hosted tools (web_search,
                    # file_search, MCP) since the SDK does NOT expose their individual
                    # streaming events as AgentResponseUpdate objects.
                    raw = getattr(content, "raw_representation", None)
                    resp = None
                    if raw is not None:
                        resp = getattr(raw, "response", None)
                    if resp is not None:
                        for out_item in getattr(resp, "output", []):
                            item_type = getattr(out_item, "type", "")
                            for pattern, tool_name in _HOSTED_PATTERNS.items():
                                if pattern in item_type:
                                    iid = getattr(out_item, "id", "") or tool_name
                                    logger.info(
                                        "Hosted tool from Response.output: "
                                        "type=%s → %s (id=%s)",
                                        item_type,
                                        tool_name,
                                        iid,
                                    )
                                    ev = _emit_start(tool_name, iid)
                                    if ev:
                                        yield ev
                                    ev = _emit_end(tool_name, iid)
                                    if ev:
                                        yield ev
                                    break

                else:
                    # Unknown content type — log for debugging
                    if ct:
                        logger.debug("Unknown content type: %s", ct)

            # ---------------------------------------------------------
            # Detect hosted tool events from raw OpenAI stream event.
            # The agent-framework-core SDK may not parse these into
            # Content objects.  We inspect raw_representation to catch
            # web_search_call, file_search_call, and mcp_call events.
            # ---------------------------------------------------------
            raw_event = getattr(update, "raw_representation", None)
            # Some SDK versions use different attribute names
            if raw_event is None:
                raw_event = getattr(update, "raw_event", None)

            if raw_event is not None:
                # Extract type string from raw event (handle dict or object)
                if isinstance(raw_event, dict):
                    raw_type = str(raw_event.get("type", ""))
                else:
                    raw_type = str(getattr(raw_event, "type", ""))

                # Log ALL raw events (not just search-related) for debugging
                if raw_type:
                    logger.debug("Raw stream event: type=%s", raw_type)

                # --- Unified hosted tool detection from raw_type ---
                matched_tool = None
                for pattern, tool_name in _HOSTED_PATTERNS.items():
                    if pattern in raw_type:
                        matched_tool = tool_name
                        break

                if matched_tool:
                    logger.info(
                        "Hosted tool raw event: type=%s → %s",
                        raw_type,
                        matched_tool,
                    )

                    # Extract item_id from the raw event
                    if isinstance(raw_event, dict):
                        item_id = str(
                            raw_event.get("item_id", "") or raw_event.get("id", "")
                        )
                        item = raw_event.get("item")
                    else:
                        item_id = str(
                            getattr(raw_event, "item_id", "")
                            or getattr(raw_event, "id", "")
                        )
                        item = getattr(raw_event, "item", None)

                    # Try to get item_id from nested item object
                    if not item_id and item:
                        if isinstance(item, dict):
                            item_id = str(item.get("id", ""))
                        else:
                            item_id = str(getattr(item, "id", ""))
                    if not item_id:
                        item_id = matched_tool

                    # Emit start or end based on event type
                    is_completed = "completed" in raw_type or "done" in raw_type
                    if is_completed:
                        ev = _emit_end(matched_tool, item_id)
                        if ev:
                            yield ev
                    else:
                        ev = _emit_start(matched_tool, item_id)
                        if ev:
                            yield ev

                # --- Also check for output_item events with hosted tool items ---
                if "output_item" in raw_type:
                    if isinstance(raw_event, dict):
                        item = raw_event.get("item", {})
                        item_type = (
                            item.get("type", "") if isinstance(item, dict) else ""
                        )
                    else:
                        item = getattr(raw_event, "item", None)
                        item_type = str(getattr(item, "type", "")) if item else ""

                    for pattern, tool_name in _HOSTED_PATTERNS.items():
                        if pattern in item_type:
                            if isinstance(item, dict):
                                iid = str(item.get("id", "")) or tool_name
                            else:
                                iid = (
                                    str(getattr(item, "id", "")) if item else tool_name
                                )

                            if "done" in raw_type:
                                ev = _emit_end(tool_name, iid)
                                if ev:
                                    yield ev
                            else:
                                ev = _emit_start(tool_name, iid)
                                if ev:
                                    yield ev
                            break

            # Fallback: if update has .text but no contents processed
            if not update.contents and update.text:
                yield update.text

        # ---- Post-stream: synthesize events for configured but undetected tools ----
        # If a hosted tool was configured but no events were detected during
        # streaming, inspect the final response for evidence of usage and emit
        # synthetic events so the frontend always shows what tools ran.
        if hasattr(stream, "response"):
            try:
                response = stream.response
                for output_item in getattr(response, "output", []):
                    item_type = getattr(output_item, "type", "")
                    for pattern, tool_name in _HOSTED_PATTERNS.items():
                        if pattern in item_type and tool_name not in _detected_hosted:
                            iid = getattr(output_item, "id", "") or tool_name
                            ev = _emit_start(tool_name, iid)
                            if ev:
                                yield ev
                            ev = _emit_end(tool_name, iid)
                            if ev:
                                yield ev
                            break
            except Exception:
                pass  # best-effort

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
