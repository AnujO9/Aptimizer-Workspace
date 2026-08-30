import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { History, RotateCcw, Save, Trash2, UserPlus } from "lucide-react";
import { api, apiError } from "../lib/api";
import { Section } from "../components/Field";
import { AiPanel } from "../components/AiPanel";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { dt, num } from "../lib/format";

/** Scaled plan view of one scheme: plot outline with tower footprints inside it.
 *
 *  Scalar metrics cannot separate four squat towers from two slender ones on the same
 *  FAR, which is exactly the choice a comparison is usually being made to settle. Drawn
 *  to a shared scale so the two plans are directly comparable in size, not just in shape.
 */
function PlanView({ geometry, label, scale }) {
  if (!geometry?.plot?.length_m) {
    return <div className="text-[11px] text-slate-500">No plot geometry recorded.</div>;
  }
  const { length_m: L, width_m: W } = geometry.plot;
  const pad = 8;
  const w = L * scale + pad * 2;
  const h = W * scale + pad * 2;
  return (
    <div className="space-y-1.5">
      <div className="text-[11px] font-medium text-slate-700">{label}</div>
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="border border-slate-200 rounded-sm bg-slate-50"
        role="img" aria-label={`Plan view of ${label}`}>
        <rect x={pad} y={pad} width={L * scale} height={W * scale}
          fill="#FFFFFF" stroke="#94A3B8" strokeWidth="1" />
        {geometry.towers.map((t) => (
          <g key={t.id}>
            <rect x={pad + t.x * scale} y={pad + t.y * scale}
              width={Math.max(t.w * scale, 2)} height={Math.max(t.d * scale, 2)}
              fill="#2563EB" fillOpacity="0.75" stroke="#1D4ED8" strokeWidth="0.75" />
            <title>{`${t.name} — ${t.floors} floors, ${t.height_m} m, ${t.footprint_sqm} m² footprint`}</title>
          </g>
        ))}
      </svg>
      <div className="text-[10px] text-slate-500 leading-snug">
        {num(L, 0)} × {num(W, 0)} m · {geometry.towers.length} tower
        {geometry.towers.length === 1 ? "" : "s"} · {num(geometry.ground_coverage_pct, 1)}% covered
        {geometry.plot.basis !== "recorded plot dimensions" && (
          <> · <span className="text-amber-700">{geometry.plot.basis}</span></>
        )}
        {geometry.placement !== "as positioned" && (
          <> · <span className="text-amber-700">tower positions indicative</span></>
        )}
      </div>
    </div>
  );
}


