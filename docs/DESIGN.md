# DESIGN.md — アーキテクチャ設計書

## 1. システムアーキテクチャ

```
┌──────────────────────────────────────────────────────────────┐
│         Frontend (React + TypeScript + Tailwind + shadcn/ui) │
│  🌐 i18n (EN/JA)  🌙 Dark/Light Mode  💬 Multi-turn Chat   │
│  🧠 Reasoning Display  🔧 Tool Viz  📋 Copy  📝 Markdown   │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST API + SSE (Server-Sent Events)
                            │ __TOOL_EVENT__ / __REASONING__ markers
┌───────────────────────────▼──────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  POST /api/chat — Streaming Response (SSE)                   │
│  GET  /api/health                                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │        Single Agent + Multi-Tool (multi_tool mode)     │  │
│  │                                                        │  │
│  │   System Prompt (Reasoning Directives)                 │  │
│  │     ├── CoT: 戦略立案の段階的思考                      │  │
│  │     ├── ReAct: ツール使用 + 推論                       │  │
│  │     └── Self-Reflection: 品質自己評価・改善            │  │
│  │                                                        │  │
│  │   Tools:                                               │  │
│  │     ├── 🔍 web_search (WebSearchPreviewTool)           │  │
│  │     ├── 📄 file_search (FileSearchTool)                │  │
│  │     ├── ✍️  generate_content (@tool custom)             │  │
│  │     └── 📊 review_content (@tool custom)               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │  AzureOpenAIResponsesClient (Singleton) │                │
│  │  agent-framework-core (Responses API)   │                │
│  └─────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐   ┌──────────────┐   ┌──────────┐
      │ File     │   │ Web Search   │   │ Custom   │
      │ Search   │   │ Preview      │   │ Tools    │
      │(Brand    │   │(Bing/Trends) │   │(generate │
      │ Guide)   │   │ gpt-5 対応   │   │ /review) │
      └──────────┘   └──────────────┘   └──────────┘
```

## 2. 単一エージェント + マルチツール設計

### 設計思想

過去リポジトリ (fabric-foundry-agentic-starter) の `multi_tool` モードを踏襲。
**`agent-framework-core` SDK の `AzureOpenAIResponsesClient` + `@tool` デコレータを使用。**

利点:

- `@tool(approval_mode="never_require")` + `Annotated` で型安全なツール定義
- `client.as_agent()` → `agent.run_stream()` のシンプルなストリーミング
- LLM が全コンテキストを保持したまま一貫した判断
- エージェント間のデータ受け渡しオーバーヘッドなし
- 推論プロセス（thinking）がフロントエンドで一元表示可能
- 過去リポジトリと同一パターン → 実績あり
- ハッカソンの100分制限内で確実に動作

### エージェント処理フロー

```
  User Message (topic, platforms, content_type, context)
      │
      ▼
  ┌─ Agent (gpt-5.2 reasoning) ──────────────────────────┐
  │                                                       │
  │  🧠 Thinking (Step 1): トピック分析・戦略立案         │
  │      ├── CoT で段階的に思考                           │
  │      └── → reasoning tokens をフロントへストリーム     │
  │                                                       │
  │  🔧 Tool Call: file_search("brand guidelines")        │
  │      └── → __TOOL_EVENT__ でフロントへ通知             │
  │                                                       │
  │  🔧 Tool Call: web_search("latest AI trends 2026")    │
  │      └── → __TOOL_EVENT__ でフロントへ通知             │
  │                                                       │
  │  🧠 Thinking (Step 2): 情報統合・コンテンツ構成       │
  │      └── ReAct: 検索結果を基にコンテンツ構想          │
  │                                                       │
  │  🔧 Tool Call: generate_content(strategy, platform)    │
  │      └── プラットフォーム別に最適化されたテキスト生成   │
  │                                                       │
  │  🧠 Thinking (Step 3): 品質自己評価                   │
  │      └── Self-Reflection: 5軸で自己評価・改善          │
  │                                                       │
  │  🔧 Tool Call: review_content(draft, guidelines)       │
  │      └── スコアリング + フィードバック生成              │
  │                                                       │
  │  📤 Final Output: JSON (contents + scores + feedback)  │
  └───────────────────────────────────────────────────────┘
```

### ツール一覧

