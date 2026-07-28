import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Map, Building2, Calculator, Car, Package, ClipboardList, Wallet, Droplets, ShieldCheck, FileText, History,
  Globe2, Box,
} from "lucide-react";
import { api, apiError } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { MetricsStrip } from "@/components/MetricsStrip";
import PlotModule from "@/modules/PlotModule";
import GisModule from "@/modules/GisModule";
import ThreeDModule from "@/modules/ThreeDModule";
import PlanningModule from "@/modules/PlanningModule";
import CalculationsModule from "@/modules/CalculationsModule";
import ParkingModule from "@/modules/ParkingModule";
import QuantitiesModule from "@/modules/QuantitiesModule";
import BoqModule from "@/modules/BoqModule";
import CostModule from "@/modules/CostModule";
import UtilitiesModule from "@/modules/UtilitiesModule";
import ComplianceModule from "@/modules/ComplianceModule";
import ReportsModule from "@/modules/ReportsModule";
import CollaborationModule from "@/modules/CollaborationModule";

const MODULES = [
  ["plot", "Plot & Site", Map, PlotModule],
  ["gis", "GIS Intelligence", Globe2, GisModule],
  ["planning", "Apartment Planning", Building2, PlanningModule],
  ["3d", "3D Visualisation", Box, ThreeDModule],
  ["calculations", "Calculations", Calculator, CalculationsModule],
  ["parking", "Parking", Car, ParkingModule],
  ["quantities", "Quantities", Package, QuantitiesModule],
  ["boq", "BOQ", ClipboardList, BoqModule],
  ["cost", "Cost Estimation", Wallet, CostModule],
  ["utilities", "Utilities", Droplets, UtilitiesModule],
  ["compliance", "Compliance", ShieldCheck, ComplianceModule],
  ["reports", "Reports", FileText, ReportsModule],
  ["collaboration", "Versions & Team", History, CollaborationModule],
];

const EDITABLE = [
  "name", "client", "location", "plot_reference", "status", "plot", "towers", "parking", "config",
  "quantity_ratios", "rates", "labour_rates", "equipment_rates", "utility_config", "compliance_rules",
];

export default function Workspace() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [accessRole, setAccessRole] = useState("viewer");
  const [active, setActive] = useState("plot");
  const [saveState, setSaveState] = useState("saved");
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

      <MetricsStrip analysis={analysis} />

      <div className="flex flex-1 min-h-0">
        <aside className="w-56 shrink-0 bg-slate-900 text-slate-300 hidden md:block" data-testid="module-nav">
          <nav className="py-3">
            {MODULES.map(([key, label, Icon]) => (
              <button
                key={key}
                onClick={() => setActive(key)}
                data-testid={`nav-module-${key}`}
                className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-[13px] text-left transition-colors ${
                  active === key ? "bg-blue-600 text-white" : "hover:bg-slate-800 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 min-w-0 p-4 md:p-6 space-y-4" data-testid={`module-panel-${active}`}>
          <div className="md:hidden flex gap-2 overflow-x-auto pb-2">
            {MODULES.map(([key, label]) => (
              <button
                key={key}
                onClick={() => setActive(key)}
                className={`text-xs whitespace-nowrap px-2 py-1 border rounded-sm ${
                  active === key ? "bg-slate-900 text-white" : "bg-white border-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
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
    </div>
  );
}
