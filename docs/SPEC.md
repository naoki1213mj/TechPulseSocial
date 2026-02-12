# SPEC.md — エージェント仕様書

## 1. プロダクト概要

**名前**: Social AI Studio — AI-Powered Social Media Content Studio

**概要**: あらゆるブランド・業界の広報・マーケティングチームを支援する AI エージェントシステム。
単一の推論エージェント (gpt-5.2) が 7 つのツールを自律的に活用し、3フェーズの推論パイプライン
（CoT → ReAct → Self-Reflection）を通じて戦略立案 → コンテンツ生成 → 品質レビューを一貫して実行する。

推論プロセスとツール使用状況のリアルタイム可視化、A/B コンテンツ比較、Human-in-the-Loop ワークフロー、
OpenTelemetry 分散トレーシング、Foundry Evaluation による品質メトリクスを統合した
エンタープライズグレードのソーシャルメディアコンテンツスタジオ。

**ターゲットユーザー**: 企業の広報・マーケティング担当者

**バージョン**: 0.4.0

## 2. 機能要件

### 2.1 対応プラットフォーム

| プラットフォーム | 用途 | 文字数上限 | トーン |
|---|---|---|---|
| **LinkedIn** | B2B、思考リーダーシップ、採用 | 3,000文字 | プロフェッショナル、データドリブン |
| **X (Twitter)** | 開発者コミュニティ、速報 | 280文字 | カジュアル、テック寄り、ウィット |
| **Instagram** | ブランディング、社内文化 | 2,200文字 | ビジュアル重視、親しみやすい |

### 2.2 コンテンツタイプ

- 製品ローンチ告知 (`product_launch`)
- 技術ブログ記事の要約投稿 (`blog_summary`)
- イベント告知・レポート (`event`)
- 採用情報 (`hiring`)
- 業界トレンド解説 (`trend`)
- 思考リーダーシップ投稿 (`thought_leadership`)
- テックインサイト (`tech_insight`)

### 2.3 入力パラメータ

| パラメータ | 必須 | 説明 |
|---|---|---|
| `message` | ✅ | 投稿のトピック・テーマ |
| `platforms` | ✅ | 対象プラットフォーム（複数選択可）|
| `content_type` | ✅ | コンテンツタイプ |
| `language` | ❌ | 出力言語（デフォルト: en、対応: en/ja/ko/zh/es）|
| `reasoning_effort` | ❌ | 推論の深さ（low/medium/high、デフォルト: high）|
| `reasoning_summary` | ❌ | thinking 表示（off/auto/concise/detailed）|
| `ab_mode` | ❌ | A/B 比較モード（デフォルト: false）|
| `thread_id` | ❌ | マルチターン用スレッド ID（初回は null）|
| `conversation_id` | ❌ | Cosmos DB 会話 ID |

### 2.4 出力

各プラットフォーム向けに以下を生成:

- **本文テキスト**: プラットフォーム最適化済み（マークダウン対応）
- **ハッシュタグ**: 関連性の高いタグ 3〜5個
- **CTA (Call to Action)**: エンゲージメント促進テキスト
- **投稿タイミング提案**: エンゲージメント最適時間帯
- **画像**: gpt-image-1.5 で生成されたプラットフォーム最適化ビジュアル（base64）
- **品質スコア**: 5軸レビュー評価（1-10）
- **改善提案**: レビューエージェントからのフィードバック
- **ソース一覧**: Web検索・MCP で参照した URL リスト

## 3. エージェント構成（単一エージェント + 7ツール）

### エージェント: Social AI Studio Content Agent

- **役割**: トピックを分析し、各プラットフォーム向けのコンテンツを生成・レビュー
- **モデル**: gpt-5.2（推論モデル）
- **推論パターン**: CoT + ReAct + Self-Reflection を統合
- **ツール**: LLM がコンテキストに応じて自動選択

### ツール一覧（7ツール）

| ツール | 種別 | 説明 |
|--------|------|------|
| `web_search` | Hosted (Bing Grounding) | リアルタイムトレンド・ニュース検索 |
| `file_search` | Hosted (FileSearchTool) | ブランドガイドライン検索（Vector Store 経由）|
| `mcp` | Hosted (MCP Server) | Microsoft Learn ドキュメント検索 (Streamable HTTP) |
| `search_knowledge_base` | Custom (@tool) | Foundry IQ Agentic Retrieval（Azure AI Search 経由）|
| `generate_content` | Custom (@tool) | プラットフォーム別最適化コンテンツ生成 |
| `review_content` | Custom (@tool) | 5軸品質スコアリング + 改善提案 |
| `generate_image` | Custom (@tool) | gpt-image-1.5 プラットフォーム最適化ビジュアル生成 |

## 4. 非機能要件