| ツール名 | 種別 | 説明 |
|----------|------|------|
| `web_search` | `WebSearchPreviewTool` (Hosted) | リアルタイムのトレンド・ニュース検索。gpt-5 対応（BingGroundingAgentTool は非対応） |
| `file_search` | `FileSearchTool` (Hosted) | ブランドガイドライン・社内資料の検索。Vector Store に格納 |
| `generate_content` | `@tool` (Custom) | プラットフォーム別の文字数制約・フォーマット最適化を適用してコンテンツ生成 |
| `review_content` | `@tool` (Custom) | 5軸品質スコアリング（brand_alignment, audience_relevance, engagement_potential, clarity, platform_optimization）+ 改善提案 |
| `generate_image` | `@tool` (Custom) | gpt-image-1.5 でプラットフォーム最適化されたビジュアルを生成。base64 でフロントエンドに返却 |

### Human-in-the-Loop (HITL) ワークフロー

生成されたコンテンツに対して、プラットフォームごとに以下のアクションが可能：

1. **承認 (Approve)** — コンテンツを確認済みとしてマーク
2. **編集 (Edit)** — インライン テキスト編集（textarea で直接修正、保存/キャンセル）
3. **改善 (Refine)** — 自然言語でフィードバックを入力 → AI エージェントに再送信

Refine は同じスレッドにフォローアップメッセージを送信し、指定プラットフォームのコンテンツのみを改善。
会話コンテキストが保持されるため、トピックや他プラットフォームの内容は維持される。

### コンテンツエクスポート

- **Markdown (.md)** — 全プラットフォームのコンテンツ + ハッシュタグ + CTA + 品質スコア + ソースを構造化された .md ファイルとしてダウンロード
- **JSON** — 構造化出力をそのまま JSON としてダウンロード（CMS 連携やツール統合用）

### マルチターン対応

- Thread ID をフロントエンド側で保持
- 「もっとカジュアルにして」「Xの投稿だけ変えて」等のリファイン対話に対応
- 会話履歴はセッション内のみ（永続化なし — ハッカソンスコープ）

## 3. データモデル

### 3.1 ChatRequest（API リクエスト）

```json
{
  "message": "string (ユーザー入力テキスト)",
  "thread_id": "string | null (マルチターン用、初回は null)",
  "platforms": ["linkedin", "x", "instagram"],
  "content_type": "product_launch | blog_summary | event | hiring | trend | thought_leadership",
  "language": "en | ja"
}
```

### 3.2 SSE ストリームイベント

過去リポジトリの `__TOOL_EVENT__` / `__END_TOOL_EVENT__` マーカー方式を踏襲。

```
# 推論トークン（thinking）
data: {"type": "reasoning", "content": "トピックを分析中..."}

# ツール呼び出し開始
data: {"type": "tool_start", "tool": "web_search", "input": {"query": "AI trends 2026"}}

# ツール結果
data: {"type": "tool_end", "tool": "web_search", "output": "...", "duration_ms": 1200}

# テキストストリーム
data: {"type": "text", "content": "生成されたコンテンツ...", "thread_id": "thread_abc123"}

# 完了
data: {"type": "done", "thread_id": "thread_abc123"}

# エラー
data: {"type": "error", "message": "Rate limit exceeded", "retry_after": 5}
```

### 3.3 ContentOutput（最終出力 JSON）

エージェントの最終出力はマークダウン形式 + 構造化 JSON のハイブリッド。
フロントエンドでマークダウンレンダリングしつつ、コピー機能にはプレーンテキストを提供。

```json
{
  "contents": [
    {
      "platform": "linkedin | x | instagram",
      "body": "string (マークダウン対応)",
      "hashtags": ["string"],
      "call_to_action": "string",
      "character_count": "number",
      "posting_time_suggestion": "string"
    }
  ],
  "review": {
    "overall_score": "number (1-10)",
    "scores": {
      "brand_alignment": "number (1-10)",
      "audience_relevance": "number (1-10)",
      "engagement_potential": "number (1-10)",
      "clarity": "number (1-10)",
      "platform_optimization": "number (1-10)"
    },
    "feedback": ["string"],
    "improvements_made": ["string"]
  },
  "sources_used": ["string (Web検索で参照したURL等)"]
}
```

## 4. 推論パターン設計（単一プロンプトに統合）

gpt-5.2 の推論能力を活用し、**1つのシステムプロンプト内に 3つの推論パターンを組み込む。**

