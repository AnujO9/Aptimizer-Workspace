import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Check, Copy, Send, Sparkles, Trash2 } from "lucide-react";
import { api, apiError, API_BASE, authHeaders } from "../lib/api";
import { Markdown } from "./AiPanel";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";

/** Marks references the app could not resolve against its own IS/NBC clause registry.
 *
 *  Never silently dropped: an answer that quietly loses its citation reads as if it never
 *  had one, and the reader has no way to know which part to check. Flagged and shown.
 */
function CitationFlags({ message }) {
  const bad = message.unverified_citations || [];
  const soft = message.unconfirmed_clauses || [];
  if (!bad.length && !soft.length) return null;
  return (
    <div className="mt-2 space-y-1" data-testid="apt-citation-flags">
      {bad.length > 0 && (
        <p className="text-[11px] text-red-800 bg-red-50 border border-red-200 rounded-sm px-2 py-1 flex gap-1.5"
          title="This standard is not in Aptimizer's clause registry. Verify it against the code before relying on it.">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-px" />
          <span>
            <span className="font-semibold">Could not verify:</span>{" "}
            <span className="font-mono">{bad.join(", ")}</span> — not in the app's clause
            registry. Check the code itself before relying on this.
          </span>
        </p>
      )}
      {soft.length > 0 && (
        <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1 flex gap-1.5"
          title="The standard is one the app knows; this particular clause number is not in its registry.">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-px" />
          <span>
            <span className="font-semibold">Clause unconfirmed:</span>{" "}
            <span className="font-mono">{soft.join(", ")}</span> — the standard is real, but
            the app does not carry that clause number to check it against.
          </span>
        </p>
      )}
    </div>
  );
}

