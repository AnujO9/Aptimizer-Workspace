import { int, money, num } from "@/lib/format";

const Item = ({ label, value, unit, testid, tone }) => (
  <div className="px-4 py-2 border-r border-slate-200 last:border-r-0 min-w-[124px]" data-testid={testid}>
    <div className="text-[10px] uppercase tracking-wider text-slate-500 whitespace-nowrap">{label}</div>
    <div
      className={`font-mono text-base leading-tight transition-colors ${
        tone === "danger" ? "text-red-600" : tone === "success" ? "text-emerald-600" : "text-slate-900"
      }`}
    >
      {value}
      {unit && <span className="text-[10px] text-slate-400 ml-0.5">{unit}</span>}
    </div>
  </div>
);

export const MetricsStrip = ({ analysis }) => {
  if (!analysis) return <div className="h-14 border-b border-slate-200 bg-white" />;
  const a = analysis.areas;
  const c = analysis.compliance;
  return (
    <div
      className="flex overflow-x-auto border-b border-slate-200 bg-white sticky top-0 z-20"
      data-testid="metrics-strip"
    >
      <Item label="Plot Area" value={num(a.plot_area_sqm, 0)} unit="m²" testid="metric-plot-area" />
      <Item label="Carpet" value={num(a.carpet_area_sqm, 0)} unit="m²" testid="metric-carpet" />
      <Item label="Built-up" value={num(a.builtup_area_sqm, 0)} unit="m²" testid="metric-builtup" />
      <Item label="Super B-up" value={num(a.super_builtup_area_sqm, 0)} unit="m²" testid="metric-super-builtup" />
      <Item label="Gr. Coverage" value={num(a.ground_coverage_pct, 1)} unit="%" testid="metric-coverage" />
      <Item label="FAR" value={num(a.far, 2)} testid="metric-far" />
      <Item label="FSI" value={num(a.fsi, 2)} testid="metric-fsi" />
      <Item label="Open Space" value={num(a.open_space_pct, 1)} unit="%" testid="metric-open-space" />
      <Item label="Units" value={int(a.total_units)} testid="metric-units" />
      <Item label="Density" value={num(a.density_units_per_acre, 1)} unit="/acre" testid="metric-density" />
      <Item label="Cost" value={money(analysis.cost.total, analysis.cost.currency)} testid="metric-cost" />
      <Item
        label="Compliance"
        value={`${c.passed}/${c.total}`}
        tone={c.overall === "pass" ? "success" : "danger"}
        testid="metric-compliance"
      />
    </div>
  );
};
