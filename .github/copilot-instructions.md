# Hackfest TechConnect 2026 - Reasoning Agents with Microsoft Foundry

## Project Overview

This is a hackathon project for **Agents League @ TechConnect 2026** — **Reasoning Agents** track.
We are building an AI-powered **social media content creation pipeline** for **TechPulse Inc.** (a technology company) that assists the communication team in creating platform-optimized content for LinkedIn, X/Twitter, and Instagram.

The system features:
- **gpt-5.2** reasoning agent with controllable reasoning depth and thinking display
- **File Search** grounding against brand guidelines via Azure AI Vector Store
- **Web Search** (Bing Grounding) for real-time trend research
- **GPT Image generation** (gpt-image-1.5) for social media visuals
- **Structured JSON output** parsed into platform-specific content cards
- **Real-time SSE streaming** with reasoning process and tool usage visualization
- **Reasoning phase indicators** (CoT → ReAct → Self-Reflection) visible in the UI

Future roadmap includes multi-agent pipeline (Ideation → Creator → Reviewer), MCP Server integration, Foundry Evaluation metrics, and Content Safety filters.

- **Deadline**: Feb 13, 2026 at 11:59 PM PT
- **Platform**: Microsoft Foundry (Azure AI Foundry)
- **Models**: gpt-5.2 (reasoning), gpt-image-1.5 (image generation)
- **SDK**: agent-framework-core (Responses API + @tool decorator)
- **Authentication**: DefaultAzureCredential (Azure CLI login)
- **Language**: Python 3.12 + TypeScript 5
- **Package Manager**: uv (Python), npm (frontend)

## Architecture

```
.
├── .github/              # Copilot instructions & custom rules
├── src/
│   ├── config.py         # Configuration loader (env vars)
│   ├── client.py         # AzureOpenAIResponsesClient singleton + monkey-patch
│   ├── agent.py          # Agent creation, reasoning options, SSE streaming
│   ├── tools.py          # Custom tools (generate_content, review_content, generate_image)
│   ├── vector_store.py   # Vector Store setup & FileSearchTool provisioning
│   ├── models.py         # Pydantic data models (ChatRequest, etc.)
│   ├── prompts/          # System prompt module (external)
│   │   └── system_prompt.py
│   └── api.py            # FastAPI + SSE streaming endpoint
├── frontend/             # React 19 + TypeScript + Vite + Tailwind v3
│   ├── src/
│   │   ├── components/   # InputForm, ContentCard, ReasoningPanel, ToolEvents, SuggestedQuestions
│   │   ├── hooks/        # useTheme, useI18n
│   │   └── lib/          # api.ts (SSE client), i18n.ts (EN/JA/KO/ZH/ES)
│   ├── package.json
│   └── vite.config.ts
├── data/                 # Grounding data
│   └── brand_guidelines.md
├── .env                  # Environment variables (gitignored)
├── .env.example          # Example config with placeholders
├── pyproject.toml        # Python project config (uv)
└── README.md
```

## Key Patterns

### Microsoft Foundry Agent Service (agent-framework-core)

- Use `AzureOpenAIResponsesClient` from `agent_framework.azure` as the main entry point
- Use `DefaultAzureCredential` from `azure.identity` — never hardcode API keys
- Reuse a **singleton** `AzureOpenAIResponsesClient` instance; do not create new instances repeatedly
- Create agents via `client.as_agent(name=..., instructions=..., tools=[...], default_options=...)`
- Pass `default_options={"reasoning": {"effort": ..., "summary": ...}}` to control gpt-5.2 reasoning
- The `OpenAIResponsesOptions` TypedDict supports: `reasoning`, `temperature`, `max_tokens`, `response_format`, etc.
- `ReasoningOptions` TypedDict: `effort` ("low"|"medium"|"high"), `summary` ("auto"|"concise"|"detailed")
- Stream responses via `agent.run(query, stream=True)` → yields `AgentResponseUpdate`
- Define custom tools with `@tool(approval_mode="never_require")` + `Annotated` type hints
- Handle `429 (Request Rate Too Large)` with retry-after logic
- Use async APIs where available for better throughput
- Load `PROJECT_ENDPOINT` and `MODEL_DEPLOYMENT_NAME` from environment variables via `python-dotenv`

### Hosted Tools

- **Web Search**: `AzureOpenAIResponsesClient.get_web_search_tool()` — Bing Grounding for real-time trends
- **File Search**: `AzureOpenAIResponsesClient.get_file_search_tool(vector_store_ids=[...])` — needs Vector Store ID
- **MCP**: `AzureOpenAIResponsesClient.get_mcp_tool(...)` or `MCPStreamableHTTPTool` for MCP server connections

### Vector Store Setup

- Use `openai.resources.VectorStores` via the openai SDK (v2.20+) to create/manage vector stores
- Upload `data/brand_guidelines.md` to a vector store at startup if not already created
- Cache the `VECTOR_STORE_ID` in `.env` after first creation
- Pass `vector_store_ids=[...]` to `get_file_search_tool()`

### Image Generation

