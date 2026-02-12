/** i18n translation data */
export type Locale = "en" | "ja" | "ko" | "zh" | "es";

/** Locale metadata for UI display */
export const LOCALE_META: Record<Locale, { flag: string; label: string; nativeLabel: string }> = {
  en: { flag: "🇺🇸", label: "English", nativeLabel: "English" },
  ja: { flag: "🇯🇵", label: "Japanese", nativeLabel: "日本語" },
  ko: { flag: "🇰🇷", label: "Korean", nativeLabel: "한국어" },
  zh: { flag: "🇨🇳", label: "Chinese", nativeLabel: "中文" },
  es: { flag: "🇪🇸", label: "Spanish", nativeLabel: "Español" },
};

export const ALL_LOCALES: Locale[] = ["en", "ja", "ko", "zh", "es"];

const translations: Record<Locale, Record<string, string>> = {
  en: {
    "app.title": "TechPulse Social",
    "app.subtitle": "AI-Powered Social Media Content Studio",
    "app.description": "Generate high-quality social media content with reasoning AI",

    // Input
    "input.topic": "Topic / Theme",
    "input.topic.placeholder": "e.g., Launch of the new AI code assistant feature...",
    "input.platforms": "Platforms",
    "input.contentType": "Content Type",
    "input.language": "Output Language",
    "input.submit": "Generate Content",
    "input.generating": "Generating...",
    "input.stop": "Stop Generation",

    // Status
    "status.complete": "Complete",
    "action.newConversation": "New Conversation",
    "metrics.reasoningChars": "chars reasoning",
    "metrics.toolsUsed": "tools",
    "metrics.outputChars": "chars output",

    // HITL
    "hitl.approve": "Approve",
    "hitl.approved": "Approved",
    "hitl.edit": "Edit",
    "hitl.refine": "Refine",
    "hitl.refine.placeholder": "Describe how to improve this content...",
    "hitl.send": "Send Feedback",
    "hitl.cancel": "Cancel",
    "hitl.save": "Save",

    // Export
    "export.markdown": "Export .md",
    "export.json": "Export JSON",

    // Error
    "error.generic": "An error occurred. Please try again.",
    "error.retry": "Retry",
    "platforms.linkedin": "LinkedIn",
    "platforms.x": "X (Twitter)",
    "platforms.instagram": "Instagram",

    // Content Types
    "contentType.product_launch": "Product Launch",
    "contentType.thought_leadership": "Thought Leadership",
    "contentType.event_promotion": "Event Promotion",
    "contentType.company_culture": "Company Culture",
    "contentType.tech_insight": "Tech Insight",

    // Language
    "language.en": "English",
    "language.ja": "Japanese",
    "language.ko": "Korean",
    "language.zh": "Chinese",
    "language.es": "Spanish",

    // Settings
    "settings.title": "AI Settings",
    "settings.reasoningEffort": "Reasoning Depth",
    "settings.reasoningEffort.low": "Low — Fast, simple",
    "settings.reasoningEffort.medium": "Medium — Balanced",
    "settings.reasoningEffort.high": "High — Deep reasoning",
    "settings.reasoningSummary": "Thinking Display",
    "settings.reasoningSummary.off": "Off — Hide thinking",
    "settings.reasoningSummary.auto": "Auto",
    "settings.reasoningSummary.concise": "Concise",
    "settings.reasoningSummary.detailed": "Detailed",

    // Reasoning
    "reasoning.title": "Reasoning Process",
    "reasoning.thinking": "Thinking...",
    "reasoning.complete": "Reasoning complete",

    // Tools
    "tools.title": "Tool Usage",
    "tools.running": "tools running",
    "tools.used": "tools used",
    "tools.started": "Running",
    "tools.completed": "Completed",
    "tools.error": "Error",
    "tools.waiting": "Analyzing...",
    "tools.category.search": "Search",
    "tools.category.content": "Content",
    "tools.category.review": "Review",
    "tools.category.image": "Image",
    "tools.category.docs": "Docs",

    // A/B Comparison
    "settings.abMode": "A/B Comparison",
    "settings.abMode.description": "Generate two variants with different strategies for comparison",
    "ab.title": "Content Comparison",
    "ab.variant": "Variant",
    "ab.select": "Select",
    "ab.selected": "Selected",
    "ab.winner": "Higher Score",
    "ab.fullView": "Full view",

    // Content
    "content.copy": "Copy",
    "content.copied": "Copied!",
    "content.chars": "characters",
    "content.title": "Generated Content",
    "content.sources": "Sources",
    "review.title": "Quality Review",
    "review.brandAlignment": "Brand Alignment",
    "review.audienceRelevance": "Audience Relevance",
    "review.engagementPotential": "Engagement Potential",
    "review.clarity": "Clarity",
    "review.platformOptimization": "Platform Optimization",
    "review.feedback": "Feedback",
    "review.safe": "Content Safe",
    "review.improvements": "Improvements Made",

    // Theme / i18n
    "theme.light": "Light",
    "theme.dark": "Dark",

    // Suggestions
    "suggestions.title": "Try these examples",
    "suggestions.1": "AI code assistant launch announcement",
    "suggestions.2": "Tech conference participation report",
    "suggestions.3": "Engineering team culture spotlight",
    "suggestions.4": "Latest AI trends and industry insights",

    // Footer area
    "footer.processing": "Processing",
    "footer.details": "Processing Details",
    "footer.reasoning": "Reasoning",
  },
  ja: {
    "app.title": "TechPulse Social",
    "app.subtitle": "AI搭載ソーシャルメディアコンテンツスタジオ",
    "app.description": "推論AIで高品質なSNSコンテンツを生成",

    // Input
    "input.topic": "トピック / テーマ",
    "input.topic.placeholder": "例: 新しいAIコードアシスタント機能のローンチ...",
    "input.platforms": "プラットフォーム",
    "input.contentType": "コンテンツタイプ",
    "input.language": "出力言語",
    "input.submit": "コンテンツ生成",
    "input.generating": "生成中...",
    "input.stop": "生成を停止",

    // Status
    "status.complete": "完了",
    "action.newConversation": "新しい会話",
    "metrics.reasoningChars": "文字の推論",
    "metrics.toolsUsed": "ツール",
    "metrics.outputChars": "文字の出力",

    // HITL
    "hitl.approve": "承認",
    "hitl.approved": "承認済み",
    "hitl.edit": "編集",
    "hitl.refine": "改善",
    "hitl.refine.placeholder": "改善ポイントを入力してください...",
    "hitl.send": "フィードバック送信",
    "hitl.cancel": "キャンセル",
    "hitl.save": "保存",

    // Export
    "export.markdown": "Markdown出力",
    "export.json": "JSON出力",

    // Error
    "error.generic": "エラーが発生しました。もう一度お試しください。",
    "error.retry": "リトライ",
    "platforms.linkedin": "LinkedIn",
    "platforms.x": "X (Twitter)",
    "platforms.instagram": "Instagram",

    // Content Types
    "contentType.product_launch": "製品ローンチ",
    "contentType.thought_leadership": "ソートリーダーシップ",
    "contentType.event_promotion": "イベントプロモーション",
    "contentType.company_culture": "企業カルチャー",
    "contentType.tech_insight": "テックインサイト",

    // Language
    "language.en": "English",
    "language.ja": "日本語",
    "language.ko": "한국어",
    "language.zh": "中文",
    "language.es": "Español",

    // Settings
    "settings.title": "AI 設定",
    "settings.reasoningEffort": "推論深度",
    "settings.reasoningEffort.low": "Low — 高速・シンプル",
    "settings.reasoningEffort.medium": "Medium — バランス型",
    "settings.reasoningEffort.high": "High — 深い推論",
    "settings.reasoningSummary": "思考プロセス表示",
    "settings.reasoningSummary.off": "Off — 非表示",
    "settings.reasoningSummary.auto": "Auto — 自動",
    "settings.reasoningSummary.concise": "Concise — 簡潔",
    "settings.reasoningSummary.detailed": "Detailed — 詳細",

    // Reasoning
    "reasoning.title": "推論プロセス",
    "reasoning.thinking": "思考中...",
    "reasoning.complete": "推論完了",

    // Tools
    "tools.title": "ツール使用状況",
    "tools.running": "個のツールを実行中",
    "tools.used": "個のツールを使用",
    "tools.started": "実行中",
    "tools.completed": "完了",
    "tools.error": "エラー",
    "tools.waiting": "分析中...",
    "tools.category.search": "検索",
    "tools.category.content": "コンテンツ",
    "tools.category.review": "レビュー",
    "tools.category.image": "画像生成",
    "tools.category.docs": "ドキュメント",

    // A/B比較
    "settings.abMode": "A/Bコンテンツ比較",
    "settings.abMode.description": "異なる戦略で2つのバリアントを生成して比較",
    "ab.title": "コンテンツ比較",
    "ab.variant": "バリアント",
    "ab.select": "選択",
    "ab.selected": "選択済み",
    "ab.winner": "高スコア",
    "ab.fullView": "詳細表示",

    // Content
    "content.copy": "コピー",
    "content.copied": "コピーしました！",
    "content.chars": "文字",
    "content.title": "生成コンテンツ",
    "content.sources": "参照元",
    "review.title": "品質レビュー",
    "review.brandAlignment": "ブランド適合性",
    "review.audienceRelevance": "ターゲット適合性",
    "review.engagementPotential": "エンゲージメント",
    "review.clarity": "明確さ",
    "review.platformOptimization": "プラットフォーム最適化",
    "review.feedback": "フィードバック",
    "review.improvements": "改善内容",
    "review.safe": "安全性確認済み",

    // Theme / i18n
    "theme.light": "ライト",
    "theme.dark": "ダーク",

    // Suggestions
    "suggestions.title": "こんなトピックを試してみてください",
    "suggestions.1": "AIコードアシスタントの新機能ローンチ告知",
    "suggestions.2": "テックカンファレンス参加レポート",
    "suggestions.3": "エンジニアリングチームのカルチャー紹介",
    "suggestions.4": "AI最新トレンドと業界インサイト",

    // Footer area
    "footer.processing": "処理中",
    "footer.details": "処理の詳細",
    "footer.reasoning": "推論",
  },
  ko: {
    "app.title": "TechPulse Social",
    "app.subtitle": "AI 기반 소셜 미디어 콘텐츠 스튜디오",
    "app.description": "추론 AI로 고품질 소셜 미디어 콘텐츠 생성",

    // Input
    "input.topic": "주제 / 테마",
    "input.topic.placeholder": "예: 새로운 AI 코드 어시스턴트 기능 출시...",
    "input.platforms": "플랫폼",
    "input.contentType": "콘텐츠 유형",
    "input.language": "출력 언어",
    "input.submit": "콘텐츠 생성",
    "input.generating": "생성 중...",
    "input.stop": "생성 중지",

    // Status
    "status.complete": "완료",
    "action.newConversation": "새 대화",
    "metrics.reasoningChars": "문자 추론",
    "metrics.toolsUsed": "도구",
    "metrics.outputChars": "문자 출력",

    // HITL
    "hitl.approve": "승인",
    "hitl.approved": "승인됨",
    "hitl.edit": "편집",
    "hitl.refine": "개선",
    "hitl.refine.placeholder": "개선 사항을 설명해 주세요...",
    "hitl.send": "피드백 전송",
    "hitl.cancel": "취소",
    "hitl.save": "저장",

    // Export
    "export.markdown": "Markdown 내보내기",
    "export.json": "JSON 내보내기",

    // Error
    "error.generic": "오류가 발생했습니다. 다시 시도해 주세요.",
    "error.retry": "재시도",
    "platforms.linkedin": "LinkedIn",
    "platforms.x": "X (Twitter)",
    "platforms.instagram": "Instagram",

    // Content Types
    "contentType.product_launch": "제품 출시",
    "contentType.thought_leadership": "사고 리더십",
    "contentType.event_promotion": "이벤트 프로모션",
    "contentType.company_culture": "기업 문화",
    "contentType.tech_insight": "기술 인사이트",

    // Language
    "language.en": "English",
    "language.ja": "日本語",
    "language.ko": "한국어",
    "language.zh": "中文",
    "language.es": "Español",

    // Settings
    "settings.title": "AI 설정",
    "settings.reasoningEffort": "추론 깊이",
    "settings.reasoningEffort.low": "Low — 빠름, 간단",
    "settings.reasoningEffort.medium": "Medium — 균형",
    "settings.reasoningEffort.high": "High — 깊은 추론",
    "settings.reasoningSummary": "사고 과정 표시",
    "settings.reasoningSummary.off": "Off — 숨기기",
    "settings.reasoningSummary.auto": "Auto — 자동",
    "settings.reasoningSummary.concise": "Concise — 간결",
    "settings.reasoningSummary.detailed": "Detailed — 상세",

    // Reasoning
    "reasoning.title": "추론 과정",
    "reasoning.thinking": "사고 중...",
    "reasoning.complete": "추론 완료",

    // Tools
    "tools.title": "도구 사용 현황",
    "tools.running": "개 도구 실행 중",
    "tools.used": "개 도구 사용됨",
    "tools.started": "실행 중",
    "tools.completed": "완료",
    "tools.error": "오류",
    "tools.waiting": "분석 중...",
    "tools.category.search": "검색",
    "tools.category.content": "콘텐츠",
    "tools.category.review": "리뷰",
    "tools.category.image": "이미지",
    "tools.category.docs": "문서",

    // A/B 비교
    "settings.abMode": "A/B 콘텐츠 비교",
    "settings.abMode.description": "다른 전략으로 두 가지 변형을 생성하여 비교",
    "ab.title": "콘텐츠 비교",
    "ab.variant": "변형",
    "ab.select": "선택",
    "ab.selected": "선택됨",
    "ab.winner": "높은 점수",
    "ab.fullView": "전체 보기",

    // Content
    "content.copy": "복사",
    "content.copied": "복사됨!",
    "content.chars": "자",
    "content.title": "생성된 콘텐츠",
    "content.sources": "출처",
    "review.title": "품질 리뷰",
    "review.brandAlignment": "브랜드 적합성",
    "review.audienceRelevance": "타겟 적합성",
    "review.engagementPotential": "참여 잠재력",
    "review.clarity": "명확성",
    "review.platformOptimization": "플랫폼 최적화",
    "review.feedback": "피드백",
    "review.improvements": "개선 사항",
    "review.safe": "콘텐츠 안전",

    // Theme / i18n
    "theme.light": "라이트",
    "theme.dark": "다크",

    // Suggestions
    "suggestions.title": "이런 주제를 시도해 보세요",
    "suggestions.1": "AI 코드 어시스턴트 신기능 출시 발표",
    "suggestions.2": "기술 컨퍼런스 참가 보고서",
    "suggestions.3": "엔지니어링 팀 문화 소개",
    "suggestions.4": "AI 최신 트렌드와 업계 인사이트",

    // Footer area
    "footer.processing": "처리 중",
    "footer.details": "처리 상세",
    "footer.reasoning": "추론",
  },
  zh: {
    "app.title": "TechPulse Social",
    "app.subtitle": "AI驱动的社交媒体内容工作室",
    "app.description": "使用推理AI生成高质量社交媒体内容",

    // Input
    "input.topic": "主题 / 话题",
    "input.topic.placeholder": "例如：新AI代码助手功能发布...",
    "input.platforms": "平台",
    "input.contentType": "内容类型",
    "input.language": "输出语言",
    "input.submit": "生成内容",
    "input.generating": "生成中...",
    "input.stop": "停止生成",

    // Status
    "status.complete": "完成",
    "action.newConversation": "新建对话",
    "metrics.reasoningChars": "字符推理",
    "metrics.toolsUsed": "工具",
    "metrics.outputChars": "字符输出",

    // HITL
    "hitl.approve": "批准",
    "hitl.approved": "已批准",
    "hitl.edit": "编辑",
    "hitl.refine": "优化",
    "hitl.refine.placeholder": "描述如何改进此内容...",
    "hitl.send": "发送反馈",
    "hitl.cancel": "取消",
    "hitl.save": "保存",

    // Export
    "export.markdown": "导出 Markdown",
    "export.json": "导出 JSON",

    // Error
    "error.generic": "发生错误，请重试。",
    "error.retry": "重试",
    "platforms.linkedin": "LinkedIn",
    "platforms.x": "X (Twitter)",
    "platforms.instagram": "Instagram",

    // Content Types
    "contentType.product_launch": "产品发布",
    "contentType.thought_leadership": "思想领导力",
    "contentType.event_promotion": "活动推广",
    "contentType.company_culture": "企业文化",
    "contentType.tech_insight": "技术洞察",

    // Language
    "language.en": "English",
    "language.ja": "日本語",
    "language.ko": "한국어",
    "language.zh": "中文",
    "language.es": "Español",

    // Settings
    "settings.title": "AI 设置",
    "settings.reasoningEffort": "推理深度",
    "settings.reasoningEffort.low": "Low — 快速简单",
    "settings.reasoningEffort.medium": "Medium — 平衡",
    "settings.reasoningEffort.high": "High — 深度推理",
    "settings.reasoningSummary": "思考过程显示",
    "settings.reasoningSummary.off": "Off — 隐藏",
    "settings.reasoningSummary.auto": "Auto — 自动",
    "settings.reasoningSummary.concise": "Concise — 简洁",
    "settings.reasoningSummary.detailed": "Detailed — 详细",

    // Reasoning
    "reasoning.title": "推理过程",
    "reasoning.thinking": "思考中...",
    "reasoning.complete": "推理完成",

    // Tools
    "tools.title": "工具使用情况",
    "tools.running": "个工具运行中",
    "tools.used": "个工具已使用",
    "tools.started": "运行中",
    "tools.completed": "完成",
    "tools.error": "错误",
    "tools.waiting": "分析中...",
    "tools.category.search": "搜索",
    "tools.category.content": "内容",
    "tools.category.review": "审核",
    "tools.category.image": "图像",
    "tools.category.docs": "文档",

    // A/B 对比
    "settings.abMode": "A/B 内容对比",
    "settings.abMode.description": "用不同策略生成两个变体进行对比",
    "ab.title": "内容对比",
    "ab.variant": "变体",
    "ab.select": "选择",
    "ab.selected": "已选择",
    "ab.winner": "高分",
    "ab.fullView": "完整视图",

    // Content
    "content.copy": "复制",
    "content.copied": "已复制！",
    "content.chars": "字符",
    "content.title": "生成的内容",
    "content.sources": "来源",
    "review.title": "质量审核",
    "review.brandAlignment": "品牌契合度",
    "review.audienceRelevance": "目标受众相关性",
    "review.engagementPotential": "互动潜力",
    "review.clarity": "清晰度",
    "review.platformOptimization": "平台优化",
    "review.feedback": "反馈",
    "review.improvements": "改进内容",
    "review.safe": "内容安全",

    // Theme / i18n
    "theme.light": "浅色",
    "theme.dark": "深色",

    // Suggestions
    "suggestions.title": "试试这些示例",
    "suggestions.1": "AI代码助手新功能发布公告",
    "suggestions.2": "技术大会参加报告",
    "suggestions.3": "工程团队文化亮点",
    "suggestions.4": "AI最新趋势与行业洞察",

    // Footer area
    "footer.processing": "处理中",
    "footer.details": "处理详情",
    "footer.reasoning": "推理",
  },
  es: {
    "app.title": "TechPulse Social",
    "app.subtitle": "Estudio de Contenido para Redes Sociales con IA",
    "app.description": "Genera contenido de alta calidad para redes sociales con IA de razonamiento",

    // Input
    "input.topic": "Tema",
    "input.topic.placeholder": "Ej: Lanzamiento de la nueva función de asistente de código IA...",
    "input.platforms": "Plataformas",
    "input.contentType": "Tipo de Contenido",
    "input.language": "Idioma de Salida",
    "input.submit": "Generar Contenido",
    "input.generating": "Generando...",
    "input.stop": "Detener Generación",

    // Status
    "status.complete": "Completado",
    "action.newConversation": "Nueva Conversación",
    "metrics.reasoningChars": "caracteres razonamiento",
    "metrics.toolsUsed": "herramientas",
    "metrics.outputChars": "caracteres salida",

    // HITL
    "hitl.approve": "Aprobar",
    "hitl.approved": "Aprobado",
    "hitl.edit": "Editar",
    "hitl.refine": "Mejorar",
    "hitl.refine.placeholder": "Describe cómo mejorar este contenido...",
    "hitl.send": "Enviar Feedback",
    "hitl.cancel": "Cancelar",
    "hitl.save": "Guardar",

    // Export
    "export.markdown": "Exportar .md",
    "export.json": "Exportar JSON",

    // Error
    "error.generic": "Ocurrió un error. Inténtalo de nuevo.",
    "error.retry": "Reintentar",
    "platforms.linkedin": "LinkedIn",
    "platforms.x": "X (Twitter)",
    "platforms.instagram": "Instagram",

    // Content Types
    "contentType.product_launch": "Lanzamiento de Producto",
    "contentType.thought_leadership": "Liderazgo de Opinión",
    "contentType.event_promotion": "Promoción de Evento",
    "contentType.company_culture": "Cultura Empresarial",
    "contentType.tech_insight": "Perspectiva Tecnológica",

    // Language
    "language.en": "English",
    "language.ja": "日本語",
    "language.ko": "한국어",
    "language.zh": "中文",
    "language.es": "Español",

    // Settings
    "settings.title": "Configuración de IA",
    "settings.reasoningEffort": "Profundidad de Razonamiento",
    "settings.reasoningEffort.low": "Low — Rápido, simple",
    "settings.reasoningEffort.medium": "Medium — Equilibrado",
    "settings.reasoningEffort.high": "High — Razonamiento profundo",
    "settings.reasoningSummary": "Mostrar Pensamiento",
    "settings.reasoningSummary.off": "Off — Ocultar",
    "settings.reasoningSummary.auto": "Auto",
    "settings.reasoningSummary.concise": "Concise — Conciso",
    "settings.reasoningSummary.detailed": "Detailed — Detallado",

    // Reasoning
    "reasoning.title": "Proceso de Razonamiento",
    "reasoning.thinking": "Pensando...",
    "reasoning.complete": "Razonamiento completo",

    // Tools
    "tools.title": "Uso de Herramientas",
    "tools.running": "herramientas en ejecución",
    "tools.used": "herramientas utilizadas",
    "tools.started": "Ejecutando",
    "tools.completed": "Completado",
    "tools.error": "Error",
    "tools.waiting": "Analizando...",
    "tools.category.search": "Búsqueda",
    "tools.category.content": "Contenido",
    "tools.category.review": "Revisión",
    "tools.category.image": "Imagen",
    "tools.category.docs": "Documentos",

    // Comparación A/B
    "settings.abMode": "Comparación A/B",
    "settings.abMode.description": "Generar dos variantes con diferentes estrategias para comparar",
    "ab.title": "Comparación de Contenido",
    "ab.variant": "Variante",
    "ab.select": "Seleccionar",
    "ab.selected": "Seleccionado",
    "ab.winner": "Puntuación Alta",
    "ab.fullView": "Vista completa",

    // Content
    "content.copy": "Copiar",
    "content.copied": "¡Copiado!",
    "content.chars": "caracteres",
    "content.title": "Contenido Generado",
    "content.sources": "Fuentes",
    "review.title": "Revisión de Calidad",
    "review.brandAlignment": "Alineación de Marca",
    "review.audienceRelevance": "Relevancia de Audiencia",
    "review.engagementPotential": "Potencial de Engagement",
    "review.clarity": "Claridad",
    "review.platformOptimization": "Optimización de Plataforma",
    "review.feedback": "Feedback",
    "review.improvements": "Mejoras Realizadas",
    "review.safe": "Contenido Seguro",

    // Theme / i18n
    "theme.light": "Claro",
    "theme.dark": "Oscuro",

    // Suggestions
    "suggestions.title": "Prueba estos ejemplos",
    "suggestions.1": "Anuncio de lanzamiento del asistente de código IA",
    "suggestions.2": "Informe de participación en conferencia tech",
    "suggestions.3": "Cultura del equipo de ingeniería",
    "suggestions.4": "Últimas tendencias de IA e insights de la industria",

    // Footer area
    "footer.processing": "Procesando",
    "footer.details": "Detalles del Proceso",
    "footer.reasoning": "Razonamiento",
  },
};

export function t(key: string, locale: Locale): string {
  return translations[locale]?.[key] ?? translations.en[key] ?? key;
}