| 項目 | 要件 |
|------|------|
| **レスポンス時間** | 全プロセス完了まで 120秒以内目標（reasoning=high 時）|
| **エラーハンドリング** | 429 レート制限時の retry-after 対応、SSE error イベント |
| **セキュリティ** | 資格情報はすべて環境変数経由、DefaultAzureCredential |
| **コンテンツ安全性** | Azure AI Content Safety（テキスト有害分析 + プロンプトシールド）|
| **可観測性** | OpenTelemetry 分散トレーシング → Application Insights |
| **品質評価** | Foundry Evaluation SDK (Relevance, Coherence, Fluency, Groundedness) |
| **データ永続化** | Cosmos DB 会話履歴（InMemory フォールバック）|
| **マルチターン** | Thread ID + Conversation ID 保持でリファイン対話対応 |
| **停止/リトライ** | Stop ボタンで SSE 中断、Retry ボタンで再生成 |
| **テスト** | 120 ユニットテスト (pytest + pytest-asyncio) |
| **デプロイ** | azd up → Azure Container Apps (Docker マルチステージ) |

## 5. フロントエンド機能要件

### コンテンツ & 生成

| 機能 | 説明 |
|------|------|
| 🖼️ **プラットフォームカード** | LinkedIn (blue), X (gray), Instagram (pink) カラーテーマ + per-card コピー |
| 🧠 **推論フェーズバッジ** | CoT (💭 indigo) → ReAct (⚡ amber) → Self-Reflection (🔍 emerald) のパルスアニメーション |
| 🔧 **ツール使用 Pills** | アニメーション + グラデーショングロー + 所要時間バッジ |
| 📊 **品質レーダーチャート** | recharts 5軸レーダー + overall score |
| 🛡️ **Content Safety バッジ** | 安全性チェックインジケータ |
| 📈 **Processing Metrics** | 生成後の統計バー (reasoning chars, tools used, output chars) |
| 🎯 **A/B 比較カード** | サイドバイサイド + ミニレーダー + 勝者バッジ |
| 🖼️ **画像表示** | gpt-image-1.5 生成画像をカード内に表示 |

### インタラクション

| 機能 | 説明 |
|------|------|
| 👤 **HITL コントロール** | Approve ✅ / Edit ✏️ / Refine 🔄 per card |
| 📝 **インライン編集** | textarea で直接修正、保存/キャンセル |
| 💬 **会話履歴** | Cosmos DB 連携サイドバー、クリックで会話復元 |
| 📥 **コンテンツエクスポート** | Markdown (.md) / JSON ダウンロード |
| ⏹️ **Stop / Retry** | 生成中断 + ワンクリックリトライ |
| ⌨️ **キーボードショートカット** | Ctrl+Enter で送信、Escape で停止 |
| 💡 **Suggested Questions** | 空状態の提案質問グリッド (4つ) |

### デザイン

| 機能 | 説明 |
|------|------|
| ✨ **Glassmorphism UI** | frosted glass cards + backdrop blur + gradient backgrounds |
| 🎨 **Gradient Design System** | ヘッダー・ボタン・ボーダーにグラディエント |
| 💀 **Skeleton Loading** | shimmer プレースホルダー (生成中) |
| 🎬 **Card Animations** | staggered fade-in (順次表示) |
| 🌙 **Dark / Light Mode** | system-preference-aware |
| 🌐 **5言語 i18n** | EN / JA / KO / ZH / ES (国旗セレクター) |

## 6. 技術スタック

| レイヤー | 技術 |
|---|---|
| **AI基盤** | Microsoft Foundry (agent-framework-core + Responses API v1) |
| **推論モデル** | gpt-5.2 (reasoning effort 制御可能) |
| **画像モデル** | gpt-image-1.5 (プラットフォーム最適化ビジュアル) |
| **バックエンド** | Python 3.12 + FastAPI + uvicorn (SSE ストリーミング) |
| **フロントエンド** | React 19 + TypeScript 5 + Vite 7 + Tailwind CSS v3 |
| **グラウンディング** | File Search (Vector Store) + Web Search (Bing) + MCP (Microsoft Learn) + Foundry IQ (Azure AI Search) |
| **可観測性** | OpenTelemetry → Azure Application Insights → Foundry Tracing |
| **品質評価** | azure-ai-evaluation SDK (Relevance, Coherence, Fluency, Groundedness) |
| **データベース** | Azure Cosmos DB (InMemory フォールバック) |
| **認証** | DefaultAzureCredential (Azure CLI / Managed Identity) |
| **デプロイ** | Azure Container Apps via azd (Docker マルチステージ) |
| **パッケージ管理** | uv (Python) / npm (Node.js) |
| **テスト** | pytest + pytest-asyncio (120 tests) |

## 7. API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/api/chat` | SSE ストリーミングレスポンス |
| `POST` | `/api/evaluate` | Foundry Evaluation 品質メトリクス |
| `GET` | `/api/health` | ヘルスチェック + バージョン + Observability 情報 |
| `GET` | `/api/conversations` | 会話一覧 |
| `GET` | `/api/conversations/{id}` | 会話詳細（メッセージ含む）|
| `DELETE` | `/api/conversations/{id}` | 会話削除 |