function Bubble({ m }) {
  const [copied, setCopied] = useState(false);
  const mine = m.role === "user";

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(m.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy");
    }
  };

  return (
    <div className={`group ${mine ? "pl-8" : ""}`} data-testid={`apt-msg-${m.role}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">
          {mine ? "You" : "Apt"}
        </div>
        <button onClick={copy} title="Copy this message"
          className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-slate-700"
          data-testid="apt-copy">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      </div>
      <div className={mine
        ? "text-sm text-slate-800 bg-slate-100 border border-slate-200 rounded-sm px-2.5 py-1.5 whitespace-pre-wrap"
        : "border-l-2 border-blue-200 pl-3"}>
        {mine ? m.content : <Markdown text={m.content} testid="apt-answer" />}
      </div>
      {!mine && <CitationFlags message={m} />}
      {!mine && m.model && (
        <p className="text-[10px] text-slate-400 font-mono mt-1.5">{m.model}</p>
      )}
    </div>
  );
}

export default function AptPanel({ open, onOpenChange, projectId, module = "" }) {
  const [thread, setThread] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(undefined);
  const [suggestions, setSuggestions] = useState([]);
  const [streaming, setStreaming] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open || !projectId) return;
    api.get("/ai/status").then(({ data }) => setStatus(data)).catch(() => setStatus(null));
    api.get(`/projects/${projectId}/ai/chat`)
      .then(({ data }) => setThread(data.thread || [])).catch(() => {});
  }, [open, projectId]);

  // Suggestions are refetched on every module switch, so the opening questions are always
  // about the tab the user is looking at. Kept in its own effect so switching modules does
  // not also refetch the thread.
  useEffect(() => {
    if (!open || !projectId) return;
    api.get(`/projects/${projectId}/ai/chat/suggestions`, { params: { module } })
      .then(({ data }) => setSuggestions(data.suggestions || [])).catch(() => {});
  }, [open, projectId, module]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread, busy, streaming]);

  const notConfigured = status && status.configured === false;

  // Streamed with fetch rather than EventSource: EventSource cannot POST, and the
  // conversation has to go up with the request. Falls back to the plain endpoint if the
  // stream cannot be opened at all, so a proxy that buffers SSE degrades to the old
  // behaviour instead of breaking the panel.
  const send = useCallback(async (text) => {
    const content = (text ?? draft).trim();
    if (!content || busy) return;
    const next = [...thread, { role: "user", content }];
    setThread(next);
    setDraft("");
    setBusy(true);
    setStreaming("");

    const payload = { messages: next.map((m) => ({ role: m.role, content: m.content })) };
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/ai/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!res.ok || !res.body) throw new Error(`stream unavailable (${res.status})`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let acc = "";
      let finished = false;

      while (!finished) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE frames are separated by a blank line; a partial frame stays in the buffer.
        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";
        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          let evt;
          try { evt = JSON.parse(line.slice(5).trim()); } catch { continue; }
          if (evt.delta) { acc += evt.delta; setStreaming(acc); }
          if (evt.error) throw new Error(evt.error);
          if (evt.done) {
            setThread(evt.thread || [...next, evt.done]);
            finished = true;
          }
        }
      }
      if (!finished) throw new Error("stream ended before the answer was complete");
    } catch (err) {
      // One retry on the non-streaming route. It reuses the same context and the same
      // citation guard, so the answer is identical -- it just arrives all at once.
      try {
        const { data } = await api.post(`/projects/${projectId}/ai/chat`, payload);
        setThread(data.thread || [...next, data.reply]);
      } catch (e) {
        setThread(next);
        toast.error(apiError(e.response?.data?.detail) || err.message);
      }
    } finally {
      setStreaming("");
      setBusy(false);
      inputRef.current?.focus();
    }
  }, [draft, thread, busy, projectId]);

  const clear = async () => {
    try {
      await api.delete(`/projects/${projectId}/ai/chat`);
      setThread([]);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  const onKeyDown = (e) => {
    // Enter sends, Shift+Enter is a newline -- the convention every chat uses, and the
    // one an engineer pasting a multi-line calculation needs.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right"
        className="w-full sm:max-w-xl flex flex-col gap-0 p-0"
        data-testid="apt-panel">
        <SheetHeader className="px-4 py-3 border-b border-slate-200 space-y-0">
          <div className="flex items-center justify-between gap-2">
            <SheetTitle className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-600" />
              Apt
            </SheetTitle>
            {thread.length > 0 && (
              <Button variant="ghost" className="h-7 rounded-sm text-xs" onClick={clear}
                data-testid="apt-clear">
                <Trash2 className="h-3.5 w-3.5 mr-1" />Clear
              </Button>
            )}
          </div>
          <p className="text-[11px] text-slate-500">
            Answers from this project's own computed numbers, with IS/NBC citations checked
            against the app's clause registry.
          </p>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {notConfigured ? (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1.5"
              data-testid="apt-unconfigured">
              {status.detail || "No AI provider key is configured."}
            </p>
          ) : thread.length === 0 ? (
            <div className="space-y-3" data-testid="apt-empty">
              <p className="text-sm text-slate-600">
                Ask about any number in this project — where it came from, which clause
                governs it, or what would change if you moved an input.
              </p>
              {suggestions.length > 0 && (
                <p className="text-[10px] uppercase tracking-wider text-slate-400">
                  About what you are looking at
                </p>
              )}
              <div className="space-y-1.5">
                {suggestions.map((q) => (
                  <button key={q} onClick={() => send(q)} disabled={busy}
                    className="w-full text-left text-[12px] text-slate-700 border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 rounded-sm px-2.5 py-2 transition-colors"
                    data-testid="apt-suggestion">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            thread.map((m, i) => <Bubble key={i} m={m} />)
          )}
          {streaming ? (
            <div data-testid="apt-streaming">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Apt</div>
              <div className="border-l-2 border-blue-200 pl-3">
                <Markdown text={streaming} testid="apt-answer-streaming" />
              </div>
            </div>
          ) : busy ? (
            <p className="text-sm text-slate-400" data-testid="apt-thinking">Thinking…</p>
          ) : null}
          <div ref={endRef} />
        </div>

        <div className="border-t border-slate-200 p-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              rows={2}
              value={draft}
              disabled={busy || notConfigured}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about this project…"
              data-testid="apt-input"
              className="flex-1 resize-none rounded-sm border border-slate-200 px-2.5 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:bg-slate-50"
            />
            <Button onClick={() => send()} disabled={busy || !draft.trim() || notConfigured}
              className="rounded-sm h-9" data-testid="apt-send">
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5">
            Enter sends · Shift+Enter for a new line. Apt explains the engine's output; it
            does not recalculate, and it is not a substitute for an engineer's sign-off.
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
