import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Map, Building2, Calculator, Car, ClipboardList, Wallet, ShieldCheck, FileText, History, CalendarClock,
  Globe2, Box, Ruler, TrendingUp, Sparkles, Gauge,
} from "lucide-react";
import { api, apiError } from "../lib/api";
import { TopBar } from "../components/TopBar";
import { MetricsStrip } from "../components/MetricsStrip";
import { CommandPalette } from "../components/CommandPalette";
import AptPanel from "../components/AptPanel";
import { ProjectNav } from "../components/ProjectNav";
import SiteModule from "../modules/SiteModule";

// Loaded on demand. Importing all fifteen eagerly put three.js, leaflet and recharts
// into the first paint of a workspace that opens on Plot & Setbacks and may never show
// a 3D scene, a map or a chart at all -- 728 kB gzipped before the user did anything.
// SiteModule stays eager because it is what "plot" renders on open: splitting it would
// only trade bundle size for a spinner on the one tab that is always shown.
const GisModule = lazy(() => import("../modules/GisModule"));
const ThreeDModule = lazy(() => import("../modules/ThreeDModule"));
const EngineeringModule = lazy(() => import("../modules/EngineeringModule"));
const PlanningModule = lazy(() => import("../modules/PlanningModule"));
const CalculationsModule = lazy(() => import("../modules/CalculationsModule"));
const ParkingModule = lazy(() => import("../modules/ParkingModule"));
const BoqModule = lazy(() => import("../modules/BoqModule"));
const CostModule = lazy(() => import("../modules/CostModule"));
const ProgrammeModule = lazy(() => import("../modules/ProgrammeModule"));
const FinanceModule = lazy(() => import("../modules/FinanceModule"));
const ComplianceModule = lazy(() => import("../modules/ComplianceModule"));
const ReportsModule = lazy(() => import("../modules/ReportsModule"));
const DataHealthModule = lazy(() => import("../modules/DataHealthModule"));
const CollaborationModule = lazy(() => import("../modules/CollaborationModule"));

// Grouped by the order a project actually moves: understand the land, design the
// building, verify the engineering, price and programme it, then issue it. Two former
// destinations were folded in rather than grouped -- Quantities is the unpriced half of
// the BOQ, and Utilities computes the same water and storm figures as the engineering
// water modules, which is why the two once disagreed on sump size for one project.
const GROUPS = [
  ["site", "Site", [
    // Plot and setbacks were two entries that always had to be read together: the
    // setbacks edited in one are what the other builds its envelope from.
    ["plot", "Plot & Setbacks", Map, SiteModule],
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
    // Sits in Deliver on purpose: "can this be issued" is the question it answers, and it
    // is the one worth asking immediately before the report is generated.
    ["data-health", "Data Reliability", Gauge, DataHealthModule],
    ["reports", "Reports", FileText, ReportsModule],
    ["collaboration", "Versions & Team", History, CollaborationModule],
  ]],
];

const MODULES = GROUPS.flatMap(([, , items]) => items);

// Holds the panel's height while a chunk arrives, so the surrounding chrome does not jump
// and settle. Deliberately quiet: on a warm cache this is on screen for a few frames, and
// a spinner that announces itself is worse than one nobody notices.
function ModuleLoading() {
  return (
    <div className="flex items-center justify-center py-24 text-sm text-muted-foreground"
         data-testid="module-loading">
      Loading module...
    </div>
  );
}
const GROUP_OF = Object.fromEntries(
  GROUPS.flatMap(([g, , items]) => items.map((m) => [m[0], g])));
const GROUP_LABEL = Object.fromEntries(GROUPS.map(([g, label]) => [g, label]));

const EDITABLE = [
  "name", "client", "location", "plot_reference", "status", "plot", "towers", "parking", "config",
  "quantity_ratios", "rates", "labour_rates", "equipment_rates", "utility_config", "compliance_rules",
  "engineering",
  // The programme config holds the user's per-task edits; without it a reload silently
  // discards them and the table quietly reverts to the generated plan.
  "schedule",
  // Setbacks live under dev_controls and are the one value the envelope is built from.
  // Without this every setback edit was discarded on reload.
  "dev_controls",
  // Shared, society-wide amenity areas are edited through update() like everything else
  // here. Leaving them out meant the clubhouse and pool areas a user typed were dropped
  // the moment the page reloaded, while still counting toward area until then.
  "society_amenities",
  // The packed site layout. Both the site map and the 3D view write it through update()
  // and both read it back expecting it to persist; it never did, so every session paid
  // to regenerate it and the staleness stamp it carries had nothing to compare against.
  "site_layout",
];

