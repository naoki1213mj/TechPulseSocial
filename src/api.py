"""FastAPI application with SSE streaming for Social AI Studio.

Provides:
- POST /api/chat — Streaming chat endpoint (SSE)
- POST /api/evaluate — Content quality evaluation (Foundry Evaluation)
- POST /api/safety — Content safety analysis
- GET /api/health — Health check
"""

import json
import logging
import os
import re
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# ---- OpenTelemetry setup (MUST be before FastAPI import) ---- #
from src.telemetry import get_tracer, setup_telemetry

setup_telemetry()

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402

from src import __version__
from src.agent import (  # noqa: E402
    IMAGE_DATA_END,
    IMAGE_DATA_START,
    REASONING_END,
    REASONING_START,
    run_agent_stream,
)
from src.config import DEBUG  # noqa: E402
from src.content_safety import (
    analyze_safety,
    check_prompt_shield,
    format_safety_summary,
)
from src.content_safety import is_configured as safety_configured  # noqa: E402
from src.database import (  # noqa: E402
    delete_conversation,
    get_conversation,
    list_conversations,
    save_conversation,
)
from src.models import ChatRequest

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------- Lifespan (replaces deprecated @app.on_event) ---------- #
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup / shutdown hooks."""
    # ---- startup ----
    try:
        from src.vector_store import ensure_vector_store

        vs_id = ensure_vector_store()
        import src.config as cfg

        cfg.VECTOR_STORE_ID = vs_id
        logger.info("Vector Store ready: %s", vs_id)
    except Exception as e:
        logger.warning("Vector Store initialization skipped: %s", e)

    yield
    # ---- shutdown ---- (nothing to clean up)


# FastAPI app
app = FastAPI(
    title="Social AI Studio API",
    description="AI-Powered Social Media Content Studio",
    version=__version__,
    lifespan=lifespan,
)

# CORS — allow frontend dev and deployed origins
# NOTE: allow_credentials=True is incompatible with allow_origins=["*"].
# In production, set ALLOWED_ORIGINS env var to the deployed domain.
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://localhost:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Serve frontend static files in production ---------- #
_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"

# Regex for reasoning, tool event, and image data markers
TOOL_EVENT_PATTERN = re.compile(r"__TOOL_EVENT__(.*?)__END_TOOL_EVENT__")
REASONING_PATTERN = re.compile(
    rf"{re.escape(REASONING_START)}([\s\S]*?){re.escape(REASONING_END)}"
)
IMAGE_DATA_PATTERN = re.compile(
    rf"{re.escape(IMAGE_DATA_START)}([\s\S]*?){re.escape(IMAGE_DATA_END)}"
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "social-ai-studio",
        "version": __version__,
        "observability": "opentelemetry",
        "content_safety": "enabled" if safety_configured() else "not_configured",
    }


# ---------- Conversation History API ---------- #


@app.get("/api/conversations")
async def api_list_conversations() -> list[dict]:
    """List all conversations."""
    return list_conversations()


@app.get("/api/conversations/{conversation_id}")
async def api_get_conversation(conversation_id: str):
    """Get a single conversation with messages."""
    convo = get_conversation(conversation_id)
    if convo is None:
        return JSONResponse(content={"error": "Not found"}, status_code=404)
    return convo


@app.delete("/api/conversations/{conversation_id}")
async def api_delete_conversation(conversation_id: str):
    """Delete a conversation."""
    if delete_conversation(conversation_id):
        return {"status": "deleted"}
    return JSONResponse(content={"error": "Not found"}, status_code=404)


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    """Streaming chat endpoint.

    Accepts a ChatRequest and returns an SSE stream with:
    - Reasoning tokens (thinking process)
    - Tool events (tool name, status, duration)
    - Text content (generated content in Markdown)
    - Done/error signals
    """
    try:
        body = await request.json()
        chat_req = ChatRequest(**body)
    except Exception as e:
        logger.error("Invalid request: %s", e)
        return JSONResponse(
            content={"error": "Invalid request body"},
            status_code=400,
        )

    # Thread ID for multi-turn
    thread_id = chat_req.thread_id or str(uuid.uuid4())

    # ---- Prompt Shield: detect prompt injection attacks ----
    shield_result = await check_prompt_shield(chat_req.message)
    if not shield_result.get("safe", True) and shield_result.get("attack_detected"):
        logger.warning("Prompt shield blocked input (thread=%s)", thread_id)
        return JSONResponse(
            content={
                "error": "Your message was blocked by our safety system. "
                "It appears to contain a prompt injection attempt.",
                "safety": shield_result,
            },
            status_code=400,
        )

    # Get conversation history from database (Cosmos or in-memory)
    existing = get_conversation(thread_id)
    history: list[dict] = existing.get("messages", []) if existing else []

    # Add user message to history
    history.append({"role": "user", "content": chat_req.message})

    async def generate():
        """SSE event generator."""
        assistant_content = ""
        tracer = get_tracer()

        try:
            async for chunk in run_agent_stream(
                message=chat_req.message,
                platforms=chat_req.platforms,
                content_type=chat_req.content_type,
                language=chat_req.language,
                history=history[:-1],  # Exclude current message (already in query)
                reasoning_effort=chat_req.reasoning_effort,
                reasoning_summary=chat_req.reasoning_summary,
                ab_mode=chat_req.ab_mode,
            ):
                if not chunk:
                    continue

                chunk_str = str(chunk)

                # Check for tool events
                tool_match = TOOL_EVENT_PATTERN.search(chunk_str)
                if tool_match:
                    yield f"{chunk_str}\n\n"
                    continue

                # Check for image data markers — send as separate SSE event
                image_match = IMAGE_DATA_PATTERN.search(chunk_str)
                if image_match:
                    try:
                        image_data = json.loads(image_match.group(1))
                        image_event = {
                            "type": "image",
                            "platform": image_data.get("platform", ""),
                            "image_base64": image_data.get("image_base64", ""),
                        }
                        yield json.dumps(image_event, ensure_ascii=False) + "\n\n"
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse image data marker")
                    continue

                # Check for reasoning markers — encode as JSON to avoid
                # \n\n in reasoning text breaking SSE framing
                reasoning_match = REASONING_PATTERN.search(chunk_str)
                if reasoning_match:
                    reasoning_text = reasoning_match.group(1)
                    reasoning_event = {
                        "type": "reasoning_update",
                        "reasoning": reasoning_text,
                    }
                    yield json.dumps(reasoning_event, ensure_ascii=False) + "\n\n"
                    continue

                # Regular text — accumulate and send as response chunk
                clean_chunk = REASONING_PATTERN.sub("", chunk_str)
                clean_chunk = TOOL_EVENT_PATTERN.sub("", clean_chunk)

                if clean_chunk.strip():
                    assistant_content += clean_chunk
                    response = {
                        "choices": [
                            {
                                "messages": [
                                    {
                                        "role": "assistant",
                                        "content": assistant_content,
                                    }
                                ]
                            }
                        ],
                        "thread_id": thread_id,
                    }
                    yield json.dumps(response, ensure_ascii=False) + "\n\n"

            # Save assistant response to history
            if assistant_content:
                history.append({"role": "assistant", "content": assistant_content})

                # Persist to Cosmos DB (or in-memory fallback)
                title = chat_req.message[:50].rstrip()
                save_conversation(
                    conversation_id=thread_id,
                    title=title,
                    messages=history,
                )

            # ---- Content Safety: analyze generated output ----
            safety_result = (
                await analyze_safety(assistant_content)
                if assistant_content
                else {"safe": True, "skipped": True, "reason": "No content generated"}
            )
            safety_event = {
                "type": "safety",
                "safety": safety_result,
                "summary": format_safety_summary(safety_result),
            }
            yield json.dumps(safety_event, ensure_ascii=False) + "\n\n"

            if not safety_result.get("safe", True):
                logger.warning(
                    "Content Safety flagged output (thread=%s): %s",
                    thread_id,
                    format_safety_summary(safety_result),
                )

            # Send done signal
            done_event = {"type": "done", "thread_id": thread_id}
            yield json.dumps(done_event) + "\n\n"

        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            # Send user-friendly error instead of raw exception
            err_msg = str(e).lower()
            if "failed to complete the prompt" in err_msg or "429" in err_msg or "500" in err_msg:
                user_message = (
                    "Azure AI サービスが一時的に利用できません。しばらくしてから再度お試しください。"
                    " / The Azure AI service is temporarily unavailable. Please try again shortly."
                )
            else:
                user_message = (
                    "コンテンツ生成中にエラーが発生しました。再度お試しください。"
                    " / An error occurred during content generation. Please try again."
                )
            error_event = {"error": user_message}
            yield json.dumps(error_event, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- Mount frontend static files (production) ---------- #
if _SERVE_STATIC and _STATIC_DIR.is_dir():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve SPA — return index.html for all non-API routes."""
        file_path = (_STATIC_DIR / full_path).resolve()
        # Prevent path traversal — ensure resolved path is under _STATIC_DIR
        if not str(file_path).startswith(str(_STATIC_DIR.resolve())):
            return FileResponse(_STATIC_DIR / "index.html")
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")

    logger.info("Serving frontend static files from %s", _STATIC_DIR)


