"""Tests for src/config.py — environment variable loading and defaults."""

import os


class TestConfigDefaults:
    """Verify default values when environment variables are not set."""

    def test_model_deployment_name_default(self):
        from src.config import MODEL_DEPLOYMENT_NAME

        # Default should be "gpt-5.2"
        assert MODEL_DEPLOYMENT_NAME == os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.2")

    def test_image_deployment_name_default(self):
        from src.config import IMAGE_DEPLOYMENT_NAME

        assert IMAGE_DEPLOYMENT_NAME == os.getenv("IMAGE_DEPLOYMENT_NAME", "gpt-image-1.5")

    def test_port_is_integer(self):
        from src.config import PORT

        assert isinstance(PORT, int)

    def test_debug_is_bool(self):
        from src.config import DEBUG

        assert isinstance(DEBUG, bool)

    def test_azure_ai_scope_constant(self):
        from src.config import AZURE_AI_SCOPE

        assert AZURE_AI_SCOPE == "https://ai.azure.com/.default"

    def test_cosmos_database_default(self):
        from src.config import COSMOS_DATABASE

        assert COSMOS_DATABASE == os.getenv("COSMOS_DATABASE", "social-ai-studio")

    def test_cosmos_container_default(self):
        from src.config import COSMOS_CONTAINER

        assert COSMOS_CONTAINER == os.getenv("COSMOS_CONTAINER", "conversations")

    def test_ai_search_reasoning_effort_default(self):
        from src.config import AI_SEARCH_REASONING_EFFORT

        assert AI_SEARCH_REASONING_EFFORT == os.getenv("AI_SEARCH_REASONING_EFFORT", "minimal")


class TestConfigDerived:
    """Verify derived configuration values."""

    def test_responses_api_base_url_empty_without_endpoint(self):
        from src.config import PROJECT_ENDPOINT, RESPONSES_API_BASE_URL

        if not PROJECT_ENDPOINT:
            assert RESPONSES_API_BASE_URL == ""
        else:
            assert RESPONSES_API_BASE_URL == f"{PROJECT_ENDPOINT}/openai/v1/"

    def test_responses_api_base_url_format(self):
        from src.config import PROJECT_ENDPOINT, RESPONSES_API_BASE_URL

        if PROJECT_ENDPOINT:
            assert RESPONSES_API_BASE_URL.endswith("/openai/v1/")
            assert RESPONSES_API_BASE_URL.startswith(PROJECT_ENDPOINT)

    def test_host_default(self):
        from src.config import HOST

        assert HOST == os.getenv("HOST", "0.0.0.0")
