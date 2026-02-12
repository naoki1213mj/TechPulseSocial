"""Agentic Retrieval Tool for Azure AI Search Knowledge Base (Foundry IQ).

Provides advanced RAG capabilities with LLM-based query planning,
multi-source retrieval, and configurable reasoning effort levels.

This module integrates with Azure AI Search Knowledge Bases using the
Agentic Retrieval API (Foundry IQ), which offers:
- Query decomposition and planning (LLM-based)
- Multi-source retrieval with semantic reranking
- Configurable reasoning effort (minimal/low/medium)
- Source attribution and citations

Environment Variables:
    AI_SEARCH_ENDPOINT: Azure AI Search endpoint URL
    AI_SEARCH_KNOWLEDGE_BASE_NAME: Knowledge Base name
    AI_SEARCH_API_KEY: API key (optional if using managed identity)
    AI_SEARCH_REASONING_EFFORT: Default reasoning effort (minimal/low/medium)

Reference:
    https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-set-retrieval-reasoning-effort
"""

import json
import logging
import os
from enum import StrEnum
from typing import Annotated, Any

import httpx
from agent_framework import tool

logger = logging.getLogger(__name__)


class ReasoningEffort(StrEnum):
    """Reasoning effort levels for Agentic Retrieval."""

    MINIMAL = "minimal"  # Direct search, no LLM — fastest/cheapest
    LOW = "low"  # Single-pass LLM query planning — balanced (default)
    MEDIUM = "medium"  # Iterative search with semantic classifier — best quality


# Configuration
AI_SEARCH_ENDPOINT = os.getenv("AI_SEARCH_ENDPOINT", "")
AI_SEARCH_KNOWLEDGE_BASE_NAME = os.getenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "")
AI_SEARCH_API_KEY = os.getenv("AI_SEARCH_API_KEY", "")
AI_SEARCH_REASONING_EFFORT = os.getenv("AI_SEARCH_REASONING_EFFORT", "low")

# API version for Agentic Retrieval
API_VERSION = "2025-11-01-preview"


def is_configured() -> bool:
    """Check if Foundry IQ is configured."""
    return bool(AI_SEARCH_ENDPOINT and AI_SEARCH_KNOWLEDGE_BASE_NAME)


async def retrieve(
    query: str,
    reasoning_effort: str | None = None,
    max_results: int = 3,
) -> dict[str, Any]:
    """Retrieve documents from Knowledge Base using Agentic Retrieval.

    Args:
        query: The search query.
        reasoning_effort: Override default effort (minimal/low/medium).
        max_results: Maximum number of results to return.

    Returns:
        Dict with sources, activity, and metadata.
    """
    if not is_configured():
        return {"error": "Foundry IQ not configured (AI_SEARCH_* env vars missing)"}

    effort = reasoning_effort or AI_SEARCH_REASONING_EFFORT
    endpoint = AI_SEARCH_ENDPOINT.rstrip("/")
    kb_name = AI_SEARCH_KNOWLEDGE_BASE_NAME

    url = f"{endpoint}/knowledgebases/{kb_name}/retrieve?api-version={API_VERSION}"

    # Build request body based on reasoning effort
    if effort == "minimal":
        # Minimal: direct intent-based search (no LLM)
        body: dict[str, Any] = {
            "intents": [{"type": "semantic", "search": query}],
        }
    else:
        # Low/Medium: LLM-based query planning
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}],
                }
            ],
            "retrievalReasoningEffort": {"kind": effort},
            "outputMode": "extractiveData",
            "maxRuntimeInSeconds": 30,
            "maxOutputSize": 6000,
        }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if AI_SEARCH_API_KEY:
        headers["api-key"] = AI_SEARCH_API_KEY
    else:
        # Use DefaultAzureCredential for managed identity
        try:
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            token = credential.get_token("https://search.azure.com/.default")
            headers["Authorization"] = f"Bearer {token.token}"
        except Exception as e:
            logger.error(f"Failed to get search token: {e}")
            return {"error": f"Authentication failed: {e}"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=body, headers=headers)

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    f"Agentic Retrieval failed: {response.status_code} - {error_text}"
                )
                return {"error": f"Search failed: {response.status_code}"}

            result = response.json()

        # Parse response
        return _parse_response(result, effort)

    except Exception as e:
        logger.error(f"Agentic Retrieval error: {e}")
        return {"error": str(e)}


