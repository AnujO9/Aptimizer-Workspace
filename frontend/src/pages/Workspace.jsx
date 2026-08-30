import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Map, Building2, Calculator, Car, ClipboardList, Wallet, ShieldCheck, FileText, History, CalendarClock,
  Globe2, Box, Ruler, TrendingUp, Sparkles,
} from "lucide-react";
import { api, apiError } from "../lib/api";
import { TopBar } from "../components/TopBar";
import { MetricsStrip } from "../components/MetricsStrip";
import { CommandPalette } from "../components/CommandPalette";
import AptPanel from "../components/AptPanel";
import { ProjectNav } from "../components/ProjectNav";
import DevControlsModule from "../modules/DevControlsModule";
import PlotModule from "../modules/PlotModule";
import GisModule from "../modules/GisModule";
import ThreeDModule from "../modules/ThreeDModule";
import EngineeringModule from "../modules/EngineeringModule";
import PlanningModule from "../modules/PlanningModule";
import CalculationsModule from "../modules/CalculationsModule";
import ParkingModule from "../modules/ParkingModule";
import BoqModule from "../modules/BoqModule";
import CostModule from "../modules/CostModule";
import ProgrammeModule from "../modules/ProgrammeModule";
import FinanceModule from "../modules/FinanceModule";
import ComplianceModule from "../modules/ComplianceModule";
import ReportsModule from "../modules/ReportsModule";
import CollaborationModule from "../modules/CollaborationModule";

// Grouped by the order a project actually moves: understand the land, design the
// building, verify the engineering, price and programme it, then issue it. Two former
// destinations were folded in rather than grouped -- Quantities is the unpriced half of
// the BOQ, and Utilities computes the same water and storm figures as the engineering
// water modules, which is why the two once disagreed on sump size for one project.
const GROUPS = [
  ["site", "Site", [
    ["plot", "Plot & Site", Map, PlotModule],
    ["controls", "Setbacks & Controls", Ruler, DevControlsModule],
    ["gis", "GIS Intelligence", Globe2, GisModule],
  ]],
  ["design", "Design", [
    ["planning", "Apartment Planning", Building2, PlanningModule],
    ["parking", "Parking", Car, ParkingModule],
    ["3d", "3D Visualisation", Box, ThreeDModule],
  ]],
  ["eng", "Engineering", [
    ["calculations", "Calculations", Calculator, CalculationsModule],
    ["engineering", "IS/NBC Engineering", Ruler, EngineeringModule],
  ]],
  ["commercial", "Cost & Programme", [
    ["boq", "BOQ & Quantities", ClipboardList, BoqModule],
    ["cost", "Cost Estimation", Wallet, CostModule],
    ["programme", "Programme", CalendarClock, ProgrammeModule],
    ["finance", "Feasibility & ROI", TrendingUp, FinanceModule],
  ]],
  ["deliver", "Deliver", [
    ["compliance", "Compliance", ShieldCheck, ComplianceModule],
    ["reports", "Reports", FileText, ReportsModule],
    ["collaboration", "Versions & Team", History, CollaborationModule],
  ]],
];

const MODULES = GROUPS.flatMap(([, , items]) => items);
const GROUP_OF = Object.fromEntries(
  GROUPS.flatMap(([g, , items]) => items.map((m) => [m[0], g])));
const GROUP_LABEL = Object.fromEntries(GROUPS.map(([g, label]) => [g, label]));

const EDITABLE = [
  "name", "client", "location", "plot_reference", "status", "plot", "towers", "parking", "config",
  "quantity_ratios", "rates", "labour_rates", "equipment_rates", "utility_config", "compliance_rules",
  "engineering",
];