```text
========================================================
システムプロンプト — TechPulse Social Content Agent
========================================================

# Role
You are an expert social media content strategist and creator
for TechPulse Inc., a technology company.

# Reasoning Process
Follow these 3 phases for EVERY content request:

## Phase 1: Strategic Analysis (Chain-of-Thought)
Think step-by-step:
1. Analyze the core topic and its significance
2. Identify the target audience for each platform
3. Determine the key message and unique angles
4. Plan platform-specific strategies

Show your thinking explicitly in your response.

## Phase 2: Content Creation (ReAct)
For each platform:
- Thought: What approach works best for this platform?
- Action: Use web_search to find latest trends/data
- Action: Use file_search to check brand guidelines
- Action: Use generate_content to create optimized text
- Observation: Verify alignment with strategy

## Phase 3: Quality Review (Self-Reflection)
Before delivering:
- Evaluate each piece on 5 axes (1-10):
  brand_alignment, audience_relevance,
  engagement_potential, clarity, platform_optimization
- If any score < 7, revise and re-evaluate
- Use review_content tool for structured scoring

# Output Format
Return content in Markdown format with structured JSON
for each platform's content and quality scores.

# Platform Guidelines
- LinkedIn: Professional, data-driven, 3000 char max
- X/Twitter: Casual, witty, dev-community voice, 280 char
- Instagram: Visual-first, approachable, 2200 char caption

# Language
Generate content in the language specified by the user.
Default: English. Support: English, Japanese.
```

### 推論トークンの取得

gpt-5.2 は Responses API で `reasoning` フィールドに推論過程を出力。
これを SSE ストリームでフロントエンドに配信し、折りたたみ UI で表示する。

```python
from agent_framework import tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from typing import Annotated

# クライアント初期化
client = AzureOpenAIResponsesClient(
    base_url=f"{PROJECT_ENDPOINT}/openai/v1/",
    deployment_name="gpt-5.2",
    credential=DefaultAzureCredential(),
)

# カスタムツール定義
@tool(approval_mode="never_require")
async def generate_content(
    topic: Annotated[str, "コンテンツのトピック"],
    platform: Annotated[str, "対象プラットフォーム (linkedin/x/instagram)"],
    language: Annotated[str, "出力言語 (en/ja)"] = "en",
) -> str:
    """プラットフォーム別に最適化されたコンテンツを生成する"""
    ...

@tool(approval_mode="never_require")
async def review_content(
    content: Annotated[str, "レビュー対象のコンテンツ"],
    platform: Annotated[str, "対象プラットフォーム"],
) -> str:
    """コンテンツを5軸で品質評価しフィードバックを提供する"""
    ...

# エージェント作成 & ストリーミング
agent = client.as_agent(
    name="techpulse_social_agent",
    instructions=SYSTEM_PROMPT,
    tools=[generate_content, review_content],  # + web_search, file_search
)

async for output in stream_with_tool_events(agent.run_stream(query)):
    yield output
```

## 5. ディレクトリ構造（最終版）

