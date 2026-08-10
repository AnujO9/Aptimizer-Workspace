import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2, Ruler, XCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { dt, int, num } from "@/lib/format";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicCompliance() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${API}/public/compliance/${token}`)
      .then(({ data }) => setData(data))
      .catch((e) => setError(e.response?.data?.detail || "Unable to load this link"));
  }, [token]);

  if (error)
    return (
      <div className="min-h-screen grid place-items-center px-6" data-testid="public-compliance-error">
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight">Link unavailable</h1>
          <p className="text-sm text-slate-500 mt-2">{error}</p>
        </div>
      </div>
    );
  if (!data)
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500" data-testid="public-compliance-loading">
        Loading compliance summary…
      </div>
    );

  const { project, metrics, compliance } = data;
  const ok = compliance.score >= 100;

  return (
    <div className="min-h-screen py-10 px-4" data-testid="public-compliance-page">
      <main className="max-w-4xl mx-auto space-y-6">
        <header className="border border-slate-200 bg-white rounded-sm p-6">
          <div className="flex items-center gap-2 text-blue-600 text-xs font-mono uppercase tracking-widest">
            <Ruler className="h-3.5 w-3.5" /> Aptimizer · read-only compliance sheet
          </div>
          <h1 className="text-3xl font-semibold tracking-tight mt-2" data-testid="public-project-name">{project.name}</h1>
          <p className="text-sm text-slate-500 mt-1">
            {project.client || "—"} · {project.location || "—"} · {project.plot_reference || "—"} · updated {dt(project.updated_at)}
          </p>
        </header>

        <section className="grid grid-cols-2 md:grid-cols-4 gap-px bg-slate-200 border border-slate-200"
          data-testid="public-metrics">
          {[
            ["FAR", num(metrics.far, 3)],
            ["FSI", num(metrics.fsi, 3)],
            ["Plot area m²", num(metrics.plot_area_sqm, 0)],
            ["Built-up m²", num(metrics.builtup_area_sqm, 0)],
            ["Ground coverage %", num(metrics.ground_coverage_pct, 2)],
            ["Open space %", num(metrics.open_space_pct, 2)],
            ["Units", int(metrics.total_units)],
            ["Max height m", num(metrics.max_height_m, 1)],
          ].map(([k, v]) => (
            <div key={k} className="bg-white px-4 py-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
              <div className="font-mono text-lg text-slate-900">{v}</div>
            </div>
          ))}
        </section>

        <section className="border border-slate-200 bg-white rounded-sm p-6">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="text-lg font-semibold tracking-tight">Compliance checks</h2>
            <span
              data-testid="public-compliance-score"
              className={`text-xs font-mono uppercase px-2 py-1 rounded-sm ${
                ok ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
              }`}
            >
              {compliance.passed}/{compliance.total} passed · {compliance.score}%
            </span>
          </div>
          <div className="mt-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Code</TableHead>
                  <TableHead>Rule</TableHead>
                  <TableHead className="text-right">Limit</TableHead>
                  <TableHead className="text-right">Actual</TableHead>
                  <TableHead className="w-24">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {compliance.results.map((r) => (
                  <TableRow key={r.code + r.label} data-testid={`public-rule-${r.code}`}>
                    <TableCell className="py-2 font-mono text-xs">{r.code}</TableCell>
                    <TableCell className="py-2 text-sm">{r.label}</TableCell>
                    <TableCell className="py-2 text-right font-mono text-xs">
                      {r.operator === "max" ? "max" : "min"} {r.threshold}
                      {r.unit}
                    </TableCell>
                    <TableCell className="py-2 text-right font-mono text-xs">{num(r.actual, 2)}</TableCell>
                    <TableCell className="py-2">
                      <span className={`inline-flex items-center gap-1 text-[11px] font-mono uppercase ${
                        r.status === "pass" ? "text-emerald-700" : "text-red-700"
                      }`}>
                        {r.status === "pass" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                        {r.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>

        <p className="text-xs text-slate-500">
          Read-only summary shared by the project owner. Figures are planning estimates and carry no statutory approval.
        </p>
      </main>
    </div>
  );
}
