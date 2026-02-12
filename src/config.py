"""Configuration loader for TechPulse Social.

Loads environment variables from .env and exposes them as module-level constants.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# Azure AI Foundry
PROJECT_ENDPOINT: str = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT_NAME: str = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-5.2")
IMAGE_DEPLOYMENT_NAME: str = os.getenv("IMAGE_DEPLOYMENT_NAME", "gpt-image-1.5")

# Vector Store (cached after first creation)
VECTOR_STORE_ID: str = os.getenv("VECTOR_STORE_ID", "")

# Foundry IQ / Azure AI Search
AI_SEARCH_ENDPOINT: str = os.getenv("AI_SEARCH_ENDPOINT", "")
AI_SEARCH_KNOWLEDGE_BASE_NAME: str = os.getenv("AI_SEARCH_KNOWLEDGE_BASE_NAME", "")
AI_SEARCH_API_KEY: str = os.getenv("AI_SEARCH_API_KEY", "")
AI_SEARCH_REASONING_EFFORT: str = os.getenv("AI_SEARCH_REASONING_EFFORT", "low")

# MCP Server (Microsoft Learn)
MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "https://learn.microsoft.com/api/mcp")

# Azure Cosmos DB
COSMOS_ENDPOINT: str = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "techpulse-social")
COSMOS_CONTAINER: str = os.getenv("COSMOS_CONTAINER", "conversations")

# Azure AI token scope (shared across client.py, tools.py, agentic_retrieval.py)
AZURE_AI_SCOPE: str = "https://ai.azure.com/.default"

# Derived: Responses API base URL
# Format: https://<endpoint>/openai/v1/
RESPONSES_API_BASE_URL: str = (
    f"{PROJECT_ENDPOINT}/openai/v1/" if PROJECT_ENDPOINT else ""
)

# Server
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))

# Observability (OpenTelemetry + Application Insights)
APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
)
OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "techpulse-social")

# Evaluation
EVAL_MODEL_DEPLOYMENT: str = os.getenv("EVAL_MODEL_DEPLOYMENT", "gpt-4o-mini")

# Content Safety
CONTENT_SAFETY_ENDPOINT: str = os.getenv("CONTENT_SAFETY_ENDPOINT", "")

# Feature flags
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
SERVE_STATIC: bool = os.getenv("SERVE_STATIC", "false").lower() == "true"
