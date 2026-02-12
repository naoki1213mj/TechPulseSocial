"""Tests for src/tools.py — custom agent tool functions."""

import json

import pytest

from src.tools import PLATFORM_RULES, generate_content, review_content


class TestPlatformRules:
    """Test platform rule definitions."""

    def test_all_platforms_defined(self):
        assert "linkedin" in PLATFORM_RULES
        assert "x" in PLATFORM_RULES
        assert "instagram" in PLATFORM_RULES

    def test_required_fields(self):
        for platform, rules in PLATFORM_RULES.items():
            assert "max_chars" in rules, f"{platform} missing max_chars"
            assert "tone" in rules, f"{platform} missing tone"
            assert "format" in rules, f"{platform} missing format"
            assert "hashtag_count" in rules, f"{platform} missing hashtag_count"
            assert "image_size" in rules, f"{platform} missing image_size"

    def test_x_character_limit(self):
        assert PLATFORM_RULES["x"]["max_chars"] == 280

    def test_linkedin_character_limit(self):
        assert PLATFORM_RULES["linkedin"]["max_chars"] == 3000

    def test_instagram_character_limit(self):
        assert PLATFORM_RULES["instagram"]["max_chars"] == 2200


class TestGenerateContent:
    """Test generate_content tool."""

    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        result = await generate_content(topic="AI launch", platform="linkedin")
        data = json.loads(result)
        assert "platform" in data
        assert "instructions" in data
        assert "rules_applied" in data
        assert data["status"] == "ready_for_generation"

    @pytest.mark.asyncio
    async def test_platform_normalization(self):
        result = await generate_content(topic="test", platform="  LinkedIn  ")
        data = json.loads(result)
        assert data["platform"] == "linkedin"

    @pytest.mark.asyncio
    async def test_rules_applied(self):
        result = await generate_content(topic="test", platform="x")
        data = json.loads(result)
        assert data["rules_applied"]["max_characters"] == 280

    @pytest.mark.asyncio
    async def test_language_instruction_en(self):
        result = await generate_content(
            topic="test", platform="linkedin", language="en"
        )
        data = json.loads(result)
        assert "English" in data["instructions"]

    @pytest.mark.asyncio
    async def test_language_instruction_ja(self):
        result = await generate_content(
            topic="test", platform="linkedin", language="ja"
        )
        data = json.loads(result)
        assert "Japanese" in data["instructions"]

    @pytest.mark.asyncio
    async def test_fallback_to_linkedin_rules(self):
        result = await generate_content(topic="test", platform="unknown_platform")
        data = json.loads(result)
        # Unknown platform falls back to LinkedIn rules
        assert data["rules_applied"]["max_characters"] == 3000

    @pytest.mark.asyncio
    async def test_strategy_included(self):
        result = await generate_content(
            topic="AI launch",
            platform="linkedin",
            strategy="Focus on ROI and enterprise value",
        )
        data = json.loads(result)
        assert "ROI" in data["instructions"]


class TestReviewContent:
    """Test review_content tool."""

    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        result = await review_content(
            content="Great product launch!", platform="linkedin"
        )
        data = json.loads(result)
        assert "platform" in data
        assert "character_count" in data
        assert "automated_checks" in data
        assert "review_criteria" in data

    @pytest.mark.asyncio
    async def test_empty_content_warning(self):
        result = await review_content(content="", platform="linkedin")
        data = json.loads(result)
        checks = data["automated_checks"]
        assert any("empty" in c.lower() for c in checks)

    @pytest.mark.asyncio
    async def test_over_limit_warning(self):
        long_content = "a" * 300
        result = await review_content(content=long_content, platform="x")
        data = json.loads(result)
        checks = data["automated_checks"]
        assert any("exceeds" in c.lower() or "280" in c for c in checks)

    @pytest.mark.asyncio
    async def test_missing_hashtags_suggestion(self):
        result = await review_content(content="No tags here", platform="linkedin")
        data = json.loads(result)
        checks = data["automated_checks"]
        assert any("hashtag" in c.lower() for c in checks)

    @pytest.mark.asyncio
    async def test_content_with_hashtags_no_warning(self):
        result = await review_content(
            content="Great product! #AI #Tech", platform="linkedin"
        )
        data = json.loads(result)
        checks = data["automated_checks"]
        assert not any("hashtag" in c.lower() for c in checks)

    @pytest.mark.asyncio
    async def test_character_count_accurate(self):
        content = "Hello World"
        result = await review_content(content=content, platform="linkedin")
        data = json.loads(result)
        assert data["character_count"] == len(content)

    @pytest.mark.asyncio
    async def test_brand_guidelines_flag(self):
        result = await review_content(
            content="test",
            platform="linkedin",
            brand_guidelines="Be professional and tech-forward",
        )
        data = json.loads(result)
        assert data["brand_guidelines_provided"] is True

    @pytest.mark.asyncio
    async def test_no_brand_guidelines_flag(self):
        result = await review_content(content="test", platform="linkedin")
        data = json.loads(result)
        assert data["brand_guidelines_provided"] is False
