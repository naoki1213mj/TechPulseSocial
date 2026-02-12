"""Content Safety module for TechPulse Social.

Integrates Azure AI Content Safety to analyze generated content
and user inputs for harmful content and prompt injection attacks.

Features:
- Text content analysis (Hate, SelfHarm, Sexual, Violence categories)
- Prompt shield (detects prompt injection / jailbreak attempts)
- Graceful fallback when Content Safety endpoint is not configured

Usage:
    from src.content_safety import analyze_safety, check_prompt_shield

    # Analyze generated content
    result = await analyze_safety("Some text to check")
    # → {"safe": True, "categories": {...}, "severity_levels": {...}}

    # Check user input for prompt injection
    shield = await check_prompt_shield("user message", "system prompt")
    # → {"safe": True, "attack_detected": False}
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy imports for optional dependency
_client = None
_configured: bool | None = None


def is_configured() -> bool:
    """Check if Content Safety is available and configured."""
    global _configured
    if _configured is not None:
        return _configured

    try:
        from azure.ai.contentsafety import ContentSafetyClient  # noqa: F401

        from src.config import CONTENT_SAFETY_ENDPOINT

        _configured = bool(CONTENT_SAFETY_ENDPOINT)
        if not _configured:
            logger.info(
                "Content Safety: CONTENT_SAFETY_ENDPOINT not set, safety checks disabled"
            )
    except ImportError:
        logger.info(
            "Content Safety: azure-ai-contentsafety not installed, safety checks disabled"
        )
        _configured = False

    return _configured


def _get_client():
    """Get or create Content Safety client (singleton)."""
    global _client
    if _client is not None:
        return _client

    from azure.ai.contentsafety import ContentSafetyClient
    from azure.identity import DefaultAzureCredential

    from src.config import CONTENT_SAFETY_ENDPOINT

    _client = ContentSafetyClient(
        endpoint=CONTENT_SAFETY_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    logger.info("Content Safety client initialized: %s", CONTENT_SAFETY_ENDPOINT)
    return _client


async def analyze_safety(text: str) -> dict[str, Any]:
    """Analyze text for harmful content using Azure AI Content Safety.

    Checks four categories: Hate, SelfHarm, Sexual, Violence.
    Each category returns a severity level (0=safe, 2=low, 4=medium, 6=high).

    Args:
        text: The text content to analyze.

    Returns:
        Dict with:
        - safe (bool): True if all categories are below threshold
        - categories (dict): Category → severity mapping
        - blocked_categories (list): Categories that exceeded threshold
    """
    if not is_configured():
        return {
            "safe": True,
            "categories": {},
            "blocked_categories": [],
            "skipped": True,
            "reason": "Content Safety not configured",
        }

    try:
        from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory

        client = _get_client()

        # Truncate to API limit (10K characters per request)
        truncated = text[:10000] if len(text) > 10000 else text

        request = AnalyzeTextOptions(
            text=truncated,
            categories=[
                TextCategory.HATE,
                TextCategory.SELF_HARM,
                TextCategory.SEXUAL,
                TextCategory.VIOLENCE,
            ],
        )

        response = client.analyze_text(request)

        categories = {}
        blocked = []
        # Severity threshold: block at 2+ (low or higher)
        severity_threshold = 2

        for item in response.categories_analysis:
            cat_name = (
                item.category.value
                if hasattr(item.category, "value")
                else str(item.category)
            )
            severity = item.severity or 0
            categories[cat_name] = severity
            if severity >= severity_threshold:
                blocked.append(cat_name)

        is_safe = len(blocked) == 0

        logger.info(
            "Content Safety analysis: safe=%s, categories=%s",
            is_safe,
            categories,
        )

        return {
            "safe": is_safe,
            "categories": categories,
            "blocked_categories": blocked,
        }

    except Exception as e:
        logger.warning("Content Safety analysis failed: %s", e)
        return {
            "safe": True,
            "categories": {},
            "blocked_categories": [],
            "skipped": True,
            "reason": f"Analysis failed: {e}",
        }


async def check_prompt_shield(
    user_input: str,
    system_prompt: str = "",
) -> dict[str, Any]:
    """Check user input for prompt injection attacks.

    Uses Azure AI Content Safety Prompt Shield to detect:
    - Direct prompt injection (user tries to override system instructions)
    - Indirect prompt injection (embedded in external data)

    Args:
        user_input: The user's message to check.
        system_prompt: The system prompt (optional, for context).

    Returns:
        Dict with:
        - safe (bool): True if no attack detected
        - attack_detected (bool): True if prompt injection found
        - details (dict): Detailed analysis results
    """
    if not is_configured():
        return {
            "safe": True,
            "attack_detected": False,
            "skipped": True,
            "reason": "Content Safety not configured",
        }

    try:
        from azure.ai.contentsafety.models import ShieldPromptOptions, TextContent

        client = _get_client()

        documents = [TextContent(text=user_input)]
        options = ShieldPromptOptions(
            user_prompt_content=documents,
        )

        response = client.shield_prompt(options)

        # Check if attack was detected in user prompt
        user_attack = False
        if response.user_prompt_analysis:
            user_attack = response.user_prompt_analysis.attack_detected or False

        logger.info(
            "Prompt Shield: attack_detected=%s",
            user_attack,
        )

        return {
            "safe": not user_attack,
            "attack_detected": user_attack,
        }

    except Exception as e:
        logger.warning("Prompt Shield check failed: %s", e)
        return {
            "safe": True,
            "attack_detected": False,
            "skipped": True,
            "reason": f"Shield check failed: {e}",
        }


def format_safety_summary(result: dict[str, Any]) -> str:
    """Format safety analysis result as human-readable summary.

    Args:
        result: Output from analyze_safety().

    Returns:
        Formatted summary string.
    """
    if result.get("skipped"):
        return f"⚠️ Safety check skipped: {result.get('reason', 'unknown')}"

    if result["safe"]:
        cats = result.get("categories", {})
        cat_str = ", ".join(f"{k}={v}" for k, v in cats.items())
        return f"✅ Content Safe — All categories clear ({cat_str})"

    blocked = result.get("blocked_categories", [])
    return f"🚫 Content Blocked — Flagged categories: {', '.join(blocked)}"
