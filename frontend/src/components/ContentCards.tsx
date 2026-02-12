import { Check, CheckCircle2, Copy, Download, Edit3, ExternalLink, Linkedin, MessageCircle, RefreshCw, Send, ShieldAlert, ShieldCheck, Trophy, Twitter, X } from "lucide-react";
import { useState } from "react";
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import type { SafetyResult } from "../lib/api";

/** Structured content from the agent's JSON output */
export interface PlatformContent {
  platform: string;
  body: string;
  hashtags: string[];
  call_to_action: string;
  posting_time: string;
  image_prompt?: string;
  image_base64?: string;
}

export interface ContentReview {
  overall_score: number;
  scores: {
    brand_alignment: number;
    audience_relevance: number;
    engagement_potential: number;
    clarity: number;
    platform_optimization: number;
  };
  feedback: string[];
  improvements_made: string[];
}

export interface StructuredOutput {
  contents: PlatformContent[];
  review: ContentReview;
  sources_used: string[];
}

/** A/B comparison variant */
export interface ABVariant {
  strategy: string;
  contents: PlatformContent[];
  review: ContentReview;
}

/** A/B comparison structured output */
export interface ABStructuredOutput {
  mode: "ab";
  variant_a: ABVariant;
  variant_b: ABVariant;
  sources_used: string[];
}

interface ContentCardsProps {
  data: StructuredOutput;
  t: (key: string) => string;
  onRefine?: (platform: string, feedback: string) => void;
  safetyResult?: SafetyResult | null;
}

/** Platform metadata for display */
const PLATFORM_META: Record<
  string,
  { icon: React.ReactNode; color: string; bgColor: string; borderColor: string; label: string }
> = {
  linkedin: {
    icon: <Linkedin className="w-5 h-5" />,
    color: "text-blue-700 dark:text-blue-400",
    bgColor: "bg-blue-50 dark:bg-blue-950/30",
    borderColor: "border-blue-200 dark:border-blue-800",
    label: "LinkedIn",
  },
  x: {
    icon: <Twitter className="w-5 h-5" />,
    color: "text-gray-900 dark:text-gray-100",
    bgColor: "bg-gray-50 dark:bg-gray-900/50",
    borderColor: "border-gray-200 dark:border-gray-700",
    label: "X (Twitter)",
  },
  instagram: {
    icon: <MessageCircle className="w-5 h-5" />,
    color: "text-pink-600 dark:text-pink-400",
    bgColor: "bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/30 dark:to-pink-950/30",
    borderColor: "border-pink-200 dark:border-pink-800",
    label: "Instagram",
  },
};

function ScoreBar({ score, label }: { score: number; label: string }) {
  const pct = (score / 10) * 100;
  const color =
    score >= 8 ? "bg-green-500" : score >= 6 ? "bg-yellow-500" : "bg-red-500";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-32 text-gray-500 dark:text-gray-400 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-6 text-right font-medium">{score}</span>
    </div>
  );
}

