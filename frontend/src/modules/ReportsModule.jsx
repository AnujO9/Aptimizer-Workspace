import { toast } from "sonner";
import { Download, FileSpreadsheet } from "lucide-react";
import { downloadFile } from "@/lib/api";
import { Section } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { int, money, num } from "@/lib/format";

const REPORTS = [
  ["executive", "Executive Summary", "One-page overview across every module"],
  ["engineering", "IS / NBC Engineering Summary", "Seismic, foundation, mix, water, fire, accessibility and green rating"],
  ["structural", "Structural Design Basis", "IS 875 loads, IS 1893 base shear, foundation, mix design, column grid"],
  ["water", "Water & Sanitation Infrastructure", "IS 1172 demand, sump/OHT, STP, storm drainage and RWH"],
  ["fire", "Fire & Life Safety", "NBC Part 4 clause-by-clause checks with a per-floor checklist"],
  ["accessibility", "Accessibility Compliance", "NBC Part 3 / RPwD checks with parking accessibility"],
  ["boq", "BOQ Report", "Material, labour and equipment schedules"],
  ["cost", "Cost Report", "Cost heads, cost per flat and per m²"],
  ["quantity", "Quantity Report", "Thumb-rule ratios and computed quantities"],
  ["parking", "Parking Report", "Required vs provided, allocation and ramp checks"],
  ["compliance", "Compliance Report", "Rule-by-rule pass/fail with violations"],
  ["utilities", "Utility Report", "Water, tanks, STP/WTP, RWH and plant rooms"],
];

export default function ReportsModule({ project, analysis, projectId }) {
  const a = analysis;
  const dl = async (path, name) => {
    try {
      await downloadFile(path, name);
      toast.success(`${name} downloaded`);
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div className="space-y-4">
      <Section title="Executive snapshot" description="Values embedded in every generated report" testid="report-snapshot">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-slate-200 border border-slate-200">
          {[
            ["Plot area", `${num(a?.areas.plot_area_sqm, 0)} m²`],
            ["Built-up area", `${num(a?.areas.builtup_area_sqm, 0)} m²`],
            ["Units", int(a?.areas.total_units)],
            ["FAR / FSI", `${num(a?.areas.far, 2)} / ${num(a?.areas.fsi, 2)}`],
            ["Parking req/prov", `${int(a?.parking.required_slots)} / ${int(a?.parking.provided_slots)}`],
            ["Total cost", money(a?.cost.total, a?.cost.currency)],
            ["Cost / flat", money(a?.cost.per_unit, a?.cost.currency)],
            ["Compliance", `${a?.compliance.passed}/${a?.compliance.total}`],
          ].map(([k, v]) => (
            <div key={k} className="bg-white px-3 py-2">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
              <div className="font-mono text-sm">{v}</div>
            </div>
          ))}
        </div>
      </Section>

      <div className="grid gap-px bg-slate-200 border border-slate-200 md:grid-cols-2">
        {REPORTS.map(([key, title, desc]) => (
          <div key={key} className="bg-white p-4 flex items-start justify-between gap-4" data-testid={`report-card-${key}`}>
            <div>
              <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
              <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
            </div>
            <Button size="sm" variant="outline" className="rounded-sm text-xs shrink-0" data-testid={`download-${key}-report`}
              onClick={() => dl(`/projects/${projectId}/reports/${key}`, `${project.name.replace(/\s+/g, "_")}_${key}.pdf`)}>
              <Download className="h-3.5 w-3.5 mr-1.5" /> PDF
            </Button>
          </div>
        ))}
        <div className="bg-white p-4 flex items-start justify-between gap-4" data-testid="report-card-boq-excel">
          <div>
            <h3 className="text-sm font-semibold tracking-tight">BOQ Workbook</h3>
            <p className="text-xs text-slate-500 mt-0.5">Excel with Materials, Labour, Equipment and Summary sheets</p>
          </div>
          <Button size="sm" variant="outline" className="rounded-sm text-xs shrink-0" data-testid="download-boq-excel"
            onClick={() => dl(`/projects/${projectId}/boq.xlsx`, `${project.name.replace(/\s+/g, "_")}_BOQ.xlsx`)}>
            <FileSpreadsheet className="h-3.5 w-3.5 mr-1.5" /> Excel
          </Button>
        </div>
      </div>
    </div>
  );
}
