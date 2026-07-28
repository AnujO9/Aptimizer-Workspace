import { Metric, NumField, Section } from "@/components/Field";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { int, num } from "@/lib/format";

export default function CalculationsModule({ project, analysis, update, readOnly }) {
  const a = analysis?.areas;
  const cfg = project.config || {};
  const setCfg = (k, v) => update((p) => { p.config[k] = v; });

  return (
    <div className="space-y-4">
      <Section title="Area statement" description="Live from plot geometry and apartment planning" testid="area-statement-section">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Metric label="Plot area" value={num(a?.plot_area_sqm, 2)} unit="m²" testid="calc-plot-area" />
          <Metric label="Plot area" value={num(a?.plot_area_acres, 4)} unit="acres" testid="calc-plot-acres" />
          <Metric label="Carpet area" value={num(a?.carpet_area_sqm, 2)} unit="m²" testid="calc-carpet" />
          <Metric label="Built-up area" value={num(a?.builtup_area_sqm, 2)} unit="m²" testid="calc-builtup" />
          <Metric label="Super built-up" value={num(a?.super_builtup_area_sqm, 2)} unit="m²" testid="calc-super-builtup" />
          <Metric label="Ground footprint" value={num(a?.ground_footprint_sqm, 2)} unit="m²" testid="calc-footprint" />
          <Metric label="Ground coverage" value={num(a?.ground_coverage_pct, 2)} unit="%" testid="calc-coverage" />
          <Metric label="Open space" value={`${num(a?.open_space_sqm, 0)} (${num(a?.open_space_pct, 1)}%)`} unit="m²" testid="calc-open-space" />
          <Metric label="FAR" value={num(a?.far, 3)} testid="calc-far" />
          <Metric label="FSI" value={num(a?.fsi, 3)} testid="calc-fsi" />
          <Metric label="Units" value={int(a?.total_units)} testid="calc-units" />
          <Metric label="Occupants" value={int(a?.occupants)} testid="calc-occupants" />
          <Metric label="Density" value={num(a?.density_units_per_acre, 2)} unit="units/acre" testid="calc-density-acre" />
          <Metric label="Density" value={num(a?.density_persons_per_hectare, 1)} unit="p/ha" testid="calc-density-ha" />
          <Metric label="Max height" value={num(a?.max_height_m, 2)} unit="m" testid="calc-height" />
          <Metric label="Balcony area" value={num(a?.towers?.reduce((s, t) => s + t.balcony_sqm, 0), 1)} unit="m²" testid="calc-balcony" />
        </div>
      </Section>

      <Section title="Calculation assumptions" description="Configurable per project — all outputs update live" testid="calc-config-section">
        <div className="grid sm:grid-cols-3 gap-3">
          <NumField label="Wall thickness allowance" suffix="ratio" step={0.01} value={cfg.wall_thickness_factor}
            disabled={readOnly} onChange={(v) => setCfg("wall_thickness_factor", v)} testid="config-wall-factor-input" />
          <NumField label="Common area loading (super b-up)" suffix="ratio" step={0.01} value={cfg.common_area_loading}
            disabled={readOnly} onChange={(v) => setCfg("common_area_loading", v)} testid="config-loading-input" />
          <NumField label="FSI factor vs FAR" suffix="×" step={0.05} value={cfg.fsi_factor}
            disabled={readOnly} onChange={(v) => setCfg("fsi_factor", v)} testid="config-fsi-factor-input" />
        </div>
        <p className="text-[11px] text-slate-500 mt-3">
          Built-up = (carpet + balcony) × (1 + wall allowance) + service core. Super built-up = built-up × (1 + loading).
          FSI = FAR × FSI factor (set to 1.0 where the region treats them identically).
        </p>
      </Section>

      <Section title="Per-tower breakdown" testid="tower-breakdown-section">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tower</TableHead>
              <TableHead className="text-right">Floors</TableHead>
              <TableHead className="text-right">Height m</TableHead>
              <TableHead className="text-right">Units</TableHead>
              <TableHead className="text-right">Carpet m²</TableHead>
              <TableHead className="text-right">Built-up m²</TableHead>
              <TableHead className="text-right">Super b-up m²</TableHead>
              <TableHead className="text-right">Footprint m²</TableHead>
              <TableHead className="text-right">Occupants</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(a?.towers || []).map((t) => (
              <TableRow key={t.id} data-testid={`tower-breakdown-${t.id}`}>
                <TableCell className="py-2 font-medium">{t.name}</TableCell>
                <TableCell className="py-2 text-right font-mono">{t.floors}</TableCell>
                <TableCell className="py-2 text-right font-mono">{num(t.height_m, 1)}</TableCell>
                <TableCell className="py-2 text-right font-mono">{t.total_units}</TableCell>
                <TableCell className="py-2 text-right font-mono">{num(t.carpet_sqm, 0)}</TableCell>
                <TableCell className="py-2 text-right font-mono">{num(t.builtup_sqm, 0)}</TableCell>
                <TableCell className="py-2 text-right font-mono">{num(t.super_builtup_sqm, 0)}</TableCell>
                <TableCell className="py-2 text-right font-mono">{num(t.footprint_sqm, 0)}</TableCell>
                <TableCell className="py-2 text-right font-mono">{t.occupants}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>
    </div>
  );
}
