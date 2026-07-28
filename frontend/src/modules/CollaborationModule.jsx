import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { History, RotateCcw, Save, Trash2, UserPlus } from "lucide-react";
import { api, apiError } from "@/lib/api";
import { Section } from "@/components/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { dt } from "@/lib/format";

export default function CollaborationModule({ projectId, setProject, readOnly }) {
  const [versions, setVersions] = useState([]);
  const [shares, setShares] = useState([]);
  const [activity, setActivity] = useState([]);
  const [label, setLabel] = useState("");
  const [shareEmail, setShareEmail] = useState("");
  const [shareRole, setShareRole] = useState("viewer");

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