# ---------- Content Safety Endpoint ---------- #


@app.post("/api/safety")
async def safety_check_endpoint(request: Request):
    """Analyze text for harmful content using Azure AI Content Safety.

    Accepts JSON: {text, check_prompt_injection?}
    Returns: {safe, categories, blocked_categories?, summary}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    text = body.get("text", "")
    check_injection = body.get("check_prompt_injection", False)

    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    if not safety_configured():
        return JSONResponse(
            {
                "error": "Content Safety not configured",
                "hint": "Set CONTENT_SAFETY_ENDPOINT environment variable",
            },
            status_code=501,
        )

    result = await analyze_safety(text)

    # Optional prompt injection check
    if check_injection:
        shield = await check_prompt_shield(text)
        result["prompt_shield"] = shield

    result["summary"] = format_safety_summary(result)
    return result


# ---------- Foundry Evaluation Endpoint ---------- #


@app.post("/api/evaluate")
async def evaluate_content_endpoint(request: Request):
    """Evaluate content quality using Azure AI Evaluation SDK.

    Accepts JSON: {query, response, context?}
    Returns: {relevance, coherence, fluency, groundedness?, ...}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    query = body.get("query", "")
    response_text = body.get("response", "")
    context = body.get("context")

    if not query or not response_text:
        return JSONResponse(
            {"error": "query and response are required"}, status_code=400
        )

    from src.evaluation import evaluate_content, is_configured

    if not is_configured():
        return JSONResponse(
            {
                "error": "Evaluation not configured",
                "hint": "Install azure-ai-evaluation: uv add azure-ai-evaluation",
            },
            status_code=501,
        )

    scores = await evaluate_content(
        query=query, response=response_text, context=context
    )
    return scores


def main() -> None:
    """Run the API server."""
    import uvicorn

    from src.config import HOST, PORT

    logger.info("Starting Social AI Studio API on %s:%s", HOST, PORT)
    uvicorn.run(
        "src.api:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )


if __name__ == "__main__":
    main()