function PlatformCard({ item, t, onRefine }: { item: PlatformContent; t: (key: string) => string; onRefine?: (platform: string, feedback: string) => void }) {
  const [copied, setCopied] = useState(false);
  const [approved, setApproved] = useState(false);
  const [showRefine, setShowRefine] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [editing, setEditing] = useState(false);
  const [editedBody, setEditedBody] = useState(item.body);
  const meta = PLATFORM_META[item.platform] ?? PLATFORM_META.linkedin;

  const handleCopy = async () => {
    const text = `${editing ? editedBody : item.body}\n\n${item.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ")}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const handleRefineSubmit = () => {
    if (feedback.trim() && onRefine) {
      onRefine(item.platform, feedback.trim());
      setFeedback("");
      setShowRefine(false);
    }
  };

  return (
    <div className={`border rounded-xl overflow-hidden card-fade-in ${meta.borderColor}`}>
      {/* Card header */}
      <div className={`flex items-center justify-between px-4 py-2.5 ${meta.bgColor}`}>
        <div className={`flex items-center gap-2 ${meta.color}`}>
          {meta.icon}
          <span className="font-semibold text-sm">{meta.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {item.posting_time && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              🕐 {item.posting_time}
            </span>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-gray-500 dark:text-gray-400 hover:bg-white/50 dark:hover:bg-gray-800 transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-green-500" />
                <span className="text-green-600 dark:text-green-400">{t("content.copied")}</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>{t("content.copy")}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Image (if generated) */}
      {item.image_base64 && (
        <div className="px-4 pt-3">
          <img
            src={`data:image/png;base64,${item.image_base64}`}
            alt={`${item.platform} visual`}
            className="w-full rounded-lg object-cover max-h-64"
          />
        </div>
      )}

      {/* Content body */}
      <div className="px-4 py-3">
        {editing ? (
          <div className="space-y-2">
            <textarea
              value={editedBody}
              onChange={(e) => setEditedBody(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm outline-none resize-y focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setEditing(false); setEditedBody(item.body); }}
                className="px-2.5 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              >
                <X className="w-3 h-3 inline mr-1" />{t("hitl.cancel")}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-2.5 py-1 text-xs bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                <Check className="w-3 h-3 inline mr-1" />{t("hitl.save")}
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-800 dark:text-gray-200">
            {editedBody}
          </p>
        )}
      </div>

      {/* Hashtags */}
      {item.hashtags.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {item.hashtags.map((tag, i) => (
            <span
              key={i}
              className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-blue-600 dark:text-blue-400"
            >
              {tag.startsWith("#") ? tag : `#${tag}`}
            </span>
          ))}
        </div>
      )}

      {/* CTA */}
      {item.call_to_action && (
        <div className="px-4 pb-3 text-xs text-gray-500 dark:text-gray-400 italic">
          CTA: {item.call_to_action}
        </div>
      )}

      {/* Character count */}
      <div className="px-4 pb-2 text-right">
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {(editing ? editedBody : item.body).length.toLocaleString()} {t("content.chars")}
        </span>
      </div>

      {/* HITL: Approve / Edit / Refine actions */}
      <div className="px-4 pb-3 border-t border-gray-100 dark:border-gray-800 pt-2.5">
        <div className="flex items-center gap-2">
          {/* Approve button */}
          <button
            onClick={() => setApproved(!approved)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all btn-hover ${
              approved
                ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700 stamp-in"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-green-50 dark:hover:bg-green-950/20 border border-transparent"
            }`}
          >
            <CheckCircle2 className={`w-3.5 h-3.5 ${approved ? "fill-green-500 text-green-700 dark:text-green-400" : ""}`} />
            {approved ? t("hitl.approved") : t("hitl.approve")}
          </button>

          {/* Edit button */}
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-colors"
            >
              <Edit3 className="w-3.5 h-3.5" />
              {t("hitl.edit")}
            </button>
          )}

          {/* Refine with AI button */}
          <button
            onClick={() => setShowRefine(!showRefine)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              showRefine
                ? "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400 border border-violet-300 dark:border-violet-700"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-violet-50 dark:hover:bg-violet-950/20 border border-transparent"
            }`}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t("hitl.refine")}
          </button>
        </div>

        {/* Refine feedback input */}
        {showRefine && (
          <div className="mt-2.5 flex gap-2">
            <input
              type="text"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleRefineSubmit(); }}
              placeholder={t("hitl.refine.placeholder")}
              className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-xs outline-none focus:ring-2 focus:ring-violet-500"
              autoFocus
            />
            <button
              onClick={handleRefineSubmit}
              disabled={!feedback.trim()}
              className="px-3 py-1.5 bg-violet-600 hover:bg-violet-700 disabled:bg-gray-400 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1"
            >
              <Send className="w-3 h-3" />
              {t("hitl.send")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Trigger a file download in the browser */
function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Convert structured output to Markdown */
function toMarkdown(data: StructuredOutput): string {
  const lines: string[] = ["# TechPulse Social — Generated Content\n"];
  const now = new Date().toLocaleString();
  lines.push(`> Generated: ${now}\n`);

  for (const item of data.contents) {
    const meta = PLATFORM_META[item.platform];
    lines.push(`## ${meta?.label ?? item.platform}\n`);
    lines.push(item.body + "\n");
    if (item.hashtags.length > 0) {
      lines.push("**Hashtags:** " + item.hashtags.map((h) => (h.startsWith("#") ? h : `#${h}`)).join(" ") + "\n");
    }
    if (item.call_to_action) lines.push(`**CTA:** ${item.call_to_action}\n`);
    if (item.posting_time) lines.push(`**Posting Time:** ${item.posting_time}\n`);
    lines.push("---\n");
  }

  if (data.review && data.review.overall_score > 0) {
    lines.push("## Quality Review\n");
    lines.push(`**Overall Score:** ${data.review.overall_score}/10\n`);
    const s = data.review.scores;
    lines.push(`| Metric | Score |`);
    lines.push(`|--------|-------|`);
    lines.push(`| Brand Alignment | ${s.brand_alignment}/10 |`);
    lines.push(`| Audience Relevance | ${s.audience_relevance}/10 |`);
    lines.push(`| Engagement Potential | ${s.engagement_potential}/10 |`);
    lines.push(`| Clarity | ${s.clarity}/10 |`);
    lines.push(`| Platform Optimization | ${s.platform_optimization}/10 |\n`);
    if (data.review.feedback.length > 0) {
      lines.push("**Feedback:**");
      data.review.feedback.forEach((f) => lines.push(`- ${f}`));
      lines.push("");
    }
  }

  if (data.sources_used && data.sources_used.length > 0) {
    lines.push("## Sources\n");
    data.sources_used.forEach((s) => lines.push(`- ${s}`));
  }

  return lines.join("\n");
}

export default function ContentCards({ data, t, onRefine, safetyResult }: ContentCardsProps) {
  const { contents, review, sources_used } = data;

  const handleExportMarkdown = () => {
    const md = toMarkdown(data);
    downloadFile("techpulse-content.md", md, "text/markdown;charset=utf-8");
  };

  const handleExportJSON = () => {
    const json = JSON.stringify(data, null, 2);
    downloadFile("techpulse-content.json", json, "application/json;charset=utf-8");
  };

  return (
    <div className="space-y-4">
      {/* Platform cards */}
      <div className="grid grid-cols-1 gap-4">
        {contents.map((item, i) => (
          <PlatformCard key={`${item.platform}-${i}`} item={item} t={t} onRefine={onRefine} />
        ))}
      </div>

      {/* Quality Review — Radar Chart + Scores */}
      {review && review.overall_score > 0 && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 bg-emerald-50 dark:bg-emerald-950/20 border-b border-emerald-100 dark:border-emerald-900">
            <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
              {t("review.title")}
              {/* Content Safety Badge — dynamic based on real safety analysis */}
              {safetyResult ? (
                safetyResult.safe ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700">
                    <ShieldCheck className="w-3 h-3" />
                    {t("review.safe") || "Content Safe"}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-700">
                    <ShieldAlert className="w-3 h-3" />
                    {t("review.unsafe") || "Safety Issue"}
                  </span>
                )
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600">
                  <ShieldCheck className="w-3 h-3" />
                  {t("review.safetyPending") || "Checking..."}
                </span>
              )}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent">
                {review.overall_score}
              </span>
              <span className="text-sm text-gray-400 dark:text-gray-500">/10</span>
            </div>
          </div>
          <div className="flex flex-col md:flex-row">
            {/* Radar Chart */}
            <div className="flex-shrink-0 w-full md:w-56 h-52 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart
                  data={[
                    { metric: t("review.brandAlignment") || "Brand", value: review.scores.brand_alignment, max: 10 },
                    { metric: t("review.audienceRelevance") || "Audience", value: review.scores.audience_relevance, max: 10 },
                    { metric: t("review.engagementPotential") || "Engagement", value: review.scores.engagement_potential, max: 10 },
                    { metric: t("review.clarity") || "Clarity", value: review.scores.clarity, max: 10 },
                    { metric: t("review.platformOptimization") || "Platform", value: review.scores.platform_optimization, max: 10 },
                  ]}
                >
                  <PolarGrid stroke="#e5e7eb" className="dark:stroke-gray-700" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{ fontSize: 9, fill: "#9ca3af" }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 10]}
                    tick={{ fontSize: 8 }}
                    tickCount={3}
                  />
                  <Radar
                    dataKey="value"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.25}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            {/* Score Bars */}
            <div className="flex-1 px-4 py-3 space-y-2">
              <ScoreBar score={review.scores.brand_alignment} label={t("review.brandAlignment")} />
              <ScoreBar score={review.scores.audience_relevance} label={t("review.audienceRelevance")} />
              <ScoreBar score={review.scores.engagement_potential} label={t("review.engagementPotential")} />
              <ScoreBar score={review.scores.clarity} label={t("review.clarity")} />
              <ScoreBar score={review.scores.platform_optimization} label={t("review.platformOptimization")} />
            </div>
          </div>
          {review.feedback.length > 0 && (
            <div className="px-4 pb-3">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{t("review.feedback")}</p>
              <ul className="text-xs text-gray-600 dark:text-gray-300 space-y-0.5">
                {review.feedback.map((f, i) => (
                  <li key={i}>• {f}</li>
                ))}
              </ul>
            </div>
          )}
          {review.improvements_made && review.improvements_made.length > 0 && (
            <div className="px-4 pb-3">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{t("review.improvements") || "Improvements Made"}</p>
              <ul className="text-xs text-gray-600 dark:text-gray-300 space-y-0.5">
                {review.improvements_made.map((imp, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                    {imp}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Sources — upgraded with link icons */}
      {sources_used && sources_used.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-lg px-4 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-1.5">
            {t("content.sources")}
          </p>
          <div className="flex flex-wrap gap-2">
            {sources_used.map((src, i) => (
              <a
                key={i}
                href={src.startsWith("http") ? src : undefined}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                <span className="truncate max-w-[200px]">{src.replace(/^https?:\/\/(www\.)?/, "")}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Export bar */}
      <div className="flex items-center justify-end gap-2 pt-1">
        <button
          onClick={handleExportMarkdown}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-blue-50 dark:hover:bg-blue-950/20 border border-gray-200 dark:border-gray-700 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          {t("export.markdown")}
        </button>
        <button
          onClick={handleExportJSON}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-blue-50 dark:hover:bg-blue-950/20 border border-gray-200 dark:border-gray-700 transition-colors"
        >
          <Download className="w-3.5 h-3.5" />
          {t("export.json")}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// A/B Comparison View
// ============================================================

/** Mini score radar for A/B comparison — smaller variant */
function MiniRadarChart({ review, t }: { review: ContentReview; t: (key: string) => string }) {
  return (
    <div className="w-full h-40">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart
          data={[
            { metric: t("review.brandAlignment") || "Brand", value: review.scores.brand_alignment },
            { metric: t("review.audienceRelevance") || "Audience", value: review.scores.audience_relevance },
            { metric: t("review.engagementPotential") || "Engage", value: review.scores.engagement_potential },
            { metric: t("review.clarity") || "Clarity", value: review.scores.clarity },
            { metric: t("review.platformOptimization") || "Platform", value: review.scores.platform_optimization },
          ]}
        >
          <PolarGrid stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 8, fill: "#9ca3af" }} />
          <PolarRadiusAxis angle={90} domain={[0, 10]} tick={false} />
          <Radar dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.25} strokeWidth={2} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface ABCompareCardsProps {
  data: ABStructuredOutput;
  t: (key: string) => string;
  onRefine?: (platform: string, feedback: string) => void;
}

export function ABCompareCards({ data, t, onRefine }: ABCompareCardsProps) {
  const [selected, setSelected] = useState<"a" | "b" | null>(null);

  const variants = [
    { key: "a" as const, label: "A", data: data.variant_a, gradient: "from-blue-500 to-indigo-600" },
    { key: "b" as const, label: "B", data: data.variant_b, gradient: "from-purple-500 to-pink-600" },
  ];

  const winner = data.variant_a.review.overall_score >= data.variant_b.review.overall_score ? "a" : "b";

  return (
    <div className="space-y-4">
      {/* A/B Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-2 py-1 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white">
            A/B
          </span>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t("ab.title") || "Content Comparison"}
          </span>
        </div>
        {selected && (
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {t("ab.selected") || "Selected"}: {t("ab.variant") || "Variant"} {selected.toUpperCase()}
          </span>
        )}
      </div>

      {/* Side-by-side variants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {variants.map(({ key, label, data: v, gradient }) => {
          const isWinner = key === winner;
          const isSelected = key === selected;

          return (
            <div
              key={key}
              className={`relative rounded-xl border-2 transition-all ${
                isSelected
                  ? "border-emerald-400 dark:border-emerald-500 shadow-lg shadow-emerald-100 dark:shadow-emerald-950/20"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              {/* Variant header */}
              <div className={`flex items-center justify-between px-4 py-2.5 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r ${gradient} bg-opacity-5`}>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold px-2 py-0.5 rounded-md bg-gradient-to-r ${gradient} text-white`}>
                    {label}
                  </span>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-300 max-w-[200px] truncate">
                    {v.strategy}
                  </span>
                  {isWinner && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                      <Trophy className="w-3 h-3" />
                      {t("ab.winner") || "Higher Score"}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <span className={`text-lg font-bold bg-gradient-to-r ${gradient} bg-clip-text text-transparent`}>
                    {v.review.overall_score}
                  </span>
                  <span className="text-xs text-gray-400">/10</span>
                </div>
              </div>

              {/* Content preview */}
              <div className="p-3 space-y-3">
                {/* Platform cards mini */}
                {v.contents.map((item, i) => {
                  const meta = PLATFORM_META[item.platform] ?? PLATFORM_META.linkedin;
                  return (
                    <div key={i} className={`rounded-lg border ${meta.borderColor} ${meta.bgColor} p-3`}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={meta.color}>{meta.icon}</span>
                        <span className="text-xs font-semibold">{meta.label}</span>
                        <span className="text-[10px] text-gray-400">{item.body.length} chars</span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-3 whitespace-pre-wrap">
                        {item.body}
                      </p>
                      {item.hashtags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {item.hashtags.slice(0, 5).map((h, j) => (
                            <span key={j} className="text-[10px] text-blue-500 dark:text-blue-400">
                              {h.startsWith("#") ? h : `#${h}`}
                            </span>
                          ))}
                        </div>
                      )}
                      {item.image_base64 && (
                        <img
                          src={`data:image/png;base64,${item.image_base64}`}
                          alt={`${item.platform} visual`}
                          className="mt-2 rounded-md w-full h-24 object-cover"
                        />
                      )}
                    </div>
                  );
                })}

                {/* Mini radar chart */}
                <MiniRadarChart review={v.review} t={t} />

                {/* Select button */}
                <button
                  onClick={() => setSelected(key)}
                  className={`w-full py-2 rounded-lg text-sm font-medium transition-all ${
                    isSelected
                      ? "bg-emerald-500 text-white shadow-sm"
                      : `bg-gradient-to-r ${gradient} bg-opacity-10 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:shadow-sm`
                  }`}
                >
                  {isSelected
                    ? `✓ ${t("ab.selected") || "Selected"}`
                    : `${t("ab.select") || "Select"} ${t("ab.variant") || "Variant"} ${label}`
                  }
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected variant full view */}
      {selected && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            {t("ab.fullView") || "Full view"}: {t("ab.variant") || "Variant"} {selected.toUpperCase()} — {selected === "a" ? data.variant_a.strategy : data.variant_b.strategy}
          </p>
          <ContentCards
            data={{
              contents: selected === "a" ? data.variant_a.contents : data.variant_b.contents,
              review: selected === "a" ? data.variant_a.review : data.variant_b.review,
              sources_used: data.sources_used,
            }}
            t={t}
            onRefine={onRefine}
          />
        </div>
      )}

      {/* Sources */}
      {data.sources_used && data.sources_used.length > 0 && !selected && (
        <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-lg px-4 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-1.5">
            {t("content.sources")}
          </p>
          <div className="flex flex-wrap gap-2">
            {data.sources_used.map((src, i) => (
              <a
                key={i}
                href={src.startsWith("http") ? src : undefined}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                <span className="truncate max-w-[200px]">{src.replace(/^https?:\/\/(www\.)?/, "")}</span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
