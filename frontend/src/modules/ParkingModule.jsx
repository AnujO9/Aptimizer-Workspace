import { Check, X } from "lucide-react";
import { Metric, NumField, Section } from "@/components/Field";
import { int, num } from "@/lib/format";

export default function ParkingModule({ project, analysis, update, readOnly }) {
  const p = project.parking || {};
  const r = analysis?.parking;
  const set = (k, v) => update((x) => { x.parking[k] = v; });
  const setRamp = (k, v) => update((x) => { x.parking.ramp[k] = v; });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Metric label="Required slots" value={int(r?.required_slots)} testid="parking-required" />
        <Metric label="Provided slots" value={int(r?.provided_slots)} testid="parking-provided"
          tone={r && r.provided_slots >= r.required_slots ? "success" : "danger"} />
        <Metric label="Deficit" value={int(r?.deficit)} tone={r?.deficit ? "danger" : "success"} testid="parking-deficit" />
        <Metric label="Area / slot (actual)" value={num(r?.area_per_slot_actual, 2)} unit="m²" testid="parking-area-per-slot" />
        <Metric label="Layout efficiency" value={num(r?.efficiency_pct, 1)} unit="%" testid="parking-efficiency" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Section title="Parking layout & capacity" testid="parking-layout-section">
          <div className="grid sm:grid-cols-2 gap-3">
            <NumField label="Basement levels" value={p.basement_levels} disabled={readOnly} onChange={(v) => set("basement_levels", v)} testid="parking-basement-levels-input" />
            <NumField label="Basement area / level" suffix="m²" value={p.basement_area_per_level} disabled={readOnly} onChange={(v) => set("basement_area_per_level", v)} testid="parking-basement-area-input" />
            <NumField label="Ground-level parking area" suffix="m²" value={p.ground_area} disabled={readOnly} onChange={(v) => set("ground_area", v)} testid="parking-ground-area-input" />
            <NumField label="Area per slot (incl. aisle)" suffix="m²" value={p.area_per_slot} disabled={readOnly} onChange={(v) => set("area_per_slot", v)} testid="parking-area-per-slot-input" />
            <NumField label="Required ratio" suffix="/unit" step={0.1} value={p.ratio_per_unit} disabled={readOnly} onChange={(v) => set("ratio_per_unit", v)} testid="parking-ratio-input" />
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <Metric label="Basement slots" value={int(r?.basement_slots)} testid="parking-basement-slots" />
            <Metric label="Ground slots" value={int(r?.ground_slots)} testid="parking-ground-slots" />
          </div>
        </Section>

        <Section title="Allocation — visitor, EV, accessible" testid="parking-allocation-section">
          <div className="grid grid-cols-3 gap-3">
            <NumField label="Visitor %" suffix="%" value={p.visitor_pct} disabled={readOnly} onChange={(v) => set("visitor_pct", v)} testid="parking-visitor-pct-input" />
            <NumField label="EV %" suffix="%" value={p.ev_pct} disabled={readOnly} onChange={(v) => set("ev_pct", v)} testid="parking-ev-pct-input" />
            <NumField label="Accessible %" suffix="%" value={p.accessible_pct} disabled={readOnly} onChange={(v) => set("accessible_pct", v)} testid="parking-accessible-pct-input" />
            <NumField label="Visitor provided" value={p.visitor_provided} disabled={readOnly} onChange={(v) => set("visitor_provided", v)} testid="parking-visitor-provided-input" />
            <NumField label="EV provided" value={p.ev_provided} disabled={readOnly} onChange={(v) => set("ev_provided", v)} testid="parking-ev-provided-input" />
            <NumField label="Accessible provided" value={p.accessible_provided} disabled={readOnly} onChange={(v) => set("accessible_provided", v)} testid="parking-accessible-provided-input" />
          </div>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <Metric label="Visitor required" value={int(r?.visitor_required)} testid="parking-visitor-required" />
            <Metric label="EV required" value={int(r?.ev_required)} testid="parking-ev-required" />
            <Metric label="Accessible required" value={int(r?.accessible_required)} testid="parking-accessible-required" />
          </div>
        </Section>
      </div>

      <Section title="Ramp planning & validation" testid="ramp-section">
        <div className="grid sm:grid-cols-3 gap-3">
          <NumField label="Slope" suffix="%" step={0.1} value={p.ramp?.slope_pct} disabled={readOnly} onChange={(v) => setRamp("slope_pct", v)} testid="ramp-slope-input" />
          <NumField label="Ramp width" suffix="m" step={0.1} value={p.ramp?.width} disabled={readOnly} onChange={(v) => setRamp("width", v)} testid="ramp-width-input" />
          <NumField label="Turning radius" suffix="m" step={0.1} value={p.ramp?.turning_radius} disabled={readOnly} onChange={(v) => setRamp("turning_radius", v)} testid="ramp-radius-input" />
        </div>
        <ul className="mt-4 space-y-2">
          {(r?.ramp_checks || []).map((c, i) => (
            <li key={i} className={`flex items-center gap-2 text-sm px-3 py-2 rounded-sm border ${
              c.pass ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-800"
            }`} data-testid={`ramp-check-${i}`}>
              {c.pass ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
              <span className="flex-1">{c.label}</span>
              <span className="font-mono text-xs">{c.value}</span>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
