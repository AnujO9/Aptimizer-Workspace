import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";
import { api, apiError } from "../lib/api";
import { Section } from "./Field";
import { Button } from "./ui/button";
import { dt } from "../lib/format";

// Minimal markdown renderer for model output: bold, inline code, headings and bullets.
// Deliberately not a full parser -- the system prompts constrain the model to these few
// constructs, and a full markdown dependency is not worth it for that.
export const Markdown = ({ text, testid = "ai-summary-text" }) => (
  <div className="space-y-1.5 text-sm text-slate-700" data-testid={testid}>
    {String(text || "").split("\n").map((line, i) => {
      const html = line
        .replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-900">$1</strong>')
        .replace(/`(.+?)`/g, '<code class="font-mono text-xs bg-slate-100 px-1 rounded-sm">$1</code>');
      if (/^#{1,3}\s/.test(line))
        return (
          <h4 key={i} className="text-sm font-semibold tracking-tight text-slate-900 pt-2"
            dangerouslySetInnerHTML={{ __html: html.replace(/^#{1,3}\s/, "") }} />
        );
      if (/^[-*]\s/.test(line))
        return <li key={i} className="ml-4 list-disc" dangerouslySetInnerHTML={{ __html: html.replace(/^[-*]\s/, "") }} />;
      if (!line.trim()) return <div key={i} className="h-1" />;
      return <p key={i} dangerouslySetInnerHTML={{ __html: html }} />;
    })}
  </div>
);

// /ai/status is the same answer for every panel on the page, so it is fetched once per
// page load and shared, rather than once per panel.
let statusPromise = null;
const aiStatus = () => {
  if (!statusPromise)
    statusPromise = api.get("/ai/status").then(({ data }) => data).catch(() => null);
  return statusPromise;
};

/**
 * One AI analysis block: a Generate/Regenerate button and the markdown it produced.
 *
 * `initial` seeds the panel from an analysis already saved on the project document, so a
 * previously generated summary is visible on load without regenerating it. It seeds state
 * once on mount rather than staying bound to the prop -- otherwise an unrelated re-render
 * of the parent would overwrite a summary the user just generated with the older stored
 * one. `onGenerated` lets the parent mirror the new result into the in-memory project so
 * it survives a tab switch; the backend has already persisted it either way.
 */
export function AiPanel({
  title = "AI analysis",
  description,
  endpoint,
  method = "post",
  body,                    // optional POST payload, for endpoints that analyse live inputs
  initial = null,
  onGenerated,
  readOnly = false,
  disabled = false,
  disabledHint = "",
  emptyHint = "Generate a natural-language analysis of the results above.",
  testid = "ai-panel",
  buttonLabel = "Generate AI analysis",
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(initial);
  const [status, setStatus] = useState(undefined);

  useEffect(() => { aiStatus().then(setStatus); }, []);

  const notConfigured = status && status.configured === false;
  const blocked = readOnly || disabled || notConfigured;

  const run = async () => {
    setBusy(true);
    try {
      const { data } = method === "get" ? await api.get(endpoint) : await api.post(endpoint, body);
      setResult(data);
      if (onGenerated) onGenerated(data);
      toast.success("AI analysis generated");
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section
      title={title}
      description={description}
      testid={`${testid}-section`}
      actions={
        <Button onClick={run} disabled={busy || blocked} className="rounded-sm h-8"
          data-testid={`${testid}-button`}>
          <Sparkles className={`h-3.5 w-3.5 mr-1.5 ${busy ? "animate-pulse" : ""}`} />
          {busy ? "Generating…" : result ? "Regenerate" : buttonLabel}
        </Button>
      }
    >
      {notConfigured ? (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1"
          data-testid={`${testid}-unconfigured`}>
          {status.detail || "No AI provider key is configured."}
        </p>
      ) : disabled && disabledHint ? (
        <p className="text-sm text-slate-500" data-testid={`${testid}-disabled`}>{disabledHint}</p>
      ) : result ? (
        <>
          <Markdown text={result.text} testid={`${testid}-text`} />
          <p className="text-[11px] text-slate-400 font-mono mt-3">
            {result.model} · {dt(result.generated_at)}
          </p>
        </>
      ) : (
        <p className="text-sm text-slate-500">{emptyHint}</p>
      )}
    </Section>
  );
}
