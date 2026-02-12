"""FastAPI application with SSE streaming for TechPulse Social.

Provides:
- POST /api/chat — Streaming chat endpoint (SSE)
- GET /api/health — Health check
"""

import json
import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.agent import REASONING_END, REASONING_START, run_agent_stream
from src.config import DEBUG
from src.database import (
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

# FastAPI app
app = FastAPI(
    title="TechPulse Social API",
    description="AI-Powered Social Media Content Studio",
    version="0.2.0",
)

# CORS — allow frontend dev server and deployed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "*",  # Allow deployed origin
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation history (hackathon scope — no persistence)
_conversations: dict[str, list[dict]] = {}

# ---------- Serve frontend static files in production ---------- #
_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_SERVE_STATIC = os.getenv("SERVE_STATIC", "false").lower() == "true"

# Regex for reasoning and tool event markers
TOOL_EVENT_PATTERN = re.compile(r"__TOOL_EVENT__(.*?)__END_TOOL_EVENT__")
REASONING_PATTERN = re.compile(
    rf"{re.escape(REASONING_START)}([\s\S]*?){re.escape(REASONING_END)}"
)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "techpulse-social", "version": "0.3.0"}


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


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize Vector Store on startup (non-blocking)."""
    try:
        from src.vector_store import ensure_vector_store

        vs_id = ensure_vector_store()
        # Update runtime config so agent.py can pick it up
        import src.config as cfg

        cfg.VECTOR_STORE_ID = vs_id
        logger.info("Vector Store ready: %s", vs_id)
    except Exception as e:
        logger.warning("Vector Store initialization skipped: %s", e)


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
        logger.error(f"Invalid request: {e}")
        return JSONResponse(
            content={"error": f"Invalid request: {e}"},
            status_code=400,
        )

    # Thread ID for multi-turn
    thread_id = chat_req.thread_id or str(uuid.uuid4())

    # Get conversation history
    history = _conversations.get(thread_id, [])

    # Add user message to history
    history.append({"role": "user", "content": chat_req.message})

    async def generate():
        """SSE event generator."""
        assistant_content = ""

        try:
            async for chunk in run_agent_stream(
                message=chat_req.message,
                platforms=chat_req.platforms,
                content_type=chat_req.content_type,
                language=chat_req.language,
                history=history[:-1],  # Exclude current message (already in query)
                reasoning_effort=chat_req.reasoning_effort,
                reasoning_summary=chat_req.reasoning_summary,
            ):
                if not chunk:
                    continue

                chunk_str = str(chunk)

                # Check for tool events
                tool_match = TOOL_EVENT_PATTERN.search(chunk_str)
                if tool_match:
                    yield f"{chunk_str}\n\n"
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
                _conversations[thread_id] = history

                # Persist to Cosmos DB (or in-memory fallback)
                title = chat_req.message[:50].rstrip()
                save_conversation(
                    conversation_id=thread_id,
                    title=title,
                    messages=history,
                )

            # Send done signal
            done_event = {"type": "done", "thread_id": thread_id}
            yield json.dumps(done_event) + "\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            error_event = {"error": str(e)}
            yield json.dumps(error_event) + "\n\n"

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
        file_path = _STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")

    logger.info(f"Serving frontend static files from {_STATIC_DIR}")


def main() -> None:
    """Run the API server."""
    import uvicorn

    from src.config import HOST, PORT

    logger.info(f"Starting TechPulse Social API on {HOST}:{PORT}")
    uvicorn.run(
        "src.api:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )


if __name__ == "__main__":
    main()
