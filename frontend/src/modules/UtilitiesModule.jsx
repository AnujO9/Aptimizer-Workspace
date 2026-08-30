import { Metric, NumField, Section } from "../components/Field";
import OptimiserPanel from "../components/OptimiserPanel";
import { int, num } from "../lib/format";

export default function UtilitiesModule({ project, analysis, update, readOnly, projectId }) {
  const u = analysis?.utilities;
  const cfg = project.utility_config || {};
  const set = (k, v) => update((p) => { p.utility_config[k] = v; });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Metric label="Population" value={int(u?.persons)} testid="util-persons" />
        <Metric label="Water demand" value={num(u?.water_demand_lpd, 0)} unit="L/day" testid="util-demand" />
        <Metric label="Domestic" value={num(u?.domestic_lpd, 0)} unit="L/day" testid="util-domestic" />
        <Metric label="Flushing" value={num(u?.flushing_lpd, 0)} unit="L/day" testid="util-flushing" />
      </div>

      <Section title="Design standards" description="Per-capita and site assumptions" testid="utility-config-section">
        <div className="grid sm:grid-cols-4 gap-3">
          <NumField label="Water supply" suffix="lpcd" value={cfg.lpcd} disabled={readOnly} onChange={(v) => set("lpcd", v)} testid="util-lpcd-input" />
          <NumField label="UG tank storage" suffix="days" step={0.1} value={cfg.ug_tank_days} disabled={readOnly} onChange={(v) => set("ug_tank_days", v)} testid="util-ug-days-input" />
          <NumField label="OH tank storage" suffix="hours" value={cfg.oh_tank_hours} disabled={readOnly} onChange={(v) => set("oh_tank_hours", v)} testid="util-oh-hours-input" />
          <NumField label="Sewage generation" suffix="factor" step={0.05} value={cfg.sewage_factor} disabled={readOnly} onChange={(v) => set("sewage_factor", v)} testid="util-sewage-input" />
          <NumField label="WTP capacity" suffix="factor" step={0.05} value={cfg.wtp_factor} disabled={readOnly} onChange={(v) => set("wtp_factor", v)} testid="util-wtp-input" />
          <NumField label="Annual rainfall" suffix="mm" value={cfg.annual_rainfall_mm} disabled={readOnly} onChange={(v) => set("annual_rainfall_mm", v)} testid="util-rainfall-input" />
          <NumField label="Runoff coefficient" step={0.05} value={cfg.runoff_coefficient} disabled={readOnly} onChange={(v) => set("runoff_coefficient", v)} testid="util-runoff-input" />
          <NumField label="Connected load" suffix="kW/unit" step={0.5} value={cfg.kw_per_unit} disabled={readOnly} onChange={(v) => set("kw_per_unit", v)} testid="util-kw-input" />
        </div>
      </Section>

      <Section title="Sizing output" testid="utility-output-section">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Metric label="Underground tank" value={num(u?.ug_tank_cum, 2)} unit="m³" testid="util-ug-tank" />
          <Metric label="Overhead tank" value={num(u?.oh_tank_cum, 2)} unit="m³" testid="util-oh-tank" />
          <Metric label="STP capacity" value={num(u?.stp_capacity_kld, 2)} unit="KLD" testid="util-stp" />
          <Metric label="WTP capacity" value={num(u?.wtp_capacity_kld, 2)} unit="KLD" testid="util-wtp" />
          <Metric label="Rainwater harvest" value={num(u?.rwh_annual_litres, 0)} unit="L/yr" testid="util-rwh" />
          <Metric label="RWH storage tank" value={num(u?.rwh_storage_cum, 2)} unit="m³" testid="util-rwh-storage" />
          <Metric label="Electrical room" value={num(u?.electrical_room_sqm, 1)} unit="m²" testid="util-electrical-room" />
          <Metric label="Pump room" value={num(u?.pump_room_sqm, 1)} unit="m²" testid="util-pump-room" />
        </div>
        <p className="text-[11px] text-slate-500 mt-3">
          Connected load {num(u?.connected_load_kw, 1)} kW. Electrical and pump rooms are sized from connected load and
          unit count; place them adjacent to the road-access edge defined in Plot & Site.
        </p>
      </Section>
      <OptimiserPanel projectId={projectId} only="utilities" readOnly={readOnly} />

    </div>
  );
}
