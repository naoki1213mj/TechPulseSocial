"""Pydantic data models for TechPulse Social API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    message: str = Field(..., description="User input text")
    thread_id: str | None = Field(
        None,
        description="Thread ID for multi-turn conversation (null for first message)",
    )
    platforms: list[str] = Field(
        default=["linkedin", "x", "instagram"],
        description="Target platforms",
    )
    content_type: str = Field(
        default="product_launch",
        description="Content type: product_launch, blog_summary, event, hiring, trend, thought_leadership",
    )
    language: str = Field(default="en", description="Output language: en or ja")
    reasoning_effort: str = Field(
        default="medium",
        description="GPT-5 reasoning depth: low, medium, high",
    )
    reasoning_summary: str = Field(
        default="auto",
        description="Thinking display: off, auto, concise, detailed",
    )
    ab_mode: bool = Field(
        default=False,
        description="A/B comparison mode: generate two content variants with different strategies",
    )


class ToolEvent(BaseModel):
    """Real-time tool event for SSE streaming."""

    type: str = Field(..., description="Event type: tool_event")
    tool: str = Field(..., description="Tool name")
    status: str = Field(..., description="started, completed, or error")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: str | None = Field(None, description="Optional message")


class ContentItem(BaseModel):
    """Generated content for a single platform."""

    platform: str
    body: str
    hashtags: list[str] = []
    call_to_action: str = ""
    character_count: int = 0
    posting_time_suggestion: str = ""


class ReviewScores(BaseModel):
    """Quality review scores on 5 axes."""

    brand_alignment: float = Field(0, ge=0, le=10)
    audience_relevance: float = Field(0, ge=0, le=10)
    engagement_potential: float = Field(0, ge=0, le=10)
    clarity: float = Field(0, ge=0, le=10)
    platform_optimization: float = Field(0, ge=0, le=10)


class Review(BaseModel):
    """Quality review results."""

    overall_score: float = Field(0, ge=0, le=10)
    scores: ReviewScores = ReviewScores()
    feedback: list[str] = []
    improvements_made: list[str] = []


class ContentOutput(BaseModel):
    """Final structured output from the agent."""

    contents: list[ContentItem] = []
    review: Review = Review()
    sources_used: list[str] = []
