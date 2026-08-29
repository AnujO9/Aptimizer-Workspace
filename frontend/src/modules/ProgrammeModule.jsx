import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarCheck,
  CalendarX,
  ChevronDown,
  ChevronRight,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Users,
  X,
} from "lucide-react";
import { api, apiError } from "../lib/api";
import { Metric, NumField, Section } from "../components/Field";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { AiPanel } from "../components/AiPanel";
import { int, money, num } from "../lib/format";

const PHASE_COLOR = {
  "Pre-construction": "#94A3B8",
  Substructure: "#78716C",
  Superstructure: "#2563EB",
  Blockwork: "#0EA5E9",
  MEP: "#8B5CF6",
  Finishing: "#F59E0B",
  "External works": "#16A34A",
  Handover: "#DC2626",
};
const PHASES = Object.keys(PHASE_COLOR);

const day = (s) => (s ? new Date(`${s}T00:00:00`) : null);
const fmt = (s) => (s ? day(s).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—");
const trade = (k) => k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const plural = (n, w) => `${int(n)} ${w}${Math.abs(n) === 1 ? "" : "s"}`;

// How the metric strip and the banner read for each solver outcome. `unreachable` is the
// one that matters: the programme floor is IS 456 curing and prop removal, so a target
// below it is refused rather than met by compressing something that must not be.
const TARGET_TONE = {
  already_met: "success",
  met_with_more_labour: "success",
  unreachable: "danger",
  invalid: "danger",
};

function TargetBanner({ target }) {
  if (!target) return null;
  const bad = TARGET_TONE[target.status] === "danger";
  const Icon = bad ? CalendarX : CalendarCheck;
  const changes = Object.entries(target.crew_changes || {});
  return (
    <div
      className={`text-[11px] rounded-sm border px-2 py-1.5 flex gap-2 ${
        bad ? "text-red-800 bg-red-50 border-red-200" : "text-emerald-900 bg-emerald-50 border-emerald-200"
      }`}
      data-testid="prog-target-result"
    >
      <Icon className={`h-4 w-4 shrink-0 mt-px ${bad ? "text-red-500" : "text-emerald-600"}`} />
      <div className="space-y-1">
        {target.status === "already_met" && (
          <p>
            The programme already finishes{" "}
            <span className="font-semibold">{plural(target.days_early, "day")}</span> inside your{" "}
            {fmt(target.requested_finish)} finish date, so the crews were left exactly as entered.
          </p>
        )}
        {target.status === "met_with_more_labour" && (
          <p>
            Planned to finish <span className="font-semibold">{fmt(target.achieved_finish)}</span> —{" "}
            {plural(target.days_early, "day")} inside your finish date and{" "}
            {plural(target.days_saved, "day")} earlier than the {fmt(target.baseline_finish)} the
            entered crews would give.
          </p>
        )}
        {target.status === "unreachable" && (
          <p>
            <span className="font-semibold">{fmt(target.requested_finish)} cannot be reached safely.</span>{" "}
            The earliest completion is {fmt(target.earliest_possible_finish)},{" "}
            {plural(target.days_short, "day")} later, even at the labour ceiling. {target.note}
          </p>
        )}
        {target.status === "invalid" && <p>{target.note}</p>}
        {changes.length > 0 && (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-emerald-800">
            <Users className="h-3.5 w-3.5 shrink-0" />
            {changes.map(([k, c]) => (
              <span key={k} className="font-mono">
                {trade(k)} {c.from}→{c.to}
              </span>
            ))}
          </p>
        )}
      </div>
    </div>
  );
}

const BLANK_TASK = { name: "", phase: "Finishing", days: 5, after: "" };

/** Compact form for work the quantities cannot know about -- approvals, a vendor scope. */
function AddTaskRow({ byPhase, onAdd, disabled }) {
  const [draft, setDraft] = useState(BLANK_TASK);
  const set = (k, v) => setDraft((d) => ({ ...d, [k]: v }));
  const ready = draft.name.trim().length > 0;

  return (
    <div className="border-t border-slate-200 pt-3 mt-3 space-y-2" data-testid="prog-add-task">
      <p className="text-[11px] text-slate-500">
        Add work the quantities cannot know about — a client approval, a compound wall, lift
        erection by a vendor. It joins the critical path like any other task.
      </p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-[2fr_1fr_0.7fr_2fr_auto] gap-2 items-end">
        <div className="space-y-1">
          <label className="text-[10px] uppercase tracking-wide text-slate-500">Task name</label>
          <Input className="h-9 rounded-sm text-sm" value={draft.name} disabled={disabled}
            placeholder="Lift erection by vendor" data-testid="prog-task-name"
            onChange={(e) => set("name", e.target.value)} />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] uppercase tracking-wide text-slate-500">Phase</label>
          <select className="h-9 w-full rounded-sm border border-slate-200 bg-white px-2 text-sm"
            value={draft.phase} disabled={disabled} data-testid="prog-task-phase"
            onChange={(e) => set("phase", e.target.value)}>
            {PHASES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] uppercase tracking-wide text-slate-500">Days</label>
          <Input type="number" min={1} className="h-9 rounded-sm font-mono text-sm"
            value={draft.days} disabled={disabled} data-testid="prog-task-days"
            onChange={(e) => set("days", Math.max(1, Number(e.target.value) || 1))} />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] uppercase tracking-wide text-slate-500">Starts after</label>
          {/* Grouped by phase: a flat list of every task on a tower job is hundreds of
              options long and impossible to pick from. */}
          <select className="h-9 w-full rounded-sm border border-slate-200 bg-white px-2 text-sm"
            value={draft.after} disabled={disabled} data-testid="prog-task-after"
            onChange={(e) => set("after", e.target.value)}>
            <option value="">Project start</option>
            {Object.entries(byPhase).map(([phase, rows]) => (
              <optgroup key={phase} label={phase}>
                {rows.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </optgroup>
            ))}
          </select>
        </div>
        <Button className="rounded-sm h-9" disabled={disabled || !ready} data-testid="prog-task-add"
          onClick={() => { onAdd({ ...draft, name: draft.name.trim() }); setDraft(BLANK_TASK); }}>
          <Plus className="h-3.5 w-3.5 mr-1" />Add
        </Button>
      </div>
    </div>
  );
}

