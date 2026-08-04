import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, BookOpen, CheckCircle2, Search, XCircle } from "lucide-react";
import { api, apiError } from "@/lib/api";
import { ClauseChip, LibraryContext } from "@/components/Clause";
import { Metric, NumField, Section } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { num } from "@/lib/format";

const TABS = [
  ["loads", "1 · Structural Loads"],
  ["seismic", "2 · Seismic"],
  ["foundation", "3 · Foundation"],
  ["mix", "4 · Mix Design"],
  ["water", "5 · Water"],
  ["storm", "6 · Storm & RWH"],
  ["parking_nbc", "7 · Parking (NBC)"],
  ["fire", "8 · Fire Safety"],
  ["accessibility", "9 · Accessibility"],
  ["library", "10 · IS Code Library"],
  ["green", "11 · Green Rating"],
  ["grid", "12 · Column Grid"],
];

const INPUTS = {
  loads: [
    ["slab_thickness_mm", "Slab thickness", "mm", 5],
    ["wall_thickness_mm", "Wall thickness", "mm", 5],
    ["finishes_load_kn_sqm", "Finishes load", "kN/m²", 0.1],
    ["grid_bay_x_m", "Grid bay X", "m", 0.5],
    ["grid_bay_y_m", "Grid bay Y", "m", 0.5],
    ["beam_span_m", "Beam span", "m", 0.5],
  ],
  mix: [["concrete_volume_cum", "Concrete volume for BOQ", "m³", 1]],
  water: [["sump_depth_m", "Sump depth", "m", 0.1], ["oht_tanks", "OH tanks", "nos", 1]],
  storm: [["roof_area_sqm", "Roof catchment area", "m²", 10], ["rain_intensity_override", "Rainfall intensity override", "mm/hr", 5]],
  parking_nbc: [
    ["basement_headroom_m", "Basement headroom", "m", 0.1],
    ["aisle_width_m", "Aisle width", "m", 0.1],
    ["two_wheeler_provided", "Two-wheeler spaces provided", "nos", 5],
  ],
  fire: [["refuge_floors_provided", "Refuge areas provided", "nos", 1]],
  accessibility: [
    ["pedestrian_ramp_slope", "Pedestrian ramp slope", "%", 0.1],
    ["door_width_mm", "Clear door width", "mm", 10],
  ],
  grid: [["grid_bay_x_m", "Grid bay X", "m", 0.5], ["grid_bay_y_m", "Grid bay Y", "m", 0.5]],
};

const OutputsGrid = ({ module }) => (
  <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3" data-testid={`outputs-${module.id}`}>
    {module.outputs.map((o) => (
      <div key={o.label} className="border border-slate-200 rounded-sm px-3 py-2" data-testid={`output-${module.id}-${o.label.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`}>
        <div className="text-[10px] uppercase tracking-wider text-slate-500">{o.label}</div>
        <div className="font-mono text-base text-slate-900">
          {typeof o.value === "number" ? num(o.value, Number.isInteger(o.value) ? 0 : 2) : o.value}
          {o.unit && <span className="text-[11px] text-slate-400 ml-1">{o.unit}</span>}
        </div>
        {o.note && <div className="text-[11px] text-slate-500 mt-0.5">{o.note}</div>}
        <div className="mt-1">
          <ClauseChip clause={o.clause} />
        </div>
      </div>
    ))}
  </div>
);