export default function Workspace() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [accessRole, setAccessRole] = useState("viewer");
  const [active, setActive] = useState("plot");
  const [saveState, setSaveState] = useState("saved");
  const [duration, setDuration] = useState(null);
  const dirty = useRef(false);

  useEffect(() => {
    api
      .get(`/projects/${projectId}`)
      .then(({ data }) => {
        setAccessRole(data.access_role);
        setProject(data);
      })
      .catch((e) => toast.error(apiError(e.response?.data?.detail)));
  }, [projectId]);

  // live recalculation
  useEffect(() => {
    if (!project) return;
    const t = setTimeout(() => {
      api
        .post("/analyse", { project })
        .then(({ data }) => setAnalysis(data))
        .catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [project]);

  // debounced autosave
  useEffect(() => {
    if (!project || !dirty.current) return;
    setSaveState("saving");
    const t = setTimeout(async () => {
      const updates = {};
      EDITABLE.forEach((k) => {
        if (project[k] !== undefined) updates[k] = project[k];
      });
      try {
        await api.put(`/projects/${projectId}`, { updates });
        dirty.current = false;
        setSaveState("saved");
      } catch (e) {
        setSaveState("error");
        toast.error(apiError(e.response?.data?.detail));
      }
    }, 900);
    return () => clearTimeout(t);
  }, [project, projectId]);

  // Headline build duration for the metrics strip. Uses the summary form of the
  // programme endpoint, which skips float verification and the 120-activity payload --
  // the completion date does not depend on either, and this runs on every recalculation.
  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    const t = setTimeout(() => {
      api.post("/schedule", { project, summary: true, config: {} })
        .then(({ data }) => { if (!cancelled) setDuration(data.ok ? data : null); })
        .catch(() => { if (!cancelled) setDuration(null); });
    }, 600);   // debounce: the project mutates on every keystroke while editing
    return () => { cancelled = true; clearTimeout(t); };
  }, [project]);

  const update = useCallback((mutator) => {
    dirty.current = true;
    setProject((prev) => {
      const copy = structuredClone(prev);
      mutator(copy);
      return copy;
    });
  }, []);

  const readOnly = accessRole === "viewer";
  const Current = useMemo(() => MODULES.find((m) => m[0] === active)?.[3], [active]);

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [aptOpen, setAptOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!project)
    return (
      <div className="min-h-screen bg-slate-50">
        <TopBar />
        <div className="p-10 text-sm text-slate-500" data-testid="workspace-loading">
          Loading project…
        </div>
      </div>
    );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <TopBar>
        <div className="flex items-center gap-3 min-w-0">
          <div className="min-w-0">
            <div className="text-sm font-semibold tracking-tight truncate" data-testid="workspace-project-name">
              {project.name}
            </div>
            <div className="text-[11px] text-slate-500 truncate">
              {project.client || "—"} · {project.location || "—"} · {project.plot_reference || "—"}
            </div>
          </div>
          <span
            className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm ${
              saveState === "saved"
                ? "bg-emerald-50 text-emerald-700"
                : saveState === "saving"
                ? "bg-amber-50 text-amber-700"
                : "bg-red-50 text-red-700"
            }`}
            data-testid="save-indicator"
          >
            {saveState}
          </span>
          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-sm bg-slate-100" data-testid="access-role-badge">
            {accessRole}
          </span>
        </div>
      </TopBar>

      <ProjectNav
        groups={GROUPS}
        active={active}
        onPick={setActive}
        onOpenPalette={() => setPaletteOpen(true)}
      />

      <div className="flex flex-1 min-h-0">
        <aside
          className="w-56 shrink-0 bg-white border-r border-slate-200 hidden md:block"
          data-testid="metrics-panel"
        >
          <MetricsStrip analysis={analysis} duration={duration} vertical />
        </aside>

        <main className="flex-1 min-w-0 p-4 md:p-6 space-y-4" data-testid={`module-panel-${active}`}>
          {Current && (
            <Current
              project={project}
              analysis={analysis}
              update={update}
              readOnly={readOnly}
              projectId={projectId}
              setProject={setProject}
            />
          )}
        </main>
      </div>

      {/* Apt sits on the workspace chrome rather than in a tab: "why is this number what
          it is" gets asked from whichever tab is showing the number. Floating bottom-right
          because that is where an assistant is looked for, and nothing can compress it. */}
      {!aptOpen && (
        <button
          onClick={() => setAptOpen(true)}
          title="Ask Apt about this project"
          data-testid="apt-trigger"
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/25 pl-3.5 pr-4 py-2.5 text-sm font-medium transition-colors"
        >
          <Sparkles className="h-4 w-4" />
          Ask Apt
        </button>
      )}

      <AptPanel open={aptOpen} onOpenChange={setAptOpen} projectId={projectId} module={active} />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        modules={MODULES}
        groupLabel={(key) => GROUP_LABEL[GROUP_OF[key]] || ""}
        onPick={setActive}
        active={active}
      />
    </div>
  );
}
