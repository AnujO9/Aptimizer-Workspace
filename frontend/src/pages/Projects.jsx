import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Building2, Plus, Trash2, Users } from "lucide-react";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { TopBar } from "@/components/TopBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { dt, int, money, num } from "@/lib/format";

export default function Projects() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", client: "", location: "", plot_reference: "" });

  const load = async () => {
    try {
      const { data } = await api.get("/projects");
      setProjects(data);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!form.name.trim()) return toast.error("Project name is required");
    setBusy(true);
    try {
      const { data } = await api.post("/projects", form);
      toast.success("Project created");
      setOpen(false);
      navigate(`/projects/${data.id}`);
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/projects/${id}`);
      toast.success("Project deleted");
      load();
    } catch (e) {
      toast.error(apiError(e.response?.data?.detail));
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <TopBar />
      <main className="max-w-7xl mx-auto p-6 space-y-6" data-testid="projects-page">
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">Projects</h1>
            <p className="text-sm text-slate-500 mt-1">
              {projects.length} project{projects.length === 1 ? "" : "s"} · signed in as{" "}
              <span className="font-mono">{user?.email}</span>
            </p>
          </div>
          {user?.role !== "viewer" && (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button className="rounded-sm" data-testid="new-project-button">
                  <Plus className="h-4 w-4 mr-1.5" /> New project
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-white">
                <DialogHeader>
                  <DialogTitle>New project</DialogTitle>
                  <DialogDescription>Metadata for the project. Plot, towers and rates can be edited after creation.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  {[
                    ["name", "Project name", "Green Meadows Phase 1"],
                    ["client", "Client", "Meadow Developers Pvt Ltd"],
                    ["location", "Location", "Whitefield, Bengaluru"],
                    ["plot_reference", "Plot reference", "Survey No. 42/1B"],
                  ].map(([k, label, ph]) => (
                    <div key={k} className="space-y-1.5">
                      <Label className="text-xs uppercase tracking-wide text-slate-500">{label}</Label>
                      <Input
                        className="rounded-sm"
                        placeholder={ph}
                        data-testid={`project-${k}-input`}
                        value={form[k]}
                        onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
                <DialogFooter>
                  <Button onClick={create} disabled={busy} className="rounded-sm" data-testid="create-project-submit">
                    {busy ? "Creating…" : "Create project"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {projects.length === 0 ? (
          <div className="border border-slate-200 bg-white rounded-sm overflow-hidden grid md:grid-cols-2" data-testid="projects-empty">
            <div className="p-10">
              <h2 className="text-lg font-semibold tracking-tight">No projects yet</h2>
              <p className="text-sm text-slate-500 mt-2 max-w-sm">
                Create your first project to draw a plot, plan towers and generate area statements, BOQ, cost and
                compliance reports.
              </p>
            </div>
            <img
              src="https://images.pexels.com/photos/18153132/pexels-photo-18153132.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
              alt="Apartment building"
              className="h-56 md:h-full w-full object-cover"
            />
          </div>
        ) : (
          <div className="grid gap-px bg-slate-200 border border-slate-200 md:grid-cols-2 xl:grid-cols-3" data-testid="projects-grid">
            {projects.map((p) => (
              <article
                key={p.id}
                className="bg-white p-4 hover:bg-slate-50 transition-colors cursor-pointer"
                onClick={() => navigate(`/projects/${p.id}`)}
                data-testid={`project-card-${p.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="font-semibold tracking-tight truncate">{p.name}</h3>
                    <p className="text-xs text-slate-500 truncate">
                      {p.client || "No client"} · {p.location || "No location"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {p.shared && (
                      <span className="text-[10px] font-mono uppercase bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded-sm flex items-center gap-1">
                        <Users className="h-3 w-3" /> shared
                      </span>
                    )}
                    <span className="text-[10px] font-mono uppercase bg-slate-100 px-1.5 py-0.5 rounded-sm">{p.status}</span>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-px bg-slate-200 border border-slate-200">
                  {[
                    ["Plot m²", num(p.summary.plot_area_sqm, 0)],
                    ["Built-up m²", num(p.summary.builtup_area_sqm, 0)],
                    ["Units", int(p.summary.total_units)],
                    ["FAR", num(p.summary.far, 2)],
                    ["Cost", money(p.summary.cost_total)],
                    ["Compliance", `${p.summary.compliance_score}%`],
                  ].map(([k, v]) => (
                    <div key={k} className="bg-white px-2 py-1.5">
                      <div className="text-[9px] uppercase tracking-wider text-slate-500">{k}</div>
                      <div className="font-mono text-sm">{v}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                  <span className="flex items-center gap-1">
                    <Building2 className="h-3 w-3" /> {p.summary.towers} tower(s) · edited {dt(p.updated_at)}
                  </span>
                  {!p.shared && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-1.5 text-red-600 hover:text-red-700"
                      data-testid={`delete-project-${p.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        remove(p.id);
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