export default function ProgrammeModule({ project, projectId, readOnly, setProject }) {
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState({});          // phase name -> task rows expanded
  const [cfg, setCfg] = useState({
    start_date: new Date().toISOString().slice(0, 10),
    target_finish: "",          // empty = plan as the quantities fall out
    mobilisation_days: 10,
    blockwork_lag_floors: 2,
    crews: {},
    extra_tasks: [],
    excluded_tasks: [],
  });

  // `next` lets an edit re-plan with the config it just produced rather than waiting a
  // render for setCfg to land.
  const run = useCallback(async (next) => {
    const body = next || cfg;
    setBusy(true);
    setErr("");
    try {
      const { data } = await api.post(`/projects/${projectId}/schedule`, { config: body });
      if (data.ok) setPlan(data);
      else { setPlan(null); setErr(data.error?.message || "Could not build a programme."); }
    } catch (e) {
      setPlan(null);
      setErr(apiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  }, [projectId, cfg]);

  useEffect(() => { run(); /* eslint-disable-next-line */ }, [projectId]);

  const apply = (next) => { setCfg(next); run(next); };
  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));

  const addTask = (t) => apply({ ...cfg, extra_tasks: [...cfg.extra_tasks, t] });
  const removeTask = (id) =>
    apply(id.startsWith("custom_")
      ? { ...cfg, extra_tasks: cfg.extra_tasks.filter((_, i) => `custom_${i}` !== id) }
      : { ...cfg, excluded_tasks: [...cfg.excluded_tasks, id] });
  const restoreAll = () => apply({ ...cfg, excluded_tasks: [] });

  // One shared time axis so every phase bar is comparable.
  const axis = useMemo(() => {
    if (!plan?.phases?.length) return null;
    const t0 = day(plan.start).getTime();
    const t1 = day(plan.finish).getTime();
    const span = Math.max(t1 - t0, 1);
    return { t0, span, pct: (s) => ((day(s).getTime() - t0) / span) * 100 };
  }, [plan]);

  const tasks = plan?.activities || [];
  // Tasks grouped under the phase they belong to, and an id -> name map so a dependency
  // reads as "Tower A: floor 3 slab" rather than "t0_slabcast_3".
  const { byPhase, nameOf } = useMemo(() => {
    const g = {};
    const n = {};
    for (const t of tasks) {
      n[t.id] = t.name;
      (g[t.phase] = g[t.phase] || []).push(t);
    }
    for (const k of Object.keys(g)) g[k].sort((a, b) => (a.start || "").localeCompare(b.start || ""));
    return { byPhase: g, nameOf: n };
  }, [tasks]);

  return (
    <div className="space-y-4">
      {/* Start sits beside completion so the strip reads as a span, not just an end date.
          Dates are long, so this goes six across only once there is room for it. */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <Metric label="Build duration" value={num(plan?.duration_months, 1)} unit="months"
          testid="prog-duration" />
        <Metric label="Calendar days" value={int(plan?.duration_calendar_days)} testid="prog-days" />
        <Metric label="Start" value={plan ? fmt(plan.start) : "—"} testid="prog-start" />
        <Metric label="Completion" value={plan ? fmt(plan.finish) : "—"} testid="prog-finish"
          tone={TARGET_TONE[plan?.target?.status]} />
        <Metric label="Floor cycle" value={int(plan?.safety?.floor_cycle_days)} unit="days"
          testid="prog-cycle" />
        <Metric label="Phases" value={int(plan?.phases?.length)} testid="prog-phases" />
      </div>

      <p className="text-[11px] text-slate-500">
        <span className="font-semibold text-slate-700">Floor cycle</span> is how many days it takes
        to complete one typical floor — pouring columns, laying the slab, and waiting for the
        concrete to set — so a 20-storey tower takes roughly 20 × that many days to reach the top.
        Open any phase in the breakdown below to see every task it includes.
      </p>

      {err && (
        <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-sm px-2 py-1.5"
          data-testid="prog-error">{err}</p>
      )}

      <TargetBanner target={plan?.target} />

      {plan?.safety && (
        <p className="text-[11px] text-slate-700 bg-slate-50 border border-slate-200 rounded-sm px-2 py-1.5 flex gap-2"
          data-testid="prog-safety">
          <ShieldAlert className="h-4 w-4 shrink-0 text-slate-500 mt-px" />
          <span>
            Each floor needs at least{" "}
            <span className="font-semibold">{plan.safety.prop_removal_days} calendar days</span> for
            the concrete to gain enough strength before the supports can be removed ({plan.safety.governing_rule}).
            Adding more workers shortens other tasks, but never this waiting period.
          </span>
        </p>
      )}

      {(plan?.safety?.findings || []).map((f, i) => (
        <p key={i} className="text-[11px] text-red-800 bg-red-50 border border-red-200 rounded-sm px-2 py-1.5"
          data-testid={`prog-safety-finding-${i}`}>{f.text}</p>
      ))}

      {(plan?.warnings || []).filter((w) => w.severity === "critical").map((w, i) => (
        <p key={i} className="text-[11px] text-red-800 bg-red-50 border border-red-200 rounded-sm px-2 py-1.5"
          data-testid={`prog-warning-${i}`}>{w.text}</p>
      ))}

      <Section
        title="Programme assumptions"
        description="Durations are derived from the project's own quantities: work days = quantity ÷ (daily output × crew). Enter a finish date and the crews are sized to hit it instead."
        testid="prog-config"
        actions={
          <Button onClick={() => run()} disabled={busy || readOnly} className="rounded-sm h-8" data-testid="prog-run">
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${busy ? "animate-spin" : ""}`} />
            {busy ? "Planning…" : "Re-plan"}
          </Button>
        }
      >
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          <div className="space-y-1">
            <label className="text-[11px] uppercase tracking-wide text-slate-500">Start date</label>
            <Input type="date" className="h-9 rounded-sm" value={cfg.start_date} disabled={readOnly}
              onChange={(e) => set("start_date", e.target.value)} data-testid="prog-start-input" />
            <p className="text-[10px] leading-snug text-slate-500">
              The day the site is handed over and work can begin.
            </p>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] uppercase tracking-wide text-slate-500">Finish date</label>
            <Input type="date" className="h-9 rounded-sm" value={cfg.target_finish} disabled={readOnly}
              min={cfg.start_date} onChange={(e) => set("target_finish", e.target.value)}
              data-testid="prog-target-input" />
            <p className="text-[10px] leading-snug text-slate-500">
              Optional. Set a date and the crews are sized to hit it. Leave blank to see how long
              the job takes on its own.
            </p>
          </div>
          <NumField label="Site setup (days)" value={cfg.mobilisation_days} disabled={readOnly}
            onChange={(v) => set("mobilisation_days", v)} testid="prog-mobilisation-input"
            hint="Days needed to set up the site — offices, fencing, water, power — before actual building begins." />
          <NumField label="Masonry starts after (floors)" value={cfg.blockwork_lag_floors} disabled={readOnly}
            onChange={(v) => set("blockwork_lag_floors", v)} testid="prog-blocklag-input"
            hint="How many floors ahead the concrete frame must be before wall work begins. Higher = safer but slower." />
          <NumField label="Concrete crew size" value={cfg.crews.concretor || 6} disabled={readOnly}
            onChange={(v) => setCfg((c) => ({ ...c, crews: { ...c.crews, concretor: v } }))}
            testid="prog-crew-concretor"
            hint="Number of concrete teams working at the same time. More teams = faster, but limited by drying/curing time." />
        </div>
      </Section>

      <Section title="Phase timeline" description="Each bar spans that phase's first start to its last finish; phases overlap by design."
        testid="prog-timeline">
        {!plan?.phases?.length ? (
          <p className="text-sm text-slate-500">Run the programme to see the timeline.</p>
        ) : (
          <div className="space-y-1.5">
            {plan.phases.map((ph) => {
              const left = axis.pct(ph.start);
              const width = Math.max(axis.pct(ph.finish) - left, 0.6);
              return (
                <div key={ph.phase} className="grid grid-cols-[150px_1fr_86px] items-center gap-2"
                  data-testid={`prog-phase-${ph.phase.replace(/\s+/g, "-").toLowerCase()}`}>
                  <span className="text-xs text-slate-700 truncate" title={ph.phase}>{ph.phase}</span>
                  <div className="relative h-5 bg-slate-100 rounded-sm">
                    <div
                      className="absolute h-5 rounded-sm"
                      style={{ left: `${left}%`, width: `${width}%`,
                               background: PHASE_COLOR[ph.phase] || "#64748B" }}
                      title={`${fmt(ph.start)} → ${fmt(ph.finish)}`}
                    />
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 text-right">{int(ph.calendar_days)}d</span>
                </div>
              );
            })}
            <div className="grid grid-cols-[150px_1fr_86px] gap-2 pt-1">
              <span />
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>{fmt(plan.start)}</span><span>{fmt(plan.finish)}</span>
              </div>
              <span />
            </div>
          </div>
        )}
      </Section>

      <Section
        title="Phase breakdown"
        description="Open a phase to read the tasks it is made of — what each one waits for, how long it takes, how many people it needs and what it costs. A phase's days are calendar days end to end; a task's are working days, so Sundays, holidays and monsoon stoppages are not counted. A red dot marks the critical path: a day lost there is a day lost on the completion date."
        testid="prog-phase-table"
        actions={cfg.excluded_tasks.length > 0 && (
          <Button variant="outline" className="rounded-sm h-8" onClick={restoreAll}
            disabled={busy || readOnly} data-testid="prog-restore-tasks">
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
            Restore {plural(cfg.excluded_tasks.length, "removed task")}
          </Button>
        )}
      >
        {!plan?.phases?.length ? (
          <p className="text-sm text-slate-500">—</p>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phase / task</TableHead>
                  <TableHead>Waits for</TableHead>
                  <TableHead className="text-right">Start</TableHead>
                  <TableHead className="text-right">Finish</TableHead>
                  <TableHead className="text-right">Days</TableHead>
                  <TableHead className="text-right">Crew</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="w-8" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {plan.phases.map((ph) => {
                  const rows = byPhase[ph.phase] || [];
                  const isOpen = !!open[ph.phase];
                  const Chevron = isOpen ? ChevronDown : ChevronRight;
                  return [
                    <TableRow key={ph.phase} className="cursor-pointer hover:bg-slate-50"
                      onClick={() => setOpen((o) => ({ ...o, [ph.phase]: !o[ph.phase] }))}
                      data-testid={`prog-phase-row-${ph.phase.replace(/\s+/g, "-").toLowerCase()}`}>
                      <TableCell className="py-1.5 text-xs font-medium">
                        <span className="flex items-center gap-1.5">
                          <Chevron className="h-3.5 w-3.5 text-slate-400" />
                          <span className="h-2 w-2 rounded-sm shrink-0"
                            style={{ background: PHASE_COLOR[ph.phase] || "#64748B" }} />
                          {ph.phase}
                          {/* Counted off the rows this actually reveals -- ph.activities
                              leaves milestones out, and a header that says 3 opening to
                              4 lines reads as a bug. */}
                          <span className="text-slate-400 font-normal">
                            ({plural(rows.length || ph.activities, "task")})
                          </span>
                        </span>
                      </TableCell>
                      <TableCell />
                      <TableCell className="py-1.5 text-xs text-right font-mono">{fmt(ph.start)}</TableCell>
                      <TableCell className="py-1.5 text-xs text-right font-mono">{fmt(ph.finish)}</TableCell>
                      <TableCell className="py-1.5 text-xs text-right font-mono"
                        title="Calendar days from this phase's first start to its last finish">
                        {int(ph.calendar_days)}
                      </TableCell>
                      <TableCell />
                      <TableCell className="py-1.5 text-xs text-right font-mono">{money(ph.cost, "INR")}</TableCell>
                      <TableCell />
                    </TableRow>,
                    ...(isOpen ? rows.map((t) => (
                      <TableRow key={t.id} className="bg-slate-50/60"
                        data-testid={`prog-task-${t.id}`}>
                        <TableCell className="py-1 text-xs pl-8">
                          <span className="flex items-center gap-1.5">
                            {t.critical && (
                              <span className="h-1.5 w-1.5 rounded-full bg-red-500 shrink-0"
                                title="On the critical path — a day lost here is a day lost on the completion date" />
                            )}
                            <span className={t.critical ? "text-slate-900" : "text-slate-600"}>{t.name}</span>
                            {t.custom && (
                              <span className="text-[9px] uppercase tracking-wide text-blue-600 border border-blue-200 bg-blue-50 rounded-sm px-1">
                                added
                              </span>
                            )}
                          </span>
                        </TableCell>
                        <TableCell className="py-1 text-[11px] text-slate-500 max-w-[180px] truncate"
                          title={(t.predecessors || []).map((p) => nameOf[p.id] || p.id).join(", ")}>
                          {t.driver ? (nameOf[t.driver] || t.driver) : "—"}
                        </TableCell>
                        <TableCell className="py-1 text-[11px] text-right font-mono text-slate-600">{fmt(t.start)}</TableCell>
                        <TableCell className="py-1 text-[11px] text-right font-mono text-slate-600">{fmt(t.finish)}</TableCell>
                        <TableCell className="py-1 text-[11px] text-right font-mono text-slate-600"
                          title="Working days — Sundays, holidays and monsoon stoppages are not counted">
                          {t.milestone ? "—" : int(t.work_days)}
                        </TableCell>
                        <TableCell className="py-1 text-[11px] text-right font-mono text-slate-600">
                          {t.milestone ? "—" : int(t.crew)}
                        </TableCell>
                        <TableCell className="py-1 text-[11px] text-right font-mono text-slate-600">
                          {t.cost ? money(t.cost, "INR") : "—"}
                        </TableCell>
                        <TableCell className="py-1 text-right">
                          {t.removable && !readOnly && (
                            <button
                              onClick={() => removeTask(t.id)}
                              disabled={busy}
                              className="text-slate-300 hover:text-red-600 transition-colors"
                              title={`Remove "${t.name}" from the programme`}
                              data-testid={`prog-task-remove-${t.id}`}
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </TableCell>
                      </TableRow>
                    )) : []),
                  ];
                })}
              </TableBody>
            </Table>
            {!readOnly && <AddTaskRow byPhase={byPhase} onAdd={addTask} disabled={busy} />}
            {plan.floats_verified === false && (
              <p className="text-[10px] text-slate-400 mt-2">
                Spare time per task is an upper bound on a programme this size — the critical
                path and every date above are exact.
              </p>
            )}
          </>
        )}
      </Section>

      {plan?.cost_check && (
        <p className="text-[11px] text-slate-500" data-testid="prog-cost-check">
          Programme prices {money(plan.cost_check.scheduled_cost, "INR")} of the{" "}
          {money(plan.cost_check.boq_grand_total, "INR")} BOQ total. {plan.cost_check.note}
        </p>
      )}

      <AiPanel
        title="AI programme review"
        description="Reads the phase spans, floor cycle and critical path and says what actually drives the date"
        endpoint={`/projects/${projectId}/ai/report`}
        initial={project?.ai?.programme}
        onGenerated={(d) => setProject?.((p) => ({ ...p, ai: { ...(p.ai || {}), programme: d } }))}
        readOnly={readOnly}
        testid="ai-programme"
        emptyHint="Explain what is driving the completion date and where time could realistically be recovered."
      />
    </div>
  );
}