```
hackfest-techconnect2026/
├── .github/
│   ├── copilot-instructions.md
│   └── instructions/
│       ├── python-foundry.instructions.md
│       └── security.instructions.md
├── src/
│   ├── __init__.py
│   ├── config.py              # 設定ローダー
│   ├── client.py              # AzureOpenAIResponsesClient シングルトン
│   ├── tools.py               # カスタムツール定義 (generate_content, review_content)
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system_prompt.py   # システムプロンプト（外部モジュール化）
│   ├── agent.py               # エージェント作成・実行ロジック
│   ├── models.py              # データモデル（Pydantic）
│   └── api.py                 # FastAPI + SSE ストリーミング
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # メインアプリ + テーマプロバイダー
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx      # チャットパネル（マルチターン）
│   │   │   ├── InputForm.tsx      # トピック入力フォーム
│   │   │   ├── ReasoningPanel.tsx # 🧠 推論プロセス表示（折りたたみ）
│   │   │   ├── ToolEvents.tsx     # 🔧 ツール使用状況可視化
│   │   │   ├── ContentCard.tsx    # プラットフォーム別結果カード
│   │   │   ├── ScoreRadar.tsx     # 品質スコアレーダーチャート
│   │   │   ├── ThemeToggle.tsx    # 🌙 ダーク/ライト切替
│   │   │   └── LanguageSwitch.tsx # 🌐 EN/JA 切替
│   │   ├── hooks/
│   │   │   ├── useSSE.ts          # SSE ストリーム処理フック
│   │   │   ├── useTheme.ts        # テーマ管理フック
│   │   │   └── useI18n.ts         # i18n フック
│   │   ├── lib/
│   │   │   ├── api.ts             # API クライアント
│   │   │   └── i18n.ts            # 翻訳データ (EN/JA)
│   │   └── index.css              # Tailwind CSS + dark mode
│   ├── package.json
│   └── vite.config.ts
├── data/
│   └── brand_guidelines.md    # ブランドガイドライン（合成データ）
├── docs/
│   ├── SPEC.md
│   └── DESIGN.md
├── .env                       # 環境変数（gitignored）
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## 6. フロントエンド設計（React + Tailwind + shadcn/ui）

### 選定理由

- **React + TypeScript**: 型安全でモダンなSPA開発
- **Tailwind CSS**: ユーティリティファーストで高速スタイリング + Dark Mode 対応
- **shadcn/ui**: 美しいプリビルドコンポーネント（Card, Badge, Progress, Collapsible等）
- **Vite**: 高速ビルド & HMR（ハッカソン向き）
- **SSE (Server-Sent Events)**: エージェント進捗のリアルタイムストリーミング

### 機能一覧（過去リポジトリからの踏襲）

| 機能 | 説明 | 元ネタ |
|------|------|--------|
| 🧠 **推論プロセス表示** | gpt-5.2 の thinking トークンを折りたたみ UI で表示 | fabric-foundry-agentic-starter |
| 🔧 **ツール使用状況可視化** | `__TOOL_EVENT__` マーカーでツール名・入力・結果・所要時間をリアルタイム表示 | fabric-foundry-agentic-starter |
| 🌐 **多言語対応 (i18n)** | EN/JA 切替。UI ラベル + コンテンツ生成言語 | fabric-foundry-agentic-starter |
| 🌙 **ダーク/ライトモード** | Tailwind `dark:` クラスで全コンポーネント対応、チャート含む | fabric-foundry-agentic-starter |
| 💬 **マルチターン会話** | Thread ID 保持でリファイン対話対応。チャット履歴表示 | fabric-foundry-agentic-starter |
| 📋 **コピー機能** | プラットフォーム別のプレーンテキストをクリップボードにコピー | 新規 |
| 📝 **マークダウン出力** | エージェント出力を Markdown レンダリングで表示（react-markdown） | 新規 |
| 📊 **品質スコア** | 5軸レーダーチャートで品質評価を可視化 | 新規 |

### UI レイアウト

```
┌──────────────────────────────────────────────────────────┐
│  🚀 TechPulse Social     [🌐 EN/JA] [🌙/☀️]          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ Input Form ─────────────────────────────────────┐   │
│  │  Message: [__________________________________]      │   │
│  │  Platforms: [LinkedIn] [X] [Instagram]              │   │
│  │  Type: [Product Launch ▼]  Lang: [EN/JA]            │   │
│  │                              [✨ Generate]           │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ 🧠 Reasoning (collapsible) ───────────────────┐   │
│  │  ▶ Step 1: トピック分析...                          │   │
│  │    “AI product launch → B2B focus → dev comm...”  │   │
│  │  ▶ Step 2: コンテンツ構想...                        │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ 🔧 Tool Activity ────────────────────────────┐   │
│  │  ✅ file_search  “brand guidelines”    0.8s       │   │
│  │  ✅ web_search   “AI trends 2026”      1.2s       │   │
│  │  ⏳ generate_content  LinkedIn          ...        │   │
│  │  ⬜ review_content                     waiting    │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Response (Markdown) ─────────────────────────┐   │
│  │  [LinkedIn] [X] [Instagram]  tabs                │   │
│  │  ┌────────────────────────────────────────┐  │   │
│  │  │  ## LinkedIn Post                        │  │   │
│  │  │  *Markdown rendered content*             │  │   │
│  │  │  #hashtags                               │  │   │
│  │  │  📊 Score: 8.5/10 [レーダーチャート]     │  │   │
│  │  │  💡 Feedback: "Strong CTA..."            │  │   │
│  │  │  [📋 Copy] [🔄 Regenerate]               │  │   │
│  │  └────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────┘   │
│                                                          │
│  ┌─ Chat History (multi-turn) ──────────────────┐   │
│  │  You: "Create posts about our new AI product"   │   │
│  │  Agent: [response...]                           │   │
│  │  You: "Make the X post more casual"              │   │
│  │  Agent: [updated response...]                    │   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### コンポーネント設計