- Use `openai.AzureOpenAI` client's `images.generate()` for gpt-image-1.5
- Custom `@tool` named `generate_image` with parameters: `prompt`, `platform`, `style`
- Returns base64 image data that the frontend displays in content cards
- Deployment name: `gpt-image-1.5`

### Reasoning Patterns

All three reasoning patterns are integrated into a **single system prompt**:

1. **Chain-of-Thought (CoT)**: Strategic analysis phase — step-by-step topic analysis
2. **ReAct (Reasoning + Acting)**: Content creation phase — tool use + reasoning
3. **Self-Reflection**: Quality review phase — self-evaluate and improve

The single agent autonomously progresses through all phases.

### Agent Design (Single Agent + Multi-Tool)

- **Architecture**: One agent with 5+ tools
- Hosted tools: `web_search` (Bing Grounding), `file_search` (Vector Store)
- Custom tools: `generate_content`, `review_content`, `generate_image`
- All custom tools use `@tool(approval_mode="never_require")` decorator with `Annotated` parameters
- Agent created via `AzureOpenAIResponsesClient.as_agent()` — Responses API v1
- The LLM decides which tools to use and in what order based on context
- System prompt embeds CoT + ReAct + Self-Reflection directives
- System prompt instructs structured JSON output for platform-specific content

### SSE Streaming Design

- Stream reasoning tokens, tool events, and text content via SSE
- Use `__TOOL_EVENT__` / `__END_TOOL_EVENT__` markers (from fabric-foundry-agentic-starter)
- Use `__REASONING_REPLACE__` / `__END_REASONING_REPLACE__` markers for cumulative reasoning
- Event types: `reasoning`, `tool_start`, `tool_end`, `text`, `done`, `error`
- Frontend displays reasoning in collapsible panels and tool usage in timeline

### Frontend Features

- 🧠 Reasoning process display (collapsible ReasoningIndicator — purple/indigo gradient)
- 🔧 Tool usage pills (always-visible animated badges with gradient glow — Web Search, File Search, etc.)
- 📊 Quality radar chart (recharts RadarChart — 5-axis scoring with overall score gradient)
- 🛡️ Content Safety badge (visual indicator for safety-checked content)
- 📈 Processing metrics (reasoning chars, tools used, output chars — post-generation stats bar)
- ⚙️ AI Settings panel (reasoning effort: low/medium/high, reasoning summary: off/auto/concise/detailed)
- 💡 Suggested questions (empty-state grid with clickable samples)
- 🖼️ Platform-specific content cards (LinkedIn / X / Instagram) with images
- 📋 Per-platform copy to clipboard
- 🌐 i18n (EN/JA/KO/ZH/ES) for UI labels and content generation
- 🌙 Dark/Light mode (Tailwind dark: classes)
- 📝 Markdown rendering (react-markdown)
- ✨ Glassmorphism UI (frosted glass cards, backdrop blur, gradient backgrounds)
- 🎨 Gradient design system (submit button, header, animated borders)

## Coding Standards

### Python Conventions

- Follow **PEP 8** style guide
- Use **type hints** on all function signatures
- Write **docstrings** (PEP 257) for all public functions and classes
- Use `logging` module instead of `print()` for diagnostics
- Handle exceptions gracefully with specific exception types
- Use `pathlib.Path` for file path operations
- Prefer f-strings for string formatting

### Project Conventions

- Use `uv` for dependency management (not pip directly)
- Store configuration in `.env` files, load with `python-dotenv`
- Never commit secrets, API keys, or Azure subscription details
- All code should be in the `src/` directory
- Keep the main entry point clean and delegate to modules

### Security (CRITICAL — Public Repository)

- ❌ **NEVER** include API keys, passwords, tokens, or credentials in code
- ❌ **NEVER** include customer data or PII
- ❌ **NEVER** include Azure subscription IDs, resource names, or connection strings
- ✅ Use environment variables for all sensitive configuration
- ✅ Use `DefaultAzureCredential` for authentication
- ✅ Keep `.env` in `.gitignore`
- ✅ Provide `.env.example` with placeholder values only

## Judging Criteria

Projects are evaluated on:
1. **Accuracy & Relevance (25%)** — Meets challenge requirements
2. **Reasoning & Multi-step Thinking (25%)** — Clear problem-solving approach
3. **Creativity & Originality (20%)** — Novel ideas or unexpected execution
4. **User Experience & Presentation (15%)** — Clear documentation, screenshots/video
5. **Technical Implementation (15%)** — Solid patterns, creative use of tools

## Quick Reference Links

- [Foundry Agent Service Overview](https://learn.microsoft.com/azure/ai-foundry/agents/overview?view=foundry)
- [Quickstart: Create agent with Python SDK](https://learn.microsoft.com/azure/ai-foundry/agents/quickstart-sdk?view=foundry-classic&pivots=python-sdk)
- [File Search tool](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/file-search?view=foundry&pivots=python)
- [Bing Search tool](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/bing-tools?view=foundry&pivots=python)
- [Microsoft Learn MCP Server](https://github.com/microsoftdocs/mcp)