export default function CollaborationModule({ projectId, setProject, readOnly }) {
  const [versions, setVersions] = useState([]);
  const [shares, setShares] = useState([]);
  const [activity, setActivity] = useState([]);
  const [label, setLabel] = useState("");
  const [shareEmail, setShareEmail] = useState("");
  const [shareRole, setShareRole] = useState("viewer");
  const [schemeA, setSchemeA] = useState("current");
  const [schemeB, setSchemeB] = useState("");
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [v, s, act] = await Promise.all([
        api.get(`/projects/${projectId}/versions`),
        api.get(`/projects/${projectId}/shares`),
        api.get(`/projects/${projectId}/activity`),
      ]);
      setVersions(v.data);
      setShares(s.data);
      setActivity(act.data);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveVersion = async () => {
    if (!label.trim()) return toast.error("Enter a version label");
    try {
      await api.post(`/projects/${projectId}/versions`, { label });
      setLabel("");
      toast.success("Snapshot saved");
      load();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  const restore = async (id) => {
    try {
      const { data } = await api.post(`/projects/${projectId}/versions/${id}/restore`);
      setProject(data);
      toast.success("Project rolled back");
      load();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  const share = async () => {
    try {
      await api.post(`/projects/${projectId}/shares`, { email: shareEmail, role: shareRole });
      setShareEmail("");
      toast.success("Access granted");
      load();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  const unshare = async (id) => {
    try {
      await api.delete(`/projects/${projectId}/shares/${id}`);
      toast.success("Access revoked");
      load();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  const runCompare = async () => {
    if (!schemeA || !schemeB) return toast.error("Pick two schemes to compare");
    if (schemeA === schemeB) return toast.error("Pick two different schemes");
    setComparing(true);
    try {
      const { data } = await api.get(`/projects/${projectId}/versions/compare`, { params: { a: schemeA, b: schemeB } });
      setCompareResult(data);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    } finally {
      setComparing(false);
    }
  };

  const schemeOptions = [{ id: "current", label: "Current project" }, ...versions.map((v) => ({ id: v.id, label: v.label }))];

  return (
    <div className="space-y-4">
      <div className="grid lg:grid-cols-2 gap-4">
        <Section title="Project versions" description="Save named snapshots and roll back" testid="versions-section">
          {!readOnly && (
            <div className="flex gap-2 mb-3">
              <Input placeholder="e.g. Pre-approval scheme B" value={label} onChange={(e) => setLabel(e.target.value)}
                className="rounded-sm" data-testid="version-label-input" />
              <Button onClick={saveVersion} className="rounded-sm shrink-0" data-testid="save-version-button">
                <Save className="h-4 w-4 mr-1.5" /> Save snapshot
              </Button>
            </div>
          )}
          {versions.length === 0 ? (
            <p className="text-sm text-slate-500">No snapshots saved yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Label</TableHead>
                  <TableHead>By</TableHead>
                  <TableHead>At</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((v) => (
                  <TableRow key={v.id} data-testid={`version-row-${v.id}`}>
                    <TableCell className="py-2 font-medium">{v.label}</TableCell>
                    <TableCell className="py-2 text-xs">{v.user_name}</TableCell>
                    <TableCell className="py-2 text-xs font-mono">{dt(v.at)}</TableCell>
                    <TableCell className="py-2">
                      {!readOnly && (
                        <Button size="sm" variant="outline" className="h-7 rounded-sm text-xs"
                          data-testid={`restore-version-${v.id}`} onClick={() => restore(v.id)}>
                          <RotateCcw className="h-3 w-3 mr-1" /> Restore
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Section>

        <Section title="Project team" description="Share with registered users by role" testid="shares-section">
          {!readOnly && (
            <div className="flex gap-2 mb-3">
              <Input placeholder="user@example.com" value={shareEmail} onChange={(e) => setShareEmail(e.target.value)}
                className="rounded-sm" data-testid="share-email-input" />
              <Select value={shareRole} onValueChange={setShareRole}>
                <SelectTrigger className="w-32 rounded-sm" data-testid="share-role-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">Viewer</SelectItem>
                  <SelectItem value="engineer">Engineer</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={share} className="rounded-sm shrink-0" data-testid="share-submit-button">
                <UserPlus className="h-4 w-4" />
              </Button>
            </div>
          )}
          {shares.length === 0 ? (
            <p className="text-sm text-slate-500">Not shared with anyone yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {shares.map((s) => (
                  <TableRow key={s.id} data-testid={`share-row-${s.id}`}>
                    <TableCell className="py-2 font-mono text-xs">{s.email}</TableCell>
                    <TableCell className="py-2 uppercase font-mono text-xs">{s.role}</TableCell>
                    <TableCell className="py-2">
                      {!readOnly && (
                        <Button size="sm" variant="ghost" className="h-7 px-1 text-red-600"
                          data-testid={`unshare-${s.id}`} onClick={() => unshare(s.id)}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Section>
      </div>

      <Section title="Scheme Comparison" description="Compare the current project against any saved version — FAR, unit count, cost per flat and more, side by side" testid="scheme-comparison-section">
        <div className="flex flex-wrap items-end gap-2 mb-4">
          <div className="space-y-1">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Scheme A</div>
            <Select value={schemeA} onValueChange={setSchemeA}>
              <SelectTrigger className="w-56 rounded-sm" data-testid="compare-scheme-a-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {schemeOptions.map((s) => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">Scheme B</div>
            <Select value={schemeB} onValueChange={setSchemeB}>
              <SelectTrigger className="w-56 rounded-sm" data-testid="compare-scheme-b-select"><SelectValue placeholder="Select a version…" /></SelectTrigger>
              <SelectContent>
                {schemeOptions.map((s) => <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={runCompare} disabled={comparing} className="rounded-sm" data-testid="run-compare-button">
            {comparing ? "Comparing…" : "Compare"}
          </Button>
        </div>

        {!compareResult ? (
          <p className="text-sm text-slate-500">
            {versions.length === 0
              ? "Save at least one snapshot above to compare it against the current project."
              : "Pick two schemes and click Compare."}
          </p>
        ) : (
          <>
          {compareResult.schemes[0].geometry && compareResult.schemes[1].geometry && (() => {
            // One scale across both plans, so a bigger plot draws bigger.
            const span = Math.max(
              ...compareResult.schemes.map((s) => Math.max(s.geometry.plot.length_m || 1,
                                                           s.geometry.plot.width_m || 1)));
            const scale = 260 / (span || 1);
            return (
              <div className="grid sm:grid-cols-2 gap-4 mb-4" data-testid="compare-plans">
                {compareResult.schemes.map((s) => (
                  <PlanView key={s.id} geometry={s.geometry} label={s.label} scale={scale} />
                ))}
              </div>
            );
          })()}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">{compareResult.schemes[0].label}</TableHead>
                <TableHead className="text-right">{compareResult.schemes[1].label}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {compareResult.keys.map((k) => {
                const va = compareResult.schemes[0].metrics[k];
                const vb = compareResult.schemes[1].metrics[k];
                return (
                  <TableRow key={k} data-testid={`compare-row-${k.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`}>
                    <TableCell className="py-1.5 text-slate-600">{k}</TableCell>
                    <TableCell className="py-1.5 text-right font-mono">{typeof va === "number" ? num(va, Number.isInteger(va) ? 0 : 2) : va}</TableCell>
                    <TableCell className="py-1.5 text-right font-mono">{typeof vb === "number" ? num(vb, Number.isInteger(vb) ? 0 : 2) : vb}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          </>
        )}

        {compareResult && (
          <div className="mt-4">
            <AiPanel
              title="AI comparison"
              description="Explains what the differences above mean in practice and which scheme is the stronger choice"
              endpoint={`/projects/${projectId}/ai/compare?a=${encodeURIComponent(schemeA)}&b=${encodeURIComponent(schemeB)}`}
              method="get"
              readOnly={readOnly}
              testid="ai-compare"
              buttonLabel="Explain the difference"
              emptyHint="Turn the metric table above into a recommendation, with the trade-offs each scheme is making."
            />
          </div>
        )}
      </Section>

      <Section title="Activity log" description="Who changed what and when" testid="activity-section">
        {activity.length === 0 ? (
          <p className="text-sm text-slate-500">No activity recorded.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {activity.map((a) => (
              <li key={a.id} className="py-2 flex items-start gap-2 text-sm" data-testid={`activity-${a.id}`}>
                <History className="h-4 w-4 text-slate-400 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{a.user_name}</span>{" "}
                  <span className="font-mono text-xs bg-slate-100 px-1 rounded-sm">{a.action}</span>{" "}
                  <span className="text-slate-500">{a.detail}</span>
                </div>
                <span className="text-[11px] font-mono text-slate-400 shrink-0">{dt(a.at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
