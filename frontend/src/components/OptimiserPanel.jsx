import { useCallback, useEffect, useState } from "react";
import { ArrowRight, Check, RefreshCw, TrendingDown } from "lucide-react";
import { api, apiError } from "../lib/api";
import { Section } from "./Field";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { money, num } from "../lib/format";

/** Renders one optimiser's current -> best -> changes. Every optimiser shares this shape,
 *  so a result that only describes the present scheme is visibly missing its right half. */
function Result({ o, currency }) {
  if (!o) return null;
  const money_ = (v) => money(v, currency);
  const fmt = (m) => (m.unit === "INR" ? money_(m.value) : `${num(m.value, 1)}${m.unit ? ` ${m.unit}` : ""}`);
  const improves = o.delta?.improves;

  return (
    <div className="border border-slate-200 rounded-sm" data-testid={`opt-${o.id}`}>
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-3 py-2">
        <h4 className="text-sm font-semibold text-slate-900">{o.title}</h4>
        {improves ? (
          <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-sm px-1.5 py-0.5">
            <TrendingDown className="h-3 w-3 inline mr-1" />
            {num(o.delta.pct, 1)}% better
          </span>
        ) : (
          <span className="text-[11px] text-slate-500 bg-slate-50 border border-slate-200 rounded-sm px-1.5 py-0.5">
            <Check className="h-3 w-3 inline mr-1" />
            already the best found
          </span>
        )}
      </div>

      <div className="p-3 space-y-3">
        <div className="grid sm:grid-cols-[1fr_auto_1fr] gap-3 items-center">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Now</div>
            <div className="font-mono text-lg text-slate-900">{fmt(o.current)}</div>
            <div className="text-[11px] text-slate-500 leading-snug">{o.current.label}</div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-300 hidden sm:block" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">Best found</div>
            <div className={`font-mono text-lg ${improves ? "text-emerald-700" : "text-slate-900"}`}>
              {fmt(o.best)}
            </div>
            <div className="text-[11px] text-slate-500 leading-snug">{o.best.label}</div>
          </div>
        </div>

        {o.changes?.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              What has to change
            </div>
            {o.changes.map((c, i) => (
              <div key={i} className="text-[11px] text-slate-700 border-l-2 border-slate-200 pl-2">
                <span className="font-medium">{c.lever}</span>
                {c.to !== "unchanged" && (
                  <>
                    {" — "}
                    <span className="font-mono text-slate-500">{c.from}</span>
                    {" → "}
                    <span className="font-mono text-slate-900">{c.to}</span>
                  </>
                )}
                {c.effect && <div className="text-slate-500 leading-snug mt-0.5">{c.effect}</div>}
              </div>
            ))}
          </div>
        )}

        {!o.feasible && (
          <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1">
            Could not be reached with the levers available.
          </p>
        )}

        {o.notes?.map((n, i) => (
          <p key={i} className="text-[10px] text-slate-500 leading-snug">{n}</p>
        ))}
      </div>
    </div>
  );
}

/**
 * Which optimisers to show. The same panel is mounted in three modules, each showing the
 * ones that belong to what that module is about, so the results sit next to the numbers
 * they would change rather than in a tab of their own.
 */
const SETS = {
  quantities: { endpoint: "optimise", keys: ["waste", "quantity"] },
  boq: { endpoint: "optimise", keys: ["quantity", "materials"] },
  cost: { endpoint: "optimise", keys: ["budget", "materials"] },
  planning: { endpoint: "optimise/planning", keys: ["floors", "far", "fsi", "open_space", "mix"] },
  parking: { endpoint: "optimise/planning", keys: ["parking"] },
  utilities: { endpoint: "optimise/planning", keys: ["utilities"] },
};

export default function OptimiserPanel({ projectId, only = "cost", readOnly, currentCost }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [target, setTarget] = useState(0);

  const set = SETS[only] || SETS.cost;

  const run = useCallback(async (t) => {
    setBusy(true);
    setErr("");
    try {
      const { data: d } = await api.post(`/projects/${projectId}/${set.endpoint}`,
        set.endpoint === "optimise" ? { target_budget: t ?? target } : {});
      setData(d);
    } catch (e) {
      setData(null);
      setErr(apiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  }, [projectId, target, set.endpoint]);

  useEffect(() => { run(0); /* eslint-disable-next-line */ }, [projectId, only]);

  const wanted = set.keys;
  const showBudget = wanted.includes("budget");

  return (
    <Section
      title="Optimisers"
      description="What the scheme does now, the best found, and the change needed. Nothing is applied automatically."
      testid={`optimisers-${only}`}
      actions={
        <Button onClick={() => run()} disabled={busy || readOnly} className="rounded-sm h-8"
          data-testid="optimise-run">
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${busy ? "animate-spin" : ""}`} />
          {busy ? "Searching…" : "Re-run"}
        </Button>
      }
    >
      {err && (
        <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-sm px-2 py-1.5 mb-3"
          data-testid="optimise-error">{err}</p>
      )}

      {showBudget && (
        <div className="flex flex-wrap items-end gap-3 mb-3 pb-3 border-b border-slate-200">
          <div className="space-y-1">
            <label className="text-[11px] uppercase tracking-wide text-slate-500">
              Target budget (₹)
            </label>
            <Input type="number" className="h-9 rounded-sm font-mono text-sm w-48"
              value={target || ""} disabled={readOnly} data-testid="optimise-target"
              placeholder={currentCost ? Math.round(currentCost * 0.9) : "leave blank for −10%"}
              onChange={(e) => setTarget(Number(e.target.value) || 0)} />
          </div>
          <Button variant="outline" className="rounded-sm h-9" disabled={busy || readOnly}
            onClick={() => run()} data-testid="optimise-target-run">
            Search for it
          </Button>
          <p className="text-[10px] text-slate-500 max-w-sm leading-snug">
            Blank searches for 10% under today's cost. Only code-compliant changes are proposed.
          </p>
        </div>
      )}

      {!data ? (
        <p className="text-sm text-slate-500">{busy ? "Searching…" : "No results yet."}</p>
      ) : (
        <div className="space-y-3">
          {wanted.map((k) => <Result key={k} o={data[k]} currency={data.currency} />)}
        </div>
      )}
    </Section>
  );
}

export { Result as OptimiserResult };