def _parse_response(response: dict, effort: str) -> dict[str, Any]:
    """Parse Agentic Retrieval response into structured format."""
    response_data = response.get("response", [])
    activity = response.get("activity", [])
    references = response.get("references", [])

    sources: list[dict] = []
    for item in response_data:
        content_list = item.get("content", [])
        for content_item in content_list:
            if content_item.get("type") == "text":
                text = content_item.get("text", "")
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and "extractiveData" in parsed:
                        chunks = parsed["extractiveData"].get("chunks", [])
                        for chunk in chunks:
                            sources.append(
                                {
                                    "content": chunk.get("content", ""),
                                    "source": chunk.get("metadata", {}).get("url", ""),
                                    "title": chunk.get("metadata", {}).get("title", ""),
                                    "score": chunk.get("rerankerScore", 0),
                                }
                            )
                except (json.JSONDecodeError, TypeError):
                    sources.append(
                        {"content": text, "source": "", "title": "", "score": 0}
                    )

    # Parse activity summary
    activity_summary = []
    for act in activity:
        act_type = act.get("type", "unknown")
        if act_type == "agenticReasoning":
            activity_summary.append(
                {
                    "type": act_type,
                    "reasoning_tokens": act.get("reasoningTokens", 0),
                }
            )
        elif act_type in ("indexedSharePoint", "searchIndex"):
            activity_summary.append(
                {
                    "type": act_type,
                    "knowledge_source": act.get("knowledgeSourceName", ""),
                    "count": act.get("count", 0),
                    "elapsed_ms": act.get("elapsedMs", 0),
                }
            )

    return {
        "sources": sources,
        "activity": activity_summary,
        "references": references,
        "reasoning_effort": effort,
    }


def _format_results(result: dict) -> str:
    """Format retrieval results for agent consumption."""
    if "error" in result:
        return f"ナレッジベース検索エラー: {result['error']}"

    sources = result.get("sources", [])
    if not sources:
        return "関連するドキュメントが見つかりませんでした。"

    formatted = []
    for i, source in enumerate(sources):
        score = source.get("score", 0)
        content = source.get("content", "")
        src = source.get("source", "")
        title = source.get("title", "")

        # Truncate long content
        if len(content) > 2000:
            content = content[:2000] + "...(truncated)"

        citation = f"【ref_{i + 1}†relevance:{score:.2f}】"
        header = f"## {title}\n" if title else ""
        source_line = f"\n_Source: {src}_" if src else ""
        formatted.append(f"{header}{citation}\n{content}{source_line}")

    # Add activity summary
    activity = result.get("activity", [])
    footer_parts = [f"Reasoning Effort: {result.get('reasoning_effort', 'unknown')}"]
    for act in activity:
        if act.get("type") == "agenticReasoning":
            tokens = act.get("reasoning_tokens", 0)
            footer_parts.append(f"推論トークン: {tokens:,}")
        elif act.get("knowledge_source"):
            ks = act.get("knowledge_source", "")
            count = act.get("count", 0)
            ms = act.get("elapsed_ms", 0)
            footer_parts.append(f"{ks}: {count}件 ({ms}ms)")

    footer = f"\n\n---\n📊 {' | '.join(footer_parts)}"

    return "\n\n---\n\n".join(formatted) + footer


# ========== Agent Tool Function ========== #


@tool(approval_mode="never_require")
async def search_knowledge_base(
    query: Annotated[str, "The search query for finding relevant documents"],
    reasoning_effort: Annotated[
        str,
        "Level of LLM processing: 'minimal' (fast), 'low' (balanced), 'medium' (best quality)",
    ] = "low",
) -> str:
    """Search the knowledge base using Foundry IQ Agentic Retrieval.

    This tool provides intelligent document retrieval with:
    - Query decomposition and planning (LLM-based)
    - Multi-source retrieval with semantic reranking
    - Configurable reasoning effort for cost/quality tradeoff

    Use this tool when you need to look up brand guidelines,
    product documentation, or internal knowledge base articles.

    Args:
        query: The search query for finding relevant documents.
        reasoning_effort: Level of LLM processing.

    Returns:
        Formatted search results with citations and relevance scores.
    """
    logger.info(f"Foundry IQ search: query='{query}', effort={reasoning_effort}")

    result = await retrieve(query, reasoning_effort)
    return _format_results(result)
