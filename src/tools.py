"""Custom tool definitions for Social AI Studio agent.

Tools are defined with the @tool decorator from agent_framework.
The LLM decides when and how to call these tools based on context.
"""

import asyncio
import json
import logging
from contextvars import ContextVar
from typing import Annotated

from agent_framework import tool
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

from src.config import (
    AZURE_AI_SCOPE,
    IMAGE_DEPLOYMENT_NAME,
    MODEL_DEPLOYMENT_NAME,
    RESPONSES_API_BASE_URL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-request image storage (side-channel via ContextVar + module-level fallback)
# ---------------------------------------------------------------------------
# Images are stored here by the generate_image tool and retrieved by agent.py
# after streaming completes. This avoids sending heavy base64 data through
# the LLM (which wastes tokens and may be truncated by the SDK).
_pending_images: ContextVar[dict[str, str]] = ContextVar("pending_images", default=None)

# Module-level fallback store (used if ContextVar doesn't propagate across
# the agent framework's tool execution context)
_fallback_images: dict[str, str] = {}


def init_image_store() -> None:
    """Initialize the per-request image store.

    Must be called at the start of each agent run so that the
    generate_image tool can store images for later retrieval.
    """
    global _fallback_images
    _pending_images.set({})
    _fallback_images = {}


def pop_pending_images() -> dict[str, str]:
    """Pop and return all pending images from the current request.

    Checks both ContextVar and module-level fallback store.

    Returns:
        Dict mapping platform name to base64 image data.
    """
    global _fallback_images
    cv_store = _pending_images.get(None) or {}
    _pending_images.set({})
    # Merge: fallback takes precedence (it's always written to)
    merged = {**cv_store, **_fallback_images}
    _fallback_images = {}
    if merged:
        logger.info(
            "pop_pending_images: %d image(s) retrieved (cv=%d, fallback=%d)",
            len(merged),
            len(cv_store),
            len(_fallback_images) + len(merged),  # was before clear
        )
    return merged


# Platform character limits and formatting rules
PLATFORM_RULES: dict[str, dict] = {
    "linkedin": {
        "max_chars": 3000,
        "tone": "Professional, data-driven, thought leadership",
        "format": "Use paragraphs, bullet points, and a strong opening hook. Include a CTA.",
        "hashtag_count": "3-5 relevant industry hashtags",
        "image_size": "1200x627",
    },
    "x": {
        "max_chars": 280,
        "tone": "Casual, witty, developer-community voice",
        "format": "Hook in first line. Concise. Use emoji sparingly. Thread format for longer content.",
        "hashtag_count": "1-2 highly relevant hashtags",
        "image_size": "1200x675",
    },
    "instagram": {
        "max_chars": 2200,
        "tone": "Visual-first, approachable, storytelling",
        "format": "Start with a hook. Use emoji. Line breaks for readability. Strong CTA at end.",
        "hashtag_count": "5-10 hashtags (mix of popular and niche)",
        "image_size": "1080x1080",
    },
}


@tool(approval_mode="never_require")
async def generate_content(
    topic: Annotated[str, "The content topic or theme"],
    platform: Annotated[str, "Target platform: linkedin, x, or instagram"],
    strategy: Annotated[str, "Content strategy and key points from analysis"] = "",
    language: Annotated[str, "Output language: en or ja"] = "en",
) -> str:
    """Generate platform-optimized social media content.

    Applies platform-specific character limits, tone, and formatting rules.
    Returns structured content with body text, hashtags, and posting suggestions.
    """
    platform_key = platform.lower().strip()
    rules = PLATFORM_RULES.get(platform_key, PLATFORM_RULES["linkedin"])

    lang_instruction = (
        "Write in natural Japanese appropriate for this platform."
        if language == "ja"
        else "Write in English."
    )

    result = {
        "platform": platform_key,
        "rules_applied": {
            "max_characters": rules["max_chars"],
            "tone": rules["tone"],
            "format": rules["format"],
        },
        "instructions": (
            f"Generate a {platform_key} post about: {topic}. "
            f"Strategy: {strategy}. "
            f"Tone: {rules['tone']}. "
            f"Format: {rules['format']}. "
            f"Max characters: {rules['max_chars']}. "
            f"Include {rules['hashtag_count']}. "
            f"{lang_instruction}"
        ),
        "status": "ready_for_generation",
    }

    logger.info(
        "generate_content called: platform=%s, topic=%s...",
        platform_key,
        topic[:50],
    )
    return json.dumps(result, ensure_ascii=False)


@tool(approval_mode="never_require")
async def review_content(
    content: Annotated[str, "The content text to review"],
    platform: Annotated[str, "Target platform: linkedin, x, or instagram"],
    brand_guidelines: Annotated[str, "Brand guidelines summary for evaluation"] = "",
) -> str:
    """Review and score social media content on 5 quality axes.

    Evaluates: brand_alignment, audience_relevance, engagement_potential,
    clarity, and platform_optimization. Each scored 1-10.
    Returns structured feedback with scores and improvement suggestions.
    """
    platform_key = platform.lower().strip()
    rules = PLATFORM_RULES.get(platform_key, PLATFORM_RULES["linkedin"])
    char_count = len(content)
    max_chars = rules["max_chars"]

    # Basic automated checks
    checks = []
    if char_count > max_chars:
        checks.append(
            f"⚠️ Content exceeds {platform_key} limit: {char_count}/{max_chars} characters"
        )
    if char_count == 0:
        checks.append("⚠️ Content is empty")
    if platform_key == "x" and char_count > 280:
        checks.append("⚠️ X/Twitter post exceeds 280 character limit")
    if "#" not in content:
        checks.append("💡 Consider adding hashtags for discoverability")

    result = {
        "platform": platform_key,
        "character_count": char_count,
        "max_characters": max_chars,
        "automated_checks": checks,
        "review_criteria": {
            "brand_alignment": "Does it match the brand's voice and messaging pillars?",
            "audience_relevance": "Is it relevant to the target audience for this platform?",
            "engagement_potential": "Will it drive likes, shares, comments?",
            "clarity": "Is the message clear and concise?",
            "platform_optimization": f"Is it optimized for {platform_key}'s format and best practices?",
        },
        "brand_guidelines_provided": bool(brand_guidelines),
        "instructions": (
            "Score each criterion 1-10 and provide specific improvement suggestions. "
            "If any score is below 7, suggest concrete revisions."
        ),
    }

    logger.info(
        "review_content called: platform=%s, chars=%d/%d, checks=%d",
        platform_key,
        char_count,
        max_chars,
        len(checks),
    )
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Image generation tool (gpt-image-1.5 via Responses API)
# ---------------------------------------------------------------------------
# The Foundry project endpoint does NOT support the legacy images.generate()
# endpoint. Instead, we use the Responses API with the built-in
# image_generation tool type, specifying the deployment via a custom header.

# Reusable OpenAI client (lazy init with auto-refresh token provider)
_image_client: OpenAI | None = None

# Azure AD token provider — handles caching and automatic refresh
_image_credential = DefaultAzureCredential()
_image_token_provider = get_bearer_token_provider(_image_credential, AZURE_AI_SCOPE)


def _get_image_client() -> OpenAI:
    """Get or create a singleton OpenAI client for image generation.

    Uses the Responses API base URL with:
    - Bearer token auth via get_bearer_token_provider
    - x-ms-oai-image-generation-deployment header for model routing
    - api-version query parameter required by Foundry endpoint
    """
    global _image_client

    if _image_client is not None:
        return _image_client

    _image_client = OpenAI(
        base_url=RESPONSES_API_BASE_URL,
        api_key=_image_token_provider,
        default_headers={
            "x-ms-oai-image-generation-deployment": IMAGE_DEPLOYMENT_NAME,
        },
        default_query={"api-version": "2025-05-15-preview"},
    )
    logger.info(
        "Image client created (Responses API): base_url=%s, deployment=%s",
        RESPONSES_API_BASE_URL,
        IMAGE_DEPLOYMENT_NAME,
    )
    return _image_client


# Platform-specific image sizes (not used in Responses API approach,
# but kept for prompt context)
IMAGE_SIZES: dict[str, str] = {
    "linkedin": "1024x1024",
    "x": "1024x1024",
    "instagram": "1024x1024",
}


@tool(approval_mode="never_require")
async def generate_image(
    prompt: Annotated[str, "Detailed image generation prompt in English"],
    platform: Annotated[str, "Target platform: linkedin, x, or instagram"],
    style: Annotated[
        str, "Visual style: photo, illustration, minimal, abstract"
    ] = "photo",
) -> str:
    """Generate a social media visual using GPT Image (gpt-image-1.5).

    Creates a platform-optimized image from a text prompt using the
    Responses API with the built-in image_generation tool.
    Returns a JSON object with metadata (image data stored via side-channel).
    """
    platform_key = platform.lower().strip()
    size = IMAGE_SIZES.get(platform_key, "1024x1024")

    # Enhance prompt with style and platform context
    enhanced_prompt = (
        f"{prompt}. "
        f"Style: {style}. "
        f"Optimized for {platform_key} social media ({size}). "
        f"Professional, modern, high quality."
    )

    logger.info(
        "generate_image called: platform=%s, style=%s, prompt=%s...",
        platform_key,
        style,
        prompt[:60],
    )

    try:
        client = _get_image_client()

        # Use Responses API with image_generation tool (runs in thread
        # since the OpenAI SDK's sync client blocks the event loop)
        def _sync_generate():
            return client.responses.create(
                model=MODEL_DEPLOYMENT_NAME,
                input=enhanced_prompt,
                tools=[{"type": "image_generation"}],
            )

        response = await asyncio.to_thread(_sync_generate)

        # Extract image data from response output
        image_items = [
            item
            for item in (response.output or [])
            if item.type == "image_generation_call"
        ]

        if not image_items or not getattr(image_items[0], "result", None):
            out_types = [i.type for i in (response.output or [])]
            logger.warning(
                "No image data in response. Output types: %s",
                out_types,
            )
            return json.dumps(
                {
                    "platform": platform_key,
                    "error": "Image generation returned no image data.",
                    "status": "failed",
                },
                ensure_ascii=False,
            )

        image_b64 = image_items[0].result

        # Store image in per-request side-channel (NOT returned to LLM)
        # This avoids sending ~1-2MB of base64 through the model context
        # Write to both ContextVar and module-level fallback for reliability
        store = _pending_images.get(None)
        if store is not None:
            store[platform_key] = image_b64
            logger.info(
                "Image stored in ContextVar: platform=%s, b64_length=%d",
                platform_key,
                len(image_b64) if image_b64 else 0,
            )
        else:
            logger.warning(
                "ContextVar image store not available (tool may be running "
                "in a different context). Using fallback store."
            )

        # Always write to module-level fallback for reliability
        _fallback_images[platform_key] = image_b64
        logger.info(
            "Image stored in fallback: platform=%s, b64_length=%d",
            platform_key,
            len(image_b64) if image_b64 else 0,
        )

        # Return only metadata to the LLM (no heavy base64 data)
        result = {
            "platform": platform_key,
            "size": size,
            "style": style,
            "status": "generated",
            "message": (
                f"Image successfully generated for {platform_key} ({size}). "
                "The image will be automatically displayed in the content card."
            ),
        }

        logger.info(
            "Image generated: platform=%s, size=%s, b64_length=%d",
            platform_key,
            size,
            len(image_b64) if image_b64 else 0,
        )
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(
            "Image generation failed: %s (type=%s, platform=%s, model=%s)",
            e,
            type(e).__name__,
            platform_key,
            IMAGE_DEPLOYMENT_NAME,
            exc_info=True,
        )
        error_result = {
            "platform": platform_key,
            "error": f"Image generation failed: {type(e).__name__}: {e}",
            "status": "failed",
        }
        return json.dumps(error_result, ensure_ascii=False)