export default function Workspace() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [accessRole, setAccessRole] = useState("viewer");
  const [active, setActive] = useState("plot");
  const [saveState, setSaveState] = useState("saved");
  // "fresh" | "recomputing" | "stale" — whether the figures on screen were computed from
  // the project as it stands. `analysedAt` is when they last were.
  const [analysisState, setAnalysisState] = useState("recomputing");
  const [analysedAt, setAnalysedAt] = useState(null);
  const [duration, setDuration] = useState(null);
  const dirty = useRef(0);   // edit generation, not a boolean -- see saveNow

  useEffect(() => {
    api
      .get(`/projects/${projectId}`)
      .then(({ data }) => {
        setAccessRole(data.access_role);
        setProject(data);
      })
      .catch((e) => toast.error(apiError(e.response?.data?.detail)));
  }, [projectId]);

  // Live recalculation.
  //
  // A failure here used to end in `.catch(() => {})`. When /analyse failed — a backend
  // restart, a network blip, a document the engine throws on — `analysis` kept its previous
  // value, so FAR, built-up area, cost, the compliance score and the whole metrics rail
  // carried on showing figures computed from an older version of the project with nothing
  // on screen to say so. Silence is the worst outcome for a number someone signs off on.
  //
  // So a failure is recorded, retried with the same backoff the autosave uses, and shown.
  const analyseRetries = useRef(0);
  const analyseTimer = useRef(null);

  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    setAnalysisState((prev) => (prev === "stale" ? "stale" : "recomputing"));

    const run = () => {
      api
        .post("/analyse", { project })
        .then(({ data }) => {
          if (cancelled) return;
          analyseRetries.current = 0;
          setAnalysis(data);
          setAnalysedAt(new Date());
          setAnalysisState("fresh");
        })
        .catch(() => {
          if (cancelled) return;
          setAnalysisState("stale");
          const wait = Math.min(2000 * 2 ** analyseRetries.current, 30000);
          analyseRetries.current += 1;
          analyseTimer.current = setTimeout(run, wait);
        });
    };

    analyseTimer.current = setTimeout(run, 250);
    return () => {
      cancelled = true;
      clearTimeout(analyseTimer.current);
    };
  }, [project]);

  // Autosave.
  //
  // Three things it has to get right, and the original got none of them:
  //
  //  1. A FAILED SAVE MUST RETRY. It used to toast an error and stop. The next attempt
  //     only came if the user happened to edit again, so a save that failed while they
  //     were finishing up lost the work silently.
  //  2. AN EDIT DURING A SAVE MUST NOT BE MARKED CLEAN. The flag was cleared after the
  //     request returned, so anything typed while it was in flight was recorded as
  //     already saved and then never sent.
  //  3. LEAVING THE PAGE MUST FLUSH. There is a debounce window where recent edits exist
  //     only in memory; closing the tab inside it threw them away.
  const saveTimer = useRef(null);
  const retries = useRef(0);
  const latest = useRef(project);
  latest.current = project;

  const saveNow = useCallback(async () => {
    const snapshot = latest.current;
    if (!snapshot || !dirty.current) return;
    // Claim the current edit generation. Anything the user types after this line bumps it
    // again, so the save cannot mark those edits clean.
    const generation = dirty.current;
    setSaveState("saving");
    const updates = {};
    EDITABLE.forEach((k) => {
      if (snapshot[k] !== undefined) updates[k] = snapshot[k];
    });
    try {
      // The revision this edit started from. The server writes only if the document is
      // still at it, so a save can no longer replace a whole subtree — the tower list, the
      // plot — that someone else changed while this tab was editing.
      const { data } = await api.put(`/projects/${projectId}`, { updates, rev: snapshot.rev });
      retries.current = 0;
      if (data && data.rev !== undefined) setProject((prev) => ({ ...prev, rev: data.rev }));
      if (dirty.current === generation) {
        dirty.current = false;
        setSaveState("saved");
      } else {
        setSaveState("saving");        // more arrived while this was in flight
      }
    } catch (e) {
      // 409 is not a failure to retry: retrying the same body would overwrite the other
      // edit, which is the thing the check exists to prevent. Take the server's copy, put
      // this tab's fields back on top of it, and let the next tick save that.
      if (e.response?.status === 409) {
        try {
          const { data: server } = await api.get(`/projects/${projectId}`);
          setProject((prev) => {
            const merged = { ...server };
            EDITABLE.forEach((k) => {
              if (prev[k] !== undefined) merged[k] = prev[k];
            });
            return merged;
          });
          toast.message("Someone else changed this project", {
            description: "Their version was loaded and your edits reapplied on top. Check the "
                       + "tabs you were working in before saving again.",
          });
          setSaveState("saving");
          saveTimer.current = setTimeout(saveNow, 1200);
        } catch {
          setSaveState("error");
          saveTimer.current = setTimeout(saveNow, 5000);
        }
        return;
      }
      setSaveState("error");
      // Back off and keep trying rather than dropping the work on the floor.
      const wait = Math.min(2000 * 2 ** retries.current, 30000);
      retries.current += 1;
      if (retries.current === 1) toast.error(apiError(e.response?.data?.detail));
      saveTimer.current = setTimeout(saveNow, wait);
    }
  }, [projectId]);

  useEffect(() => {
    if (!project || !dirty.current) return;
    setSaveState("saving");
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(saveNow, 900);
    return () => clearTimeout(saveTimer.current);
  }, [project, saveNow]);

  // Flush on the way out: closing the tab, switching away, or navigating.
  useEffect(() => {
    const flush = () => {
      if (!dirty.current) return;
      clearTimeout(saveTimer.current);
      saveNow();
    };
    const onHide = () => { if (document.visibilityState === "hidden") flush(); };
    const onBeforeUnload = (e) => {
      if (!dirty.current) return;
      flush();
      e.preventDefault();
      e.returnValue = "";        // prompts only while a save is genuinely outstanding
    };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("beforeunload", onBeforeUnload);
      flush();
    };
  }, [saveNow]);

  // Headline build duration for the metrics strip. Uses the summary form of the
  // programme endpoint, which skips float verification and the 120-activity payload --
  // the completion date does not depend on either, and this runs on every recalculation.
  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    const t = setTimeout(() => {
      // The project's own schedule config, so the headline cost reflects the programme the
      // user actually set -- target date, added tasks and all -- not a default one.
      api.post("/schedule", { project, summary: true, config: project.schedule || {} })
        .then(({ data }) => { if (!cancelled) setDuration(data.ok ? data : null); })
        .catch(() => { if (!cancelled) setDuration(null); });
    }, 600);   // debounce: the project mutates on every keystroke while editing
    return () => { cancelled = true; clearTimeout(t); };
  }, [project]);

  const update = useCallback((mutator) => {
    // A counter, not a boolean: the save compares the value it started with against the
    // value at the end, which is how an edit made mid-request stays dirty.
    dirty.current = (dirty.current || 0) + 1;
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
            title={saveState === "error"
              ? "Could not save. Retrying automatically — your work is not lost."
              : saveState === "saving" ? "Saving…" : "All changes saved"}
          >
            {saveState === "error" ? "retrying" : saveState}
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
          <MetricsStrip analysis={analysis} duration={duration} vertical
                        state={analysisState} at={analysedAt} />
        </aside>

        <main className="flex-1 min-w-0 p-4 md:p-6 space-y-4" data-testid={`module-panel-${active}`}>
          {Current && (
            <Suspense fallback={<ModuleLoading />}>
              <Current
                project={project}
                analysis={analysis}
                update={update}
                readOnly={readOnly}
                projectId={projectId}
                setProject={setProject}
                goToModule={setActive}
              />
            </Suspense>
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
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-[#F4C2C2] hover:bg-[#EBACAC] text-[#6B2233] shadow-lg shadow-[#F4C2C2]/50 pl-3.5 pr-4 py-2.5 text-sm font-medium transition-colors"
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
