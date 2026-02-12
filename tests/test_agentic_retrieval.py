"""Tests for src/agentic_retrieval.py — Foundry IQ Agentic Retrieval."""

import json
from unittest.mock import patch

from src.agentic_retrieval import (
    API_VERSION,
    ReasoningEffort,
    _format_results,
    _parse_response,
    is_configured,
)


class TestReasoningEffort:
    """Test ReasoningEffort enum."""

    def test_values(self):
        assert ReasoningEffort.MINIMAL == "minimal"
        assert ReasoningEffort.LOW == "low"
        assert ReasoningEffort.MEDIUM == "medium"

    def test_is_str(self):
        assert isinstance(ReasoningEffort.LOW, str)


class TestIsConfigured:
    """Test is_configured function."""

    def test_configured_with_both(self):
        with (
            patch(
                "src.agentic_retrieval.AI_SEARCH_ENDPOINT", "https://search.example.com"
            ),
            patch("src.agentic_retrieval.AI_SEARCH_KNOWLEDGE_BASE_NAME", "my-kb"),
        ):
            assert is_configured() is True

    def test_not_configured_missing_endpoint(self):
        with (
            patch("src.agentic_retrieval.AI_SEARCH_ENDPOINT", ""),
            patch("src.agentic_retrieval.AI_SEARCH_KNOWLEDGE_BASE_NAME", "my-kb"),
        ):
            assert is_configured() is False

    def test_not_configured_missing_kb(self):
        with (
            patch(
                "src.agentic_retrieval.AI_SEARCH_ENDPOINT", "https://search.example.com"
            ),
            patch("src.agentic_retrieval.AI_SEARCH_KNOWLEDGE_BASE_NAME", ""),
        ):
            assert is_configured() is False

    def test_not_configured_both_empty(self):
        with (
            patch("src.agentic_retrieval.AI_SEARCH_ENDPOINT", ""),
            patch("src.agentic_retrieval.AI_SEARCH_KNOWLEDGE_BASE_NAME", ""),
        ):
            assert is_configured() is False


class TestParseResponse:
    """Test _parse_response function."""

    def test_empty_response(self):
        result = _parse_response({}, "low")
        assert result["sources"] == []
        assert result["activity"] == []
        assert result["reasoning_effort"] == "low"

    def test_extractive_data_parsing(self):
        response = {
            "response": [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "extractiveData": {
                                        "chunks": [
                                            {
                                                "content": "Brand voice is professional",
                                                "metadata": {
                                                    "url": "https://docs.example.com/brand",
                                                    "title": "Brand Guidelines",
                                                },
                                                "rerankerScore": 0.95,
                                            }
                                        ]
                                    }
                                }
                            ),
                        }
                    ]
                }
            ],
        }
        result = _parse_response(response, "medium")
        assert len(result["sources"]) == 1
        assert result["sources"][0]["content"] == "Brand voice is professional"
        assert result["sources"][0]["title"] == "Brand Guidelines"
        assert result["sources"][0]["score"] == 0.95

    def test_plain_text_fallback(self):
        response = {
            "response": [
                {"content": [{"type": "text", "text": "Plain search result text"}]}
            ],
        }
        result = _parse_response(response, "minimal")
        assert len(result["sources"]) == 1
        assert result["sources"][0]["content"] == "Plain search result text"
        assert result["sources"][0]["source"] == ""

    def test_activity_parsing(self):
        response = {
            "response": [],
            "activity": [
                {"type": "agenticReasoning", "reasoningTokens": 150},
                {
                    "type": "searchIndex",
                    "knowledgeSourceName": "brand-docs",
                    "count": 5,
                    "elapsedMs": 200,
                },
            ],
        }
        result = _parse_response(response, "low")
        assert len(result["activity"]) == 2
        assert result["activity"][0]["reasoning_tokens"] == 150
        assert result["activity"][1]["knowledge_source"] == "brand-docs"

    def test_references_preserved(self):
        response = {
            "response": [],
            "references": [{"id": "ref1", "url": "https://example.com"}],
        }
        result = _parse_response(response, "low")
        assert len(result["references"]) == 1

    def test_multiple_chunks(self):
        chunks = [
            {
                "content": f"Chunk {i}",
                "metadata": {"url": f"url{i}", "title": f"Title {i}"},
                "rerankerScore": 0.9 - i * 0.1,
            }
            for i in range(3)
        ]
        response = {
            "response": [
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"extractiveData": {"chunks": chunks}}),
                        }
                    ]
                }
            ],
        }
        result = _parse_response(response, "medium")
        assert len(result["sources"]) == 3


class TestFormatResults:
    """Test _format_results function."""

    def test_error_result(self):
        result = _format_results({"error": "Auth failed"})
        assert "エラー" in result
        assert "Auth failed" in result

    def test_empty_sources(self):
        result = _format_results({"sources": []})
        assert "見つかりませんでした" in result

    def test_formatted_output(self):
        data = {
            "sources": [
                {
                    "content": "Professional brand voice",
                    "source": "https://example.com/brand",
                    "title": "Brand Guide",
                    "score": 0.92,
                }
            ],
            "activity": [],
            "reasoning_effort": "low",
        }
        result = _format_results(data)
        assert "Brand Guide" in result
        assert "Professional brand voice" in result
        assert "0.92" in result
        assert "ref_1" in result

    def test_content_truncation(self):
        data = {
            "sources": [
                {
                    "content": "x" * 3000,
                    "source": "",
                    "title": "",
                    "score": 0.5,
                }
            ],
            "activity": [],
            "reasoning_effort": "minimal",
        }
        result = _format_results(data)
        assert "truncated" in result

    def test_activity_footer(self):
        data = {
            "sources": [{"content": "test", "source": "", "title": "", "score": 0.5}],
            "activity": [
                {"type": "agenticReasoning", "reasoning_tokens": 200},
                {
                    "type": "searchIndex",
                    "knowledge_source": "brand-docs",
                    "count": 3,
                    "elapsed_ms": 150,
                },
            ],
            "reasoning_effort": "medium",
        }
        result = _format_results(data)
        assert "200" in result  # reasoning tokens
        assert "brand-docs" in result


class TestApiVersion:
    """Test API version constant."""

    def test_api_version_format(self):
        assert API_VERSION == "2025-11-01-preview"