| コンポーネント | 役割 | SSE イベント |
|---|---|---|
| `App.tsx` | レイアウト、テーマプロバイダー、i18n コンテキスト | — |
| `ChatPanel.tsx` | マルチターン会話履歴・入力 UI | — |
| `InputForm.tsx` | トピック入力 + プラットフォーム選択 + 言語選択 | — |
| `ReasoningPanel.tsx` | 🧠 thinking トークンを折りたたみ表示 | `reasoning` |
| `ToolEvents.tsx` | 🔧 ツール名・入力・所要時間をタイムライン表示 | `tool_start` / `tool_end` |
| `ContentCard.tsx` | プラットフォーム別の Markdown レンダリング + コピーボタン | `text` |
| `ScoreRadar.tsx` | 5軸品質スコアのレーダーチャート | `text` (最終JSONから抽出) |
| `ThemeToggle.tsx` | Dark/Light モード切替ボタン | — |
| `LanguageSwitch.tsx` | EN/JA 切替 | — |

### SSE ストリーム処理（useSSE フック）

```typescript
// 過去リポジトリの ReadableStreamDefaultReader パターンを踏襲
const useSSE = (url: string) => {
  // SSE イベントをパースし、type に応じて状態を更新:
  // "reasoning"  → reasoningPanelState に追加
  // "tool_start" → toolEventsState に開始マーカー追加
  // "tool_end"   → toolEventsState に完了 + 所要時間追加
  // "text"       → contentState に Markdown テキスト追加
  // "done"       → thread_id 保存、ローディング終了
  // "error"      → エラー表示 + retry
};
```

### 推論プロセス表示の実装詳細

- `reasoning` イベントを `ReasoningPanel.tsx` にストリーム
- デフォルトは折りたたみ状態（`<Collapsible>`）、クリックで展開
- 🧠 アイコン + “Thinking...” アニメーション中はパルス表示
- モノスペースフォントで表示（thinking が本文と区別されるよう）
- ダークモードでは背景色を `bg-zinc-900/50` に

### ツール使用状況可視化の実装詳細

- `tool_start` でスピナー + ツール名 + 入力パラメータを表示
- `tool_end` でチェックマーク + 所要時間バッジ表示
- アイコン: 🔍 (file_search), 🌐 (web_search), ✍️ (generate), 📊 (review)
- タイムライン形式で上から下に順次追加

### コピー機能

- 各 `ContentCard` に「📋 Copy」ボタン
- クリックで `navigator.clipboard.writeText()` でプレーンテキスト（Markdownなし）をコピー
- コピー成功時にトースト通知

## 7. 依存パッケージ

### Python (Backend)

```
agent-framework-core # Agent Framework SDK (推移的に以下を含む):
                     #   pydantic, uvicorn, sse-starlette, httpx,
                     #   openai, mcp, opentelemetry, fastapi (starlette)
azure-identity       # 認証 (DefaultAzureCredential)
azure-cosmos         # Cosmos DB 会話履歴永続化
httpx                # Foundry IQ Agentic Retrieval HTTP client
python-dotenv        # 環境変数
```

### Node.js (Frontend)

```
react                # UI フレームワーク
typescript           # 型安全
tailwindcss          # スタイリング + dark mode
@radix-ui/react-*    # shadcn/ui 基盤
react-markdown       # Markdown レンダリング
recharts             # レーダーチャート
lucide-react         # アイコン
vite                 # ビルドツール
```

## 8. Azure デプロイメント

### Docker マルチステージビルド

```
Stage 1 (node:22-slim): npm install → npm run build → frontend/dist
Stage 2 (python:3.12-slim): uv sync → COPY frontend/dist → uvicorn
```

backend で SERVE_STATIC=true を設定すると、frontend/dist を FastAPI から直接配信。

### Azure Container Apps (azd)

- `azure.yaml` で host: containerapp を定義
- `infra/main.bicep` で ACR + Log Analytics + Container Apps Environment + Container App を一括プロビジョニング
- SystemAssigned マネージド ID で Azure AI Foundry に認証
- `azd up` 一発でプロビジョニング + デプロイ

## 9. Cosmos DB 会話履歴

- `src/database.py` で Cosmos DB 統合
- パーティションキー: `/userId`（将来のマルチテナント対応）
- 400 RU でサーバーレススケーリング
- Cosmos DB 未設定時はインメモリ辞書にフォールバック
- REST API: `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`

## 10. Foundry IQ Agentic Retrieval

- `src/agentic_retrieval.py` で Azure AI Search Agentic Retrieval API を統合
- API バージョン: `2025-11-01-preview`
- ReasoningEffort 3段階: MINIMAL（intents 方式）, LOW/MEDIUM（messages 方式）
- `@tool` デコレータでエージェントのツールとして自動登録
- `AI_SEARCH_ENDPOINT` 未設定時は自動スキップ（ツール一覧に含まれない）
