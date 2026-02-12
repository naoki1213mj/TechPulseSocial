"""Tests for src/models.py — Pydantic data model validation."""

import pytest
from pydantic import ValidationError

from src.models import (
    ChatRequest,
    ContentItem,
    ContentOutput,
    Review,
    ReviewScores,
    ToolEvent,
)


class TestChatRequest:
    """Test ChatRequest model validation."""

    def test_valid_minimal(self):
        req = ChatRequest(message="Hello world")
        assert req.message == "Hello world"

    def test_defaults(self):
        req = ChatRequest(message="test")
        assert req.thread_id is None
        assert req.platforms == ["linkedin", "x", "instagram"]
        assert req.content_type == "product_launch"
        assert req.language == "en"
        assert req.reasoning_effort == "medium"
        assert req.reasoning_summary == "auto"

    def test_custom_values(self):
        req = ChatRequest(
            message="Launch AI product",
            thread_id="abc-123",
            platforms=["x"],
            content_type="blog_summary",
            language="ja",
            reasoning_effort="high",
            reasoning_summary="detailed",
        )
        assert req.thread_id == "abc-123"
        assert req.platforms == ["x"]
        assert req.language == "ja"

    def test_message_required(self):
        with pytest.raises(ValidationError):
            ChatRequest()

    def test_empty_message_allowed(self):
        # Pydantic str field allows empty by default
        req = ChatRequest(message="")
        assert req.message == ""

    def test_serialization(self):
        req = ChatRequest(message="test")
        data = req.model_dump()
        assert "message" in data
        assert "platforms" in data
        assert isinstance(data["platforms"], list)


class TestReviewScores:
    """Test ReviewScores with ge/le validators."""

    def test_defaults(self):
        scores = ReviewScores()
        assert scores.brand_alignment == 0
        assert scores.audience_relevance == 0

    def test_valid_scores(self):
        scores = ReviewScores(
            brand_alignment=8.5,
            audience_relevance=9.0,
            engagement_potential=7.0,
            clarity=10.0,
            platform_optimization=0.0,
        )
        assert scores.brand_alignment == 8.5
        assert scores.platform_optimization == 0.0

    def test_score_exceeds_max(self):
        with pytest.raises(ValidationError):
            ReviewScores(brand_alignment=11)

    def test_score_below_min(self):
        with pytest.raises(ValidationError):
            ReviewScores(clarity=-1)

    def test_boundary_values(self):
        scores = ReviewScores(brand_alignment=0, clarity=10)
        assert scores.brand_alignment == 0
        assert scores.clarity == 10


class TestToolEvent:
    """Test ToolEvent model."""

    def test_valid_event(self):
        event = ToolEvent(
            type="tool_event",
            tool="generate_content",
            status="started",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert event.tool == "generate_content"
        assert event.message is None

    def test_with_message(self):
        event = ToolEvent(
            type="tool_event",
            tool="generate_image",
            status="completed",
            timestamp="2025-01-01T00:00:00Z",
            message="Image generated successfully",
        )
        assert event.message == "Image generated successfully"


class TestContentItem:
    """Test ContentItem model."""

    def test_defaults(self):
        item = ContentItem(platform="linkedin", body="Hello world")
        assert item.hashtags == []
        assert item.call_to_action == ""
        assert item.character_count == 0

    def test_full_item(self):
        item = ContentItem(
            platform="x",
            body="Check out our new product!",
            hashtags=["#AI", "#Tech"],
            call_to_action="Learn more →",
            character_count=26,
            posting_time_suggestion="9:00 AM PST",
        )
        assert len(item.hashtags) == 2
        assert item.posting_time_suggestion == "9:00 AM PST"


class TestReview:
    """Test Review model."""

    def test_defaults(self):
        review = Review()
        assert review.overall_score == 0
        assert review.feedback == []
        assert review.improvements_made == []

    def test_nested_scores(self):
        review = Review(
            overall_score=8.5,
            scores=ReviewScores(brand_alignment=9, clarity=8),
        )
        assert review.scores.brand_alignment == 9


class TestContentOutput:
    """Test ContentOutput model."""

    def test_defaults(self):
        output = ContentOutput()
        assert output.contents == []
        assert output.sources_used == []

    def test_nested_construction(self):
        output = ContentOutput(
            contents=[
                ContentItem(platform="linkedin", body="Post content"),
                ContentItem(platform="x", body="Tweet content"),
            ],
            review=Review(overall_score=8.0),
            sources_used=["bing_search", "file_search"],
        )
        assert len(output.contents) == 2
        assert output.review.overall_score == 8.0
        assert "bing_search" in output.sources_used
