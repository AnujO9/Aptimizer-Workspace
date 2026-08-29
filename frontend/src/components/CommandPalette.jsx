import { useEffect, useMemo, useRef, useState } from "react";
import { Search, CornerDownLeft } from "lucide-react";

/**
 * Ctrl/Cmd+K jump-to-module.
 *
 * Grouping the sidebar trades a click for vertical space. The palette pays that click
 * back: anyone who works in this daily reaches any module in two keystrokes without
 * opening a group at all.
 */
const score = (label, group, q) => {
  if (!q) return 0;
  const l = label.toLowerCase(), g = group.toLowerCase(), s = q.toLowerCase();
  if (l.startsWith(s)) return 100;
  if (l.includes(s)) return 60;
  if (g.includes(s)) return 40;
  // Subsequence match, so "isnbc" still finds "IS/NBC Engineering".
  let i = 0;
  for (const ch of l) if (ch === s[i]) i += 1;
  return i === s.length ? 20 : -1;
};

export function CommandPalette({ open, onClose, modules, groupLabel, onPick, active }) {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef(null);

  const results = useMemo(() => {
    const scored = modules
      .map((m) => ({ key: m[0], label: m[1], Icon: m[2], group: groupLabel(m[0]) }))
      .map((m) => ({ ...m, s: score(m.label, m.group, q) }))
      .filter((m) => m.s >= 0);
    scored.sort((a, b) => b.s - a.s || a.label.localeCompare(b.label));
    return scored;
  }, [q, modules, groupLabel]);

  useEffect(() => {
    if (open) {
      setQ("");
      setCursor(0);
      // The dialog mounts before the browser can focus it, so defer a frame.
      const t = setTimeout(() => inputRef.current?.focus(), 20);
      return () => clearTimeout(t);
    }
  }, [open]);

  useEffect(() => { setCursor(0); }, [q]);

  if (!open) return null;

  const choose = (key) => { onPick(key); onClose(); };

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); if (results[cursor]) choose(results[cursor].key); }
    else if (e.key === "Escape") { e.preventDefault(); onClose(); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-start justify-center pt-[12vh] px-4"
      onMouseDown={onClose} data-testid="command-palette">
      <div className="w-full max-w-lg bg-white rounded-sm shadow-xl border border-slate-200 overflow-hidden"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 px-3 border-b border-slate-200">
          <Search className="h-4 w-4 text-slate-400 shrink-0" />
          <input
            ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey}
            placeholder="Jump to a module…" data-testid="command-palette-input"
            className="w-full py-3 text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="text-[10px] font-mono text-slate-400 border border-slate-200 rounded-sm px-1 py-0.5">esc</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {results.length === 0 ? (
            <p className="px-4 py-6 text-sm text-slate-500 text-center">No module matches “{q}”.</p>
          ) : results.map((m, i) => (
            <button
              key={m.key}
              onMouseEnter={() => setCursor(i)}
              onClick={() => choose(m.key)}
              data-testid={`command-palette-item-${m.key}`}
              className={`w-full flex items-center gap-2.5 px-4 py-2 text-left text-sm transition-colors ${
                i === cursor ? "bg-blue-50 text-blue-900" : "hover:bg-slate-50"
              }`}
            >
              <m.Icon className="h-4 w-4 shrink-0 text-slate-400" />
              <span className="flex-1 truncate">{m.label}</span>
              <span className="text-[11px] text-slate-400">{m.group}</span>
              {m.key === active && <span className="text-[10px] text-blue-600 font-medium">current</span>}
              {i === cursor && <CornerDownLeft className="h-3 w-3 text-slate-400" />}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
