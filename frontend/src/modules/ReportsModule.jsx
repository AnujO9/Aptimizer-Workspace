import { toast } from "sonner";
import { Download, FileSpreadsheet } from "lucide-react";
import { downloadFile } from "../lib/api";
import { Section } from "../components/Field";
import { AiPanel } from "../components/AiPanel";
import { Button } from "../components/ui/button";
import { int, money, num } from "../lib/format";

// The reports page mirrors the workspace menu: same group order, same group labels, so a
// reader looking for "the parking numbers" goes to the group they already navigate by.
//
// Three things the menu has that no longer have a document of their own -- Plot &
// Setbacks, Apartment Planning, Parking -- were merged into other reports rather than kept
// as thin duplicates. Each group says where its numbers went instead of showing an empty
// heading, because an unexplained gap reads as something missing.
const REPORT_GROUPS = [
  ["site", "Site", [
    ["site", "Site Analysis", "Terrain, flood risk, access, sun path, suitability and solar potential"],
  ], "Plot geometry and setbacks are checked in the Compliance report."],

  ["design", "Design", [],
   "Apartment planning and parking are in the Executive Summary — neither filled a report on its own."],

  ["eng", "Engineering", [
    ["engineering", "IS / NBC Engineering Summary", "Seismic, foundation, mix, water, fire, accessibility, carbon and plantation"],
    ["structural", "Structural Design Basis", "IS 875 loads, IS 1893 base shear, foundation, mix design, column grid"],
    ["water", "Water & Sanitation", "IS 1172 demand, sump and OHT, STP, storm drainage, RWH and plant rooms"],
    ["fire", "Fire & Life Safety", "NBC Part 4 clause-by-clause checks with a per-floor checklist"],
    ["sustainability", "Sustainability & Carbon", "Green rating, embodied carbon by material, plantation plan and rooftop solar"],
  ], ""],

  ["commercial", "Cost & Programme", [
    ["boq", "BOQ & Quantities", "Material, labour and equipment schedules with the quantities behind them"],
    ["cost", "Cost & Feasibility", "Cost heads, revenue, margin, ROI, IRR, payback, cash flow and optimiser findings"],
    ["programme", "Construction Programme", "Phase table, critical path, floor cycle and the IS 456 safety basis"],
  ], ""],

  ["deliver", "Deliver", [
    ["compliance", "Compliance Validation", "Rule-by-rule pass/fail, including accessibility and development controls"],
    ["executive", "Executive Summary", "The roll-up of everything above: scale, cost, compliance, parking and site"],
  ], ""],
];

const REPORTS = REPORT_GROUPS.flatMap(([, , items]) => items);

export default function ReportsModule({ project, analysis, projectId, readOnly, setProject }) {
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

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <p className="text-[11px] text-slate-500 max-w-xl">
          Eleven reports, grouped as in the menu.
        </p>
        <Button
          className="rounded-sm"
          data-testid="download-all-reports"
          onClick={() => dl(`/projects/${projectId}/reports/all`,
            `${project.name.replace(/\s+/g, "_")}_all_reports.pdf`)}>
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Download all as one PDF
        </Button>
      </div>

      {REPORT_GROUPS.map(([gid, label, items, note]) => (
        <div key={gid} className="space-y-2" data-testid={`report-group-${gid}`}>
          <h3 className="text-[11px] uppercase tracking-wider text-slate-500">{label}</h3>
          {note && <p className="text-[11px] text-slate-500">{note}</p>}
          {items.length > 0 && (
            <div className="grid gap-px bg-slate-200 border border-slate-200 md:grid-cols-2">
              {items.map(([key, title, desc]) => (
                <div key={key} className="bg-white p-4 flex items-start justify-between gap-4"
                  data-testid={`report-card-${key}`}>
                  <div>
                    <h4 className="text-sm font-semibold tracking-tight">{title}</h4>
                    <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                  </div>
                  <Button size="sm" variant="outline" className="rounded-sm text-xs shrink-0"
                    data-testid={`download-${key}-report`}
                    onClick={() => dl(`/projects/${projectId}/reports/${key}`,
                      `${project.name.replace(/\s+/g, "_")}_${key}.pdf`)}>
                    <Download className="h-3.5 w-3.5 mr-1.5" /> PDF
                  </Button>
                </div>
              ))}
              {/* The workbook belongs beside the BOQ report it duplicates in Excel form. */}
              {gid === "commercial" && (
                <div className="bg-white p-4 flex items-start justify-between gap-4"
                  data-testid="report-card-boq-excel">
                  <div>
                    <h4 className="text-sm font-semibold tracking-tight">BOQ Workbook</h4>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Excel with Materials, Labour, Equipment and Summary sheets
                    </p>
                  </div>
                  <Button size="sm" variant="outline" className="rounded-sm text-xs shrink-0"
                    data-testid="download-boq-excel"
                    onClick={() => dl(`/projects/${projectId}/boq.xlsx`,
                      `${project.name.replace(/\s+/g, "_")}_BOQ.xlsx`)}>
                    <FileSpreadsheet className="h-3.5 w-3.5 mr-1.5" /> Excel
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      <AiPanel
        title="AI executive summary"
        description="A client-facing narrative of scale, cost, compliance and the open decisions, written from the figures above"
        endpoint={`/projects/${projectId}/ai/report`}
        initial={project?.ai?.report}
        onGenerated={(d) => setProject?.((p) => ({ ...p, ai: { ...(p.ai || {}), report: d } }))}
        readOnly={readOnly}
        testid="ai-report"
        emptyHint="Draft a plain-language summary for the client, covering what this project is, what it costs and what still needs a decision."
      />
    </div>
  );
}