const ChecksList = ({ module }) => (
  <ul className="space-y-2" data-testid={`checks-${module.id}`}>
    {(module.checks || []).map((c, i) => (
      <li
        key={i}
        data-testid={`check-${module.id}-${i}`}
        className={`border rounded-sm px-3 py-2 flex items-start gap-2 ${
          c.status === "pass" ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
        }`}
      >
        {c.status === "pass" ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
        ) : (
          <XCircle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-slate-900">{c.label}</div>
          <div className="text-[11px] text-slate-600 font-mono">
            actual {String(c.actual)} · required {String(c.required)}
          </div>
          {c.note && <div className="text-[11px] text-slate-500">{c.note}</div>}
          <div className="mt-1">
            <ClauseChip clause={c.clause} />
          </div>
        </div>
        <span
          className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm ${
            c.status === "pass" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
          }`}
        >
          {c.status}
        </span>
      </li>
    ))}
  </ul>
);

const CodeLibrary = ({ query, setQuery, focusId, clearFocus }) => {
  const [entries, setEntries] = useState([]);
  useEffect(() => {
    const t = setTimeout(() => {
      const qs = focusId ? `id=${encodeURIComponent(focusId)}` : `q=${encodeURIComponent(query)}`;
      api.get(`/iscodes?${qs}`).then(({ data }) => setEntries(data.entries)).catch(() => {});
    }, 200);
    return () => clearTimeout(t);
  }, [query, focusId]);
  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="h-4 w-4 absolute left-2.5 top-2.5 text-slate-400" />
        <Input
          value={query}
          onChange={(e) => { clearFocus?.(); setQuery(e.target.value); }}
          placeholder="Search IS / NBC codes, topics or values…"
          className="pl-9 rounded-sm"
          data-testid="code-library-search"
        />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-44">Code</TableHead>
            <TableHead>Topic</TableHead>
            <TableHead>Key values</TableHead>
            <TableHead className="w-40">Clause</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((e) => (
            <TableRow key={e.id} id={`code-${e.id}`} data-testid={`code-row-${e.id}`}>
              <TableCell className="py-2 font-mono text-xs">{e.code}</TableCell>
              <TableCell className="py-2 text-sm">{e.topic}</TableCell>
              <TableCell className="py-2 text-xs text-slate-600">{e.key_value}</TableCell>
              <TableCell className="py-2 font-mono text-xs">{e.clause}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!entries.length && <p className="text-sm text-slate-500" data-testid="code-library-empty">No entries match “{query}”.</p>}
    </div>
  );
};

export default function EngineeringModule({ project, update, readOnly }) {
  const [eng, setEng] = useState(null);
  const [tab, setTab] = useState("loads");
  const [libQuery, setLibQuery] = useState("");
  const [libFocus, setLibFocus] = useState("");
  const [libOpen, setLibOpen] = useState(false);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    api.get("/cities").then(({ data }) => setMeta(data)).catch(() => {});
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .post("/engineering/analyse", { project })
        .then(({ data }) => setEng(data))
        .catch((e) => toast.error(apiError(e.response?.data?.detail)));
    }, 300);
    return () => clearTimeout(t);
  }, [project]);

  const openLibrary = useCallback((code, libraryId) => {
    setLibQuery(code);
    setLibFocus(libraryId || "");
    setLibOpen(true);
  }, []);

  const setCfg = (k, v) => update((p) => { p.engineering = { ...(p.engineering || {}), [k]: v }; });
  const toggleGreen = (id, v) =>
    update((p) => {
      const g = { ...((p.engineering || {}).green_checklist || {}) };
      g[id] = v;
      p.engineering = { ...(p.engineering || {}), green_checklist: g };
    });

  const cfgv = useMemo(() => eng?.config || {}, [eng]);
  const mod = eng?.modules?.[tab];

  if (!eng) return <p className="text-sm text-slate-500" data-testid="engineering-loading">Computing IS/NBC modules…</p>;

  return (
    <LibraryContext.Provider value={openLibrary}>
      <div className="space-y-4">
        <Section
          title="Shared project data (feeds every module)"
          description="Enter once — city derives seismic zone, wind speed and rainfall; soil derives SBC and φ."
          testid="engineering-shared-section"
        >
          <div className="grid sm:grid-cols-3 lg:grid-cols-4 gap-3">
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">City</div>
              <Select value={cfgv.city} disabled={readOnly} onValueChange={(v) => {
                const c = (meta?.cities || []).find((x) => x.city === v);
                update((p) => {
                  p.engineering = { ...(p.engineering || {}), city: v, state: c?.state || "" };
                });
              }}>
                <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-city-select"><SelectValue /></SelectTrigger>
                <SelectContent className="max-h-72">
                  {(meta?.cities || []).map((c) => (
                    <SelectItem key={c.city} value={c.city}>{c.city} — Zone {c.zone}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Soil type</div>
              <Select value={cfgv.soil_type} disabled={readOnly} onValueChange={(v) => setCfg("soil_type", v)}>
                <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-soil-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(meta?.soils || []).map((s) => (
                    <SelectItem key={s.key} value={s.key}>{s.label} — SBC {s.sbc} kN/m²</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Exposure condition</div>
              <Select value={cfgv.exposure_condition} disabled={readOnly} onValueChange={(v) => setCfg("exposure_condition", v)}>
                <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-exposure-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(meta?.exposures || []).map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Structural system</div>
              <Select value={cfgv.structural_system} disabled={readOnly} onValueChange={(v) => setCfg("structural_system", v)}>
                <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-system-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(meta?.structural_systems || []).map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <NumField label="Occupancy per unit" value={cfgv.occupancy_per_unit} disabled={readOnly}
              onChange={(v) => setCfg("occupancy_per_unit", v)} testid="eng-occupancy-input" />
            <NumField label="Roof area (0 = use footprint)" suffix="m²" value={cfgv.roof_area_sqm} disabled={readOnly}
              onChange={(v) => setCfg("roof_area_sqm", v)} testid="eng-roof-area-input" />
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Concrete grade</div>
              <Select value={String(cfgv.concrete_grade)} disabled={readOnly} onValueChange={(v) => setCfg("concrete_grade", Number(v))}>
                <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-grade-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[20, 25, 30, 35, 40].map((g) => <SelectItem key={g} value={String(g)}>M{g}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Aggregate / cement</div>
              <div className="flex gap-2">
                <Select value={String(cfgv.aggregate_size_mm)} disabled={readOnly} onValueChange={(v) => setCfg("aggregate_size_mm", Number(v))}>
                  <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-agg-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{[10, 20, 40].map((s) => <SelectItem key={s} value={String(s)}>{s} mm</SelectItem>)}</SelectContent>
                </Select>
                <Select value={cfgv.cement_type} disabled={readOnly} onValueChange={(v) => setCfg("cement_type", v)}>
                  <SelectTrigger className="h-9 rounded-sm text-sm" data-testid="eng-cement-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{["OPC 43", "OPC 53", "PPC"].map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-4">
            <Metric label="Seismic zone" value={eng.city_reference.zone} testid="eng-zone-metric" />
            <Metric label="Basic wind speed" value={eng.city_reference.wind_speed} unit="m/s" testid="eng-wind-metric" />
            <Metric label="Annual rainfall" value={eng.city_reference.annual_rainfall_mm} unit="mm" testid="eng-rain-metric" />
            <Metric label="Base shear" value={num(eng.summary.base_shear_kn, 0)} unit="kN" testid="eng-shear-metric" />
            <Metric label="Column size" value={eng.summary.column_size} unit="mm" testid="eng-column-metric" />
          </div>

          {eng.missing_inputs.length > 0 && (
            <div className="mt-3 border border-amber-200 bg-amber-50 rounded-sm px-3 py-2" data-testid="eng-missing-inputs">
              <div className="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" /> Missing inputs ({eng.missing_inputs.length})
              </div>
              <ul className="text-xs text-amber-800 mt-1 list-disc ml-5">
                {eng.missing_inputs.map((m) => <li key={m}>{m}</li>)}
              </ul>
            </div>
          )}
          {eng.warnings.length > 0 && (
            <div className="mt-3 space-y-2" data-testid="eng-warnings">
              {eng.warnings.map((w, i) => (
                <div key={i} className={`border rounded-sm px-3 py-2 text-sm ${
                  w.severity === "critical" ? "bg-red-50 border-red-200 text-red-800" : "bg-amber-50 border-amber-200 text-amber-800"
                }`} data-testid={`eng-warning-${i}`}>
                  <span className="font-semibold">[{w.severity}] {w.module}: </span>{w.text}
                  <div className="mt-1"><ClauseChip clause={w.clause} /></div>
                </div>
              ))}
            </div>
          )}
        </Section>

        <div className="flex gap-1.5 flex-wrap" data-testid="engineering-tabs">
          {TABS.map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              data-testid={`eng-tab-${id}`}
              className={`text-xs px-2.5 py-1.5 border rounded-sm transition-colors ${
                tab === id ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200 hover:border-slate-400"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "library" ? (
          <Section title="IS / NBC Code Reference Library" description="Every calculated value in the app links here"
            testid="eng-panel-library">
            <CodeLibrary query={libQuery} setQuery={setLibQuery} focusId={libFocus} clearFocus={() => setLibFocus("")} />
          </Section>
        ) : (
          mod && (
            <Section
              title={mod.title}
              description={mod.codes.join(" · ")}
              testid={`eng-panel-${mod.id}`}
              actions={
                mod.score !== undefined && (
                  <span className={`text-[11px] font-mono uppercase px-1.5 py-0.5 rounded-sm ${
                    mod.score === 100 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
                  }`} data-testid={`eng-score-${mod.id}`}>
                    {mod.passed}/{mod.total} · {mod.score}%
                  </span>
                )
              }
            >
              {mod.missing?.length > 0 && (
                <div className="mb-3 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-sm px-2 py-1.5"
                  data-testid={`eng-module-missing-${mod.id}`}>
                  Missing for this module: {mod.missing.join(", ")}
                </div>
              )}

              {INPUTS[mod.id] && (
                <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
                  {INPUTS[mod.id].map(([k, label, unit, step]) => (
                    <NumField key={k} label={label} suffix={unit} step={step} value={cfgv[k]} disabled={readOnly}
                      onChange={(v) => setCfg(k, v)} testid={`eng-input-${k}`} />
                  ))}
                </div>
              )}

              {mod.id === "fire" && (
                <div className="flex items-center gap-4 mb-4">
                  <label className="flex items-center gap-2 text-xs">
                    <Switch checked={!!cfgv.stair_pressurisation} disabled={readOnly}
                      onCheckedChange={(v) => setCfg("stair_pressurisation", v)} data-testid="eng-pressurisation-toggle" />
                    Stairwell pressurisation provided
                  </label>
                  <NumField label="Fire lift car width" suffix="m" step={0.1} value={cfgv.fire_lift_car_m?.[0]}
                    disabled={readOnly} testid="eng-firelift-w"
                    onChange={(v) => setCfg("fire_lift_car_m", [v, cfgv.fire_lift_car_m?.[1] || 2.1])} />
                  <NumField label="Fire lift car depth" suffix="m" step={0.1} value={cfgv.fire_lift_car_m?.[1]}
                    disabled={readOnly} testid="eng-firelift-d"
                    onChange={(v) => setCfg("fire_lift_car_m", [cfgv.fire_lift_car_m?.[0] || 1.1, v])} />
                </div>
              )}

              {mod.id === "accessibility" && (
                <div className="flex flex-wrap items-center gap-4 mb-4">
                  <NumField label="Lift car width" suffix="mm" step={10} value={cfgv.lift_car_mm?.[0]} disabled={readOnly}
                    testid="eng-liftcar-w" onChange={(v) => setCfg("lift_car_mm", [v, cfgv.lift_car_mm?.[1] || 1400])} />
                  <NumField label="Lift car depth" suffix="mm" step={10} value={cfgv.lift_car_mm?.[1]} disabled={readOnly}
                    testid="eng-liftcar-d" onChange={(v) => setCfg("lift_car_mm", [cfgv.lift_car_mm?.[0] || 1100, v])} />
                  <label className="flex items-center gap-2 text-xs">
                    <Switch checked={!!cfgv.dual_handrails} disabled={readOnly}
                      onCheckedChange={(v) => setCfg("dual_handrails", v)} data-testid="eng-handrails-toggle" />
                    Dual handrails (760 / 900 mm)
                  </label>
                  <label className="flex items-center gap-2 text-xs">
                    <Switch checked={!!cfgv.tactile_path} disabled={readOnly}
                      onCheckedChange={(v) => setCfg("tactile_path", v)} data-testid="eng-tactile-toggle" />
                    Tactile path entrance → lift
                  </label>
                </div>
              )}

              {mod.outputs?.length > 0 && <OutputsGrid module={mod} />}

              {mod.recommendation && (
                <div className="mt-4 border border-blue-200 bg-blue-50 rounded-sm px-3 py-2" data-testid={`eng-recommendation-${mod.id}`}>
                  <div className="text-[10px] uppercase tracking-wider text-blue-700">{mod.recommendation.label}</div>
                  <div className="text-sm font-medium text-slate-900">{mod.recommendation.value}</div>
                  <div className="mt-1"><ClauseChip clause={mod.recommendation.clause} /></div>
                </div>
              )}

              {mod.checks?.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Code checks</h4>
                  <ChecksList module={mod} />
                </div>
              )}

              {mod.id === "foundation" && (
                <div className="mt-4">
                  <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                    Safe bearing capacity reference (IS 6403)
                  </h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Soil</TableHead>
                        <TableHead className="text-right">SBC (kN/m²)</TableHead>
                        <TableHead className="text-right">φ (°)</TableHead>
                        <TableHead className="text-right">γ (kN/m³)</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mod.sbc_table.map((s) => (
                        <TableRow key={s.soil} className={s.selected ? "bg-blue-50" : ""} data-testid={`sbc-row-${s.soil.replace(/\W/g, "-").toLowerCase()}`}>
                          <TableCell className="py-1.5">{s.soil}{s.selected && " ← selected"}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">{s.sbc}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">{s.phi}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">{s.gamma}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {mod.id === "mix" && (
                <div className="mt-4" data-testid="mix-boq-link">
                  <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                    BOQ material quantities for {mod.boq_link.volume_cum} m³ of concrete
                  </h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Material</TableHead>
                        <TableHead className="text-right">Per m³</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right">Converted</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {mod.boq_link.rows.map((r) => (
                        <TableRow key={r.material} data-testid={`mix-boq-${r.material.split(" ")[0].toLowerCase()}`}>
                          <TableCell className="py-1.5">{r.material}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">{num(r.per_cum, 1)} {r.unit}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">{num(r.total, 1)} {r.unit}</TableCell>
                          <TableCell className="py-1.5 text-right font-mono">
                            {r.bags ? `${num(r.bags, 1)} bags` : r.tonnes ? `${num(r.tonnes, 2)} t` : "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <p className="text-[11px] text-slate-500 mt-2">{mod.boq_link.note}</p>
                </div>
              )}

              {mod.id === "fire" && (
                <div className="mt-4">
                  <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Per-floor checklist</h4>
                  <div className="max-h-72 overflow-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Floor</TableHead>
                          <TableHead className="text-right">Level</TableHead>
                          <TableHead>Travel ≤ 22.5 m</TableHead>
                          <TableHead className="text-right">Extinguishers</TableHead>
                          <TableHead>Refuge</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {mod.floor_rows.map((r) => (
                          <TableRow key={r.floor} data-testid={`fire-floor-${r.floor}`}>
                            <TableCell className="py-1.5 font-mono">{r.floor}</TableCell>
                            <TableCell className="py-1.5 text-right font-mono">{num(r.level_m, 1)} m</TableCell>
                            <TableCell className="py-1.5">{r.travel_ok ? "pass" : "fail"}</TableCell>
                            <TableCell className="py-1.5 text-right font-mono">{r.extinguishers}</TableCell>
                            <TableCell className="py-1.5">{r.refuge_required ? "required" : "—"}</TableCell>
                            <TableCell className="py-1.5">
                              <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm ${
                                r.status === "pass" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"
                              }`}>{r.status}</span>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {mod.id === "green" && (
                <div className="mt-4 space-y-4">
                  <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
                    {mod.categories.map((c) => (
                      <div key={c.category} className="border border-slate-200 rounded-sm px-3 py-2"
                        data-testid={`green-cat-${c.category.split(" ")[0].toLowerCase()}`}>
                        <div className="text-[10px] uppercase tracking-wider text-slate-500">{c.category}</div>
                        <div className="font-mono text-sm">{c.earned}/{c.total}</div>
                        <Progress value={c.pct} className="h-1.5 mt-1" />
                      </div>
                    ))}
                  </div>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {mod.items.map((i) => (
                      <label key={i.id} className="flex items-start gap-2 border border-slate-200 rounded-sm px-3 py-2 text-sm"
                        data-testid={`green-item-${i.id}`}>
                        <Switch checked={i.checked} disabled={readOnly || i.auto_credited}
                          onCheckedChange={(v) => toggleGreen(i.id, v)} />
                        <span className="flex-1">
                          {i.label}
                          <span className="text-[11px] text-slate-500 block">
                            {i.category} · {i.points} pts{i.auto_credited ? " · auto-credited from Water/Storm modules" : ""}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {mod.id === "grid" && (
                <div className="mt-4 space-y-4">
                  <div>
                    <h4 className="text-xs uppercase tracking-wide text-slate-500 mb-2">Grid options</h4>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Bay</TableHead>
                          <TableHead>Bays</TableHead>
                          <TableHead className="text-right">Columns</TableHead>
                          <TableHead className="text-right">Plot use</TableHead>
                          <TableHead className="text-right">Beam depth</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {mod.options.map((o) => (
                          <TableRow key={o.bay} className={o.selected ? "bg-blue-50" : ""}
                            data-testid={`grid-option-${o.bay.replace(/[^0-9x]/gi, "")}`}>
                            <TableCell className="py-1.5">{o.bay}{o.selected && " ← current"}</TableCell>
                            <TableCell className="py-1.5 font-mono">{o.bays}</TableCell>
                            <TableCell className="py-1.5 text-right font-mono">{o.columns}</TableCell>
                            <TableCell className="py-1.5 text-right font-mono">{o.plot_utilisation_pct}%</TableCell>
                            <TableCell className="py-1.5 text-right font-mono">{o.beam_depth_mm} mm</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {mod.clashes.length > 0 && (
                    <div className="border border-red-200 bg-red-50 rounded-sm px-3 py-2" data-testid="grid-clashes">
                      <div className="text-sm font-semibold text-red-800">
                        {mod.clashes.length} column(s) fall inside usable room space
                      </div>
                      <ul className="text-xs text-red-800 mt-1 list-disc ml-5">
                        {mod.clashes.slice(0, 12).map((c, i) => (
                          <li key={i}>Grid node ({c.x}, {c.y}) m sits inside {c.room} ({c.type})</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Section>
          )
        )}

        <Dialog open={libOpen} onOpenChange={setLibOpen}>
          <DialogContent className="bg-white max-w-4xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <BookOpen className="h-4 w-4" /> IS / NBC Code Reference
              </DialogTitle>
              <DialogDescription>Deep-linked from the calculated value you clicked.</DialogDescription>
            </DialogHeader>
            <div className="max-h-[70vh] overflow-auto" data-testid="clause-dialog">
              <CodeLibrary query={libQuery} setQuery={setLibQuery} focusId={libFocus} clearFocus={() => setLibFocus("")} />
            </div>
            <Button variant="outline" className="rounded-sm" data-testid="clause-dialog-open-library"
              onClick={() => { setTab("library"); setLibOpen(false); }}>
              Open full library tab
            </Button>
          </DialogContent>
        </Dialog>
      </div>
    </LibraryContext.Provider>
  );
}
