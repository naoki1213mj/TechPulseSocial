"""Tests for src/agent.py — agent creation helpers and tool event formatting."""

import json

from src.agent import (
    REASONING_END,
    REASONING_START,
    REASONING_THROTTLE_MS,
    TOOL_EVENT_END,
    TOOL_EVENT_START,
    _build_query_with_context,
    create_tool_event,
)


class TestCreateToolEvent:
    """Test create_tool_event helper."""

    def test_basic_event(self):
        result = create_tool_event("web_search", "started")
        assert result.startswith(TOOL_EVENT_START)
        assert result.endswith(TOOL_EVENT_END)

    def test_json_parseable(self):
        result = create_tool_event("generate_content", "completed")
        # Extract JSON between markers
        json_str = result[len(TOOL_EVENT_START) : -len(TOOL_EVENT_END)]
        data = json.loads(json_str)
        assert data["type"] == "tool_event"
        assert data["tool"] == "generate_content"
        assert data["status"] == "completed"
        assert "timestamp" in data

    def test_with_message(self):
        result = create_tool_event("generate_image", "error", "Rate limited")
        json_str = result[len(TOOL_EVENT_START) : -len(TOOL_EVENT_END)]
        data = json.loads(json_str)
        assert data["message"] == "Rate limited"

    def test_without_message(self):
        result = create_tool_event("review_content", "started")
        json_str = result[len(TOOL_EVENT_START) : -len(TOOL_EVENT_END)]
        data = json.loads(json_str)
        assert "message" not in data

    def test_timestamp_iso_format(self):
        result = create_tool_event("test_tool", "started")
        json_str = result[len(TOOL_EVENT_START) : -len(TOOL_EVENT_END)]
        data = json.loads(json_str)
        # ISO 8601 should contain T and +00:00 or Z
        assert "T" in data["timestamp"]

    def test_japanese_message(self):
        result = create_tool_event("test", "completed", "画像生成完了")
        json_str = result[len(TOOL_EVENT_START) : -len(TOOL_EVENT_END)]
        data = json.loads(json_str)
        assert data["message"] == "画像生成完了"


class TestBuildQueryWithContext:
    """Test _build_query_with_context helper."""

    def test_basic_query(self):
        result = _build_query_with_context(
            message="AI product launch",
            platforms=["linkedin", "x"],
            content_type="product_launch",
            language="en",
        )
        assert "AI product launch" in result
        assert "linkedin" in result
        assert "product_launch" in result
        assert "en" in result

    def test_no_history(self):
        result = _build_query_with_context(
            message="test", platforms=["x"], content_type="trend", language="en"
        )
        assert "Previous conversation" not in result

    def test_with_history(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _build_query_with_context(
            message="Follow up",
            platforms=["linkedin"],
            content_type="thought_leadership",
            language="en",
            history=history,
        )
        assert "Previous conversation" in result
        assert "Hello" in result
        assert "Hi there" in result

    def test_history_truncated_to_6(self):
        # Create more than 6 history messages
        history = [{"role": "user", "content": f"msg-{i}"} for i in range(10)]
        result = _build_query_with_context(
            message="latest",
            platforms=["x"],
            content_type="trend",
            language="en",
            history=history,
        )
        # Only last 6 should appear
        assert "msg-4" in result  # 10-6=4, so msg-4..msg-9
        assert "msg-0" not in result

    def test_single_platform(self):
        result = _build_query_with_context(
            message="test", platforms=["instagram"], content_type="event", language="ja"
        )
        assert "instagram" in result
        assert "ja" in result

    def test_empty_history(self):
        result = _build_query_with_context(
            message="test",
            platforms=["x"],
            content_type="trend",
            language="en",
            history=[],
        )
        assert "Previous conversation" not in result


class TestConstants:
    """Test agent module constants."""

    def test_marker_strings(self):
        assert TOOL_EVENT_START == "__TOOL_EVENT__"
        assert TOOL_EVENT_END == "__END_TOOL_EVENT__"
        assert REASONING_START == "__REASONING_REPLACE__"
        assert REASONING_END == "__END_REASONING_REPLACE__"

    def test_throttle_value(self):
        assert REASONING_THROTTLE_MS == 100
        assert isinstance(REASONING_THROTTLE_MS, int)
