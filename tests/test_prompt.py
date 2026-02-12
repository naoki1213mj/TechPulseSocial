"""Tests for src/prompts/system_prompt.py — A/B mode prompt generation."""

from src.prompts.system_prompt import (
    _AB_MODE_ADDENDUM,
    _BASE_PROMPT,
    SYSTEM_PROMPT,
    get_system_prompt,
)


class TestGetSystemPrompt:
    """Test get_system_prompt function."""

    def test_default_returns_base_prompt(self):
        prompt = get_system_prompt()
        assert prompt == _BASE_PROMPT
        assert "A/B COMPARISON MODE" not in prompt

    def test_ab_mode_false_returns_base(self):
        prompt = get_system_prompt(ab_mode=False)
        assert prompt == _BASE_PROMPT
        assert "variant_a" not in prompt

    def test_ab_mode_true_includes_addendum(self):
        prompt = get_system_prompt(ab_mode=True)
        assert "A/B COMPARISON MODE" in prompt
        assert "variant_a" in prompt
        assert "variant_b" in prompt
        assert "strategy" in prompt

    def test_ab_mode_preserves_base(self):
        prompt = get_system_prompt(ab_mode=True)
        # Base prompt content should still be there
        assert "TechPulse Inc." in prompt
        assert "Chain-of-Thought" in prompt
        assert "ReAct" in prompt
        assert "Self-Reflection" in prompt

    def test_backward_compat_constant(self):
        """SYSTEM_PROMPT constant should equal base prompt."""
        assert SYSTEM_PROMPT == _BASE_PROMPT

    def test_ab_addendum_has_json_example(self):
        assert '"mode": "ab"' in _AB_MODE_ADDENDUM
        assert '"variant_a"' in _AB_MODE_ADDENDUM
        assert '"variant_b"' in _AB_MODE_ADDENDUM

    def test_mcp_instruction_in_base(self):
        """MCP tool usage should be mentioned in base prompt."""
        assert "microsoft_learn" in _BASE_PROMPT or "MCP" in _BASE_PROMPT
