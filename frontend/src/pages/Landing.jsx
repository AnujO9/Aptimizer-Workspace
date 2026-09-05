// Public landing page.
//
// Every claim below is checked against the app rather than written around it: the
// workspace map is the sidebar's own group order, the pipeline is the order siteplan
// runs its stages, the code references are the ones engineering.py attaches to its
// outputs, and each number in the metrics band is the real length of the collection it
// counts. A landing page that overstates its product is a bug with a very long feedback
// loop, so these lists are kept beside the source of truth in the comments.
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Brand, BrandMark } from "../components/Brand";
import { ScrollScene } from "../components/ScrollScene";
import {
  Accessibility,
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  BookOpen,
  Box,
  Boxes,
  Building2,
  Car,
  CheckCircle2,
  ChevronDown,
  Compass,
  Droplets,
  Factory,
  FileText,
  Flame,
  Grid3x3,
  Layers,
  Leaf,
  Ruler,
  ShieldCheck,
  Sparkles,
  TreePine,
  Wallet,
  Waves,
} from "lucide-react";
import { motion, useMotionValueEvent, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import { LANDING } from "../constants/testIds";
import CountUp from "../components/landing/CountUp";
import ReactiveButton from "../components/landing/ReactiveButton";
import { Reveal, RevealItem, Stagger } from "../components/landing/Reveal";

// The workspace, exactly as the sidebar groups it (see pages/Workspace.jsx GROUPS).
// Fifteen modules; the two the sidebar shows that are not project work -- Reports is the
// download page, Versions & Team the audit trail -- are still listed, because leaving
// them out would misstate what a visitor finds when they sign in.
const WORKSPACE = [
  {
    group: "Site",
    icon: Compass,
    items: [
      ["Plot & Setbacks", "Boundary, area, road edges and the NBC setback minimums"],
      ["GIS Intelligence", "Terrain, flood, wind, sun path, rooftop solar and suitability"],
    ],
  },
  {
    group: "Design",
    icon: Building2,
    items: [
      ["Apartment Planning", "Unit mix, floor plates and a Vastu audit of each one"],
      ["Parking", "Per-building demand against the norm your authority uses"],
      ["3D Visualisation", "Massing, roads and amenity blocks in three dimensions"],
    ],
  },
  {
    group: "Engineering",
    icon: Ruler,
    items: [
      ["Calculations", "Carpet to saleable, and the FAR it produces, step by step"],
      ["IS / NBC Engineering", "Thirteen modules, each one citing its own clause"],
    ],
  },
  {
    group: "Cost & Programme",
    icon: Wallet,
    items: [
      ["BOQ & Quantities", "Material, labour and equipment schedules"],
      ["Cost Estimation", "Your rates, resolved per square metre and per flat"],
      ["Programme", "CPM critical path on an IS 456 floor cycle"],
      ["Feasibility & ROI", "Revenue, margin, IRR, payback and cash flow"],
    ],
  },
  {
    group: "Deliver",
    icon: ShieldCheck,
    items: [
      ["Compliance", "Rule by rule, with the margin left on each"],
      ["Data Reliability", "Whether the inputs behind those figures hold up"],
      ["Reports", "Seventeen PDFs and the BOQ workbook"],
      ["Versions & Team", "Saved versions, roles and the activity log"],
    ],
  },
];

// The layout pipeline, in the order the engine runs it (backend/siteplan).
const PIPELINE = [
  ["Clean the boundary", "The drawn polygon is repaired and closed before anything is measured against it."],
  ["Offset the setbacks", "Front, rear and side setbacks are applied per edge to give the buildable envelope."],
  ["Route the roads", "A perimeter fire-tender ring is reserved first, then internal drives where they are needed."],
  ["Place the amenities", "Low-rise blocks for clubhouse, gym and pool take land from the remaining open space."],
  ["Pack the towers", "Footprints are packed on a grid, sweeping rotation and floor count for the best yield."],
  ["Score the layout", "Unit yield, tower spacing, open space and circulation are scored, and containment re-checked."],
];

// Engineering modules and the code each answers to. Thirteen, matching
// engineering.analyse_engineering().modules.
const MODULES = [
  { icon: Layers, name: "Structural load estimator", code: "IS 875 Parts 1–3" },
  { icon: Waves, name: "Seismic zone & base shear", code: "IS 1893 (Part 1)" },
  { icon: Boxes, name: "Foundation advisor", code: "IS 6403, IS 1904" },
  { icon: Layers, name: "Concrete mix design", code: "IS 10262" },
  { icon: Grid3x3, name: "Column grid optimiser", code: "IS 456, IS 3861" },
  { icon: Droplets, name: "Water infrastructure", code: "IS 1172" },
  { icon: Waves, name: "Storm water & harvesting", code: "IS 3764" },
  { icon: Car, name: "Parking compliance", code: "NBC Part 4, SP:21" },
  { icon: Flame, name: "Fire & life safety", code: "NBC 2016 Part 4" },
  { icon: Accessibility, name: "Accessibility", code: "NBC Part 3, RPwD 2016" },
  { icon: Leaf, name: "Green rating", code: "GRIHA, IGBC" },
  { icon: Factory, name: "Embodied carbon", code: "GRIHA v2019" },
  { icon: TreePine, name: "Plantation plan", code: "Local bye-law" },
];

// What the AI layer actually does -- see backend/ai.py, citations.py, codesearch.py
// and aifloorplan.py. Shipped capability, not roadmap.
const INTELLIGENCE = [
  {
    icon: Box,
    title: "Reads your project, never re-derives it",
    body: "Apt answers from this project's computed outputs — the same figures already on screen. It explains the engine's result; it does not recalculate it.",
  },
  {
    icon: BadgeCheck,
    title: "Citations resolved before you see them",
    body: "Every IS and NBC reference in a reply is checked against a 62-clause registry. One that will not resolve is marked in place, not quietly deleted.",
  },
  {
    icon: BookOpen,
    title: "Clause text, or nothing",
    body: "Answers that need the code quote a retrieved passage, split on the document's own numbering with tables kept whole. With no corpus loaded it says so.",
  },
  {
    icon: Grid3x3,
    title: "Floor plates that answer to the manual",
    body: "Unit layouts are generated per floor with circulation, exterior windows and attached balconies, then audited against the Vastu anchors and hard rules.",
  },
];

// Illustrative, and labelled as such on the card.
const CITATION_SAMPLE = [
  { code: "IS 875 (Part 2), Cl. 3.1", ok: true, note: "Clause in registry" },
  { code: "IS 1893 (Part 1), Cl. 6.4.2", ok: true, note: "Clause in registry" },
  { code: "IS 456, Cl. 26.5.1.1", ok: false, note: "Standard known, clause not in registry" },
];

const METRICS = [
  { value: 15, label: "linked workspace modules" },
  { value: 6, label: "stage layout pipeline" },
  { value: 13, label: "code-backed engineering modules" },
  { value: 62, label: "clauses every citation is checked against" },
  { value: 17, label: "downloadable reports" },
];

const NAV_LINKS = [
  ["Workspace", "#workspace"],
  ["Pipeline", "#pipeline"],
  ["Codes", "#modules"],
  ["Assurance", "#intelligence"],
];

function SectionLabel({ children }) {
  return (
    <div className="flex items-center gap-3">
      <span className="h-px w-8 bg-blue-600" />
      <span className="font-mono text-xs uppercase tracking-[0.18em] text-blue-700">{children}</span>
    </div>
  );
}

/** Section heading block: label, title, and an optional standfirst. */
function SectionHead({ label, title, children }) {
  return (
    <>
      <Reveal y={0}>
        <SectionLabel>{label}</SectionLabel>
      </Reveal>
      <Reveal delay={0.05}>
        <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          {title}
        </h2>
      </Reveal>
      {children ? (
        <Reveal delay={0.1}>
          <p className="mt-4 max-w-2xl leading-relaxed text-slate-600">{children}</p>
        </Reveal>
      ) : null}
    </>
  );
}

/** Bordered card with a hairline header strip. Used for both worked examples. */
function SampleCard({ icon: Icon, title, children }) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold tracking-tight text-slate-900">
          <Icon className="h-4 w-4 text-blue-600" />
          {title}
        </span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">Sample</span>
      </div>
      {children}
    </div>
  );
}

const HERO_FRAMES = [1, 10, 20, 30, 38, 45, 52, 60];

export default function Landing() {
  const { user } = useAuth();
  const signedIn = Boolean(user);
  const reduced = useReducedMotion();
  const heroRef = useRef(null);
  const [navSolid, setNavSolid] = useState(false);

  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.3 });

  // The hero is a scroll runway with a sticky viewport inside it: the sequence needs
  // travel to scrub through. Shortened from 280vh -- almost three screens of scrolling
  // before the first sentence is a cost the sequence was not paying back.
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const cueFade = useTransform(heroProgress, [0, 0.12], [1, 0]);

  useMotionValueEvent(scrollYProgress, "change", (v) => setNavSolid(v > 0.01));

  const workspaceHref = signedIn ? "/projects" : "/register";
  const workspaceLabel = signedIn ? "Open workspace" : "Start a project";

  return (
    <div className="min-h-screen text-left" data-testid={LANDING.root}>
      <motion.div
        aria-hidden="true"
        data-testid={LANDING.scrollProgress}
        style={{ scaleX: progress }}
        className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-blue-600"
      />

      <header
        data-testid={LANDING.nav}
        className={[
          "sticky top-0 z-40 bg-white/95 backdrop-blur-sm",
          "transition-[border-color,box-shadow] duration-300 ease-out",
          navSolid ? "border-b border-slate-200 shadow-sm" : "border-b border-transparent",
        ].join(" ")}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link to="/" className="flex items-center gap-2" data-testid={LANDING.navBrand}>
            <Brand markClass="h-9 w-auto" wordClass="text-lg" />
          </Link>

          <nav className="hidden items-center gap-8 md:flex">
            {NAV_LINKS.map(([label, href]) => (
              <a
                key={href}
                href={href}
                className="relative text-sm text-slate-600 transition-colors duration-200 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
              >
                <span className="after:absolute after:inset-x-0 after:-bottom-1.5 after:h-px after:origin-left after:scale-x-0 after:bg-blue-600 after:transition-transform after:duration-200 motion-safe:hover:after:scale-x-100">
                  {label}
                </span>
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <ReactiveButton as={Link} to="/login" variant="ghost" size="sm" data-testid={LANDING.navSignIn}>
              Sign in
            </ReactiveButton>
            <ReactiveButton
              as={Link}
              to={workspaceHref}
              size="sm"
              icon={<ArrowRight className="h-4 w-4" />}
              data-testid={LANDING.navPrimaryCta}
            >
              {workspaceLabel}
            </ReactiveButton>
          </div>
        </div>
      </header>

      {/* Hero: the build sequence scrubs with the scroll — sketch, dimensioned plan, 3D
          model, structure, mark — which is the product's own story in order. */}
      <section ref={heroRef} className="relative h-[200vh]" data-testid={LANDING.hero}>
        <div
          className="sticky top-0 isolate flex h-screen items-center overflow-hidden"
          style={{ background: "radial-gradient(120% 90% at 50% 35%, #DCD8CB 0%, #CECBBE 45%, #B2B5B1 100%)" }}
        >
          {/* The sequence gets the screen to itself. White copy over a pale studio render
              needed an 85% black scrim to stay readable, which is what made the render
              look flat; the pitch sits below instead, where it needs no scrim at all. */}
          <ScrollScene target={heroRef} frames={HERO_FRAMES} leadIn={0.06} />

          <motion.div
            aria-hidden="true"
            style={{ opacity: cueFade }}
            className="absolute inset-x-0 bottom-8 z-10 flex justify-center"
            animate={reduced ? undefined : { y: [0, 6, 0] }}
            transition={reduced ? undefined : { duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          >
            <ChevronDown className="h-5 w-5 text-slate-500" />
          </motion.div>
        </div>
      </section>

      {/* The pitch, and the numbers behind it, on one dark ground. Two separate sections
          here meant two full screens before any substance. */}
      <section className="relative bg-slate-950 py-24 sm:py-28" data-testid={LANDING.heroCopy}>
        <div className="relative z-10 mx-auto max-w-4xl px-6">
          <div className="flex flex-col items-center text-center">
            <Reveal immediate>
              <motion.div
                animate={reduced ? undefined : { y: [0, -8, 0] }}
                transition={reduced ? undefined : { duration: 6, repeat: Infinity, ease: "easeInOut" }}
              >
                <BrandMark light className="h-16 w-auto drop-shadow-[0_4px_28px_rgba(0,0,0,0.5)] sm:h-20" />
              </motion.div>
            </Reveal>

            <Reveal delay={0.1} immediate>
              <div className="mt-7 flex items-center gap-3 text-blue-300">
                <span className="h-px w-8 bg-blue-400/70" />
                <span className="font-mono text-xs uppercase tracking-[0.18em]">
                  Civil engineering platform
                </span>
                <span className="h-px w-8 bg-blue-400/70" />
              </div>
            </Reveal>

            <Reveal delay={0.16} immediate>
              <h1 className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-6xl">
                Plot boundary in.
                <br />
                <span className="text-blue-400">Compliant scheme out.</span>
              </h1>
            </Reveal>

            <Reveal delay={0.22} immediate>
              <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                Draw the plot and Aptimizer carries it the whole way — site intelligence,
                buildable envelope, tower placement, unit mix, IS and NBC engineering, BOQ,
                cost, programme and feasibility. One project model behind all of it, and every
                figure traceable to the input and the clause it came from.
              </p>
            </Reveal>

            <Reveal delay={0.28} immediate>
              <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
                <ReactiveButton
                  as={Link}
                  to={workspaceHref}
                  size="lg"
                  icon={<ArrowRight className="h-4 w-4" />}
                  data-testid={LANDING.heroPrimaryCta}
                >
                  {workspaceLabel}
                </ReactiveButton>
                <ReactiveButton
                  as="a"
                  href="#workspace"
                  variant="outline"
                  size="lg"
                  className="border-white/30 bg-white/5 text-white backdrop-blur-sm hover:border-white/50 hover:bg-white/10"
                  data-testid={LANDING.heroSecondaryCta}
                >
                  See what it does
                </ReactiveButton>
              </div>
            </Reveal>
          </div>

          {/* Metrics, on the same ground as the claim they support. */}
          <Stagger
            className="mt-16 grid grid-cols-2 gap-x-6 gap-y-8 border-t border-white/10 pt-10 sm:grid-cols-3 lg:grid-cols-5"
            data-testid={LANDING.metrics}
          >
            {METRICS.map((m) => (
              <RevealItem key={m.label}>
                <div className="font-mono text-3xl font-semibold tracking-tight text-white">
                  <CountUp value={m.value} data-testid={LANDING.metricValue} />
                </div>
                <div className="mt-1 text-xs leading-snug text-slate-400">{m.label}</div>
              </RevealItem>
            ))}
          </Stagger>

          <Reveal delay={0.1}>
            <p className="mt-10 text-center text-sm leading-relaxed text-slate-400">
              Built for Indian byelaws. FAR, setbacks, ground coverage and parking norms are
              configuration per municipal body, never hardcoded constants. Money in INR, grouped
              in lakh and crore.
            </p>
          </Reveal>
        </div>
      </section>

      {/* The workspace map. This is the product; everything after it is evidence. */}
      <section id="workspace" className="scroll-mt-20 py-20 sm:py-24" data-testid={LANDING.workspace}>
        <div className="mx-auto max-w-6xl px-6">
          <SectionHead label="The workspace" title="Fifteen modules, one project model.">
            Move a boundary vertex and everything downstream recomputes from it — envelope,
            unit count, loads, quantities, cost, programme. Nothing is re-entered anywhere, so
            no two screens can disagree about the same fact.
          </SectionHead>

          {/* Five groups into a two- or three-column grid leaves the last row short, and a
              short row in a hairline grid is a grey hole rather than an ending. The last
              group spans the remainder at each breakpoint instead: 2+2+(1×2) at sm,
              3+(1+1×2) at lg, and a clean five across from xl. */}
          <Stagger step={0.05} className="mt-12 grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {WORKSPACE.map((col, i) => {
              const Icon = col.icon;
              const last = i === WORKSPACE.length - 1;
              return (
                <RevealItem
                  key={col.group}
                  data-testid={LANDING.workspaceGroup}
                  className={last ? "sm:col-span-2 lg:col-span-2 xl:col-span-1" : ""}
                >
                  <div className="flex h-full flex-col bg-white p-6">
                    <div className="flex items-center gap-2.5">
                      <span className="grid h-8 w-8 place-items-center rounded-sm border border-slate-200 bg-slate-50 text-slate-600">
                        <Icon className="h-4 w-4" />
                      </span>
                      <h3 className="font-mono text-xs uppercase tracking-[0.14em] text-slate-500">
                        {col.group}
                      </h3>
                    </div>

                    <ul className="mt-5 space-y-4">
                      {col.items.map(([name, note]) => (
                        <li key={name}>
                          <div className="text-sm font-semibold tracking-tight text-slate-900">{name}</div>
                          <p className="mt-0.5 text-[13px] leading-relaxed text-slate-500">{note}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                </RevealItem>
              );
            })}
          </Stagger>
        </div>
      </section>

      {/* Pipeline */}
      <section
        id="pipeline"
        className="scroll-mt-20 border-y border-slate-200 bg-white py-20 sm:py-24"
        data-testid={LANDING.pipeline}
      >
        <div className="mx-auto max-w-6xl px-6">
          <SectionHead label="Layout pipeline" title="Six stages, in the order a site plan is drafted.">
            The plot polygon is a hard constraint. No footprint, podium, amenity block or road
            may cross it, and containment is re-checked before any layout is returned.
          </SectionHead>

          <Stagger step={0.05} className="mt-12 grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE.map(([title, body], i) => (
              <RevealItem key={title} data-testid={LANDING.pipelineStep}>
                <div className="group h-full bg-white p-6 transition-colors duration-200 hover:bg-slate-50">
                  <span className="font-mono text-xs text-slate-400">{String(i + 1).padStart(2, "0")}</span>
                  <h3 className="mt-3 text-base font-semibold tracking-tight text-slate-900">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
                </div>
              </RevealItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Codes */}
      <section id="modules" className="scroll-mt-20 py-20 sm:py-24" data-testid={LANDING.modules}>
        <div className="mx-auto max-w-6xl px-6">
          <SectionHead label="Engineering modules" title="Every module answers to a code.">
            Clause references travel with the result, into the screen and on into the PDF.
            Nothing returns a bare number.
          </SectionHead>

          {/* CSS columns rather than a grid: thirteen is prime to every sensible column
              count, and a grid of hairline cells would leave three grey holes in the last
              row. Multi-column balances the list instead — 5/4/4 — and stays balanced
              whatever the module count becomes. */}
          <Reveal delay={0.14}>
            {/* Names wrap rather than truncate: a clipped module name tells the reader
                nothing, and these are the whole point of the section. The code stays on
                the first line by aligning the row on the baseline, not the box. */}
            <div className="mt-12 columns-1 gap-x-14 md:columns-2 lg:columns-3">
              {MODULES.map((mod) => {
                const Icon = mod.icon;
                return (
                  <div
                    key={mod.name}
                    data-testid={LANDING.moduleCard}
                    className="group flex break-inside-avoid items-baseline justify-between gap-4 border-b border-slate-200 py-3.5"
                  >
                    <span className="flex min-w-0 items-baseline gap-3">
                      <Icon className="h-4 w-4 shrink-0 translate-y-0.5 text-slate-400 transition-colors duration-200 group-hover:text-blue-600" />
                      <span className="text-sm font-medium tracking-tight text-slate-900">
                        {mod.name}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-xs text-slate-500">{mod.code}</span>
                  </div>
                );
              })}
            </div>
          </Reveal>
        </div>
      </section>

      {/* Assurance: traceability and the AI layer share one section, because they are the
          same promise made about two different surfaces. Two sections said it twice. */}
      <section
        id="intelligence"
        className="scroll-mt-20 border-t border-slate-200 bg-white py-20 sm:py-24"
        data-testid={LANDING.intelligence}
      >
        <div className="mx-auto max-w-6xl px-6">
          <SectionHead label="Assurance" title="Every number says where it came from.">
            A wrong IS reference stated confidently is worse than no reference at all. So each
            screen shows the inputs it used, the formula it applied and the clause behind it —
            and the assistant reading those screens is held to the same standard.
          </SectionHead>

          <div className="mt-12 grid items-start gap-10 lg:grid-cols-[1fr_0.85fr]">
            <Stagger step={0.05} className="grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-2">
              {INTELLIGENCE.map((item) => {
                const Icon = item.icon;
                return (
                  <RevealItem key={item.title} data-testid={LANDING.intelligenceCard}>
                    <div className="group h-full bg-white p-6 transition-colors duration-200 hover:bg-slate-50">
                      <span className="grid h-9 w-9 place-items-center rounded-sm border border-slate-200 bg-slate-50 text-slate-700 transition-colors duration-200 group-hover:border-blue-200 group-hover:bg-blue-50 group-hover:text-blue-700">
                        <Icon className="h-4 w-4" />
                      </span>
                      <h3 className="mt-4 text-[15px] font-semibold leading-snug tracking-tight text-slate-900">
                        {item.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.body}</p>
                    </div>
                  </RevealItem>
                );
              })}
            </Stagger>

            <div className="space-y-6" data-testid={LANDING.traceability}>
              {/* A worked figure, shown the way the app shows it. */}
              <Reveal delay={0.08}>
                <SampleCard icon={FileText} title="Permitted built-up area">
                  <dl className="divide-y divide-slate-200">
                    <div className="flex items-baseline justify-between px-5 py-2.5">
                      <dt className="text-sm text-slate-500">Plot area</dt>
                      <dd className="font-mono text-sm text-slate-900">4,000.00 m²</dd>
                    </div>
                    <div className="flex items-baseline justify-between px-5 py-2.5">
                      <dt className="text-sm text-slate-500">Permitted FAR</dt>
                      <dd className="font-mono text-sm text-slate-900">2.50</dd>
                    </div>
                    <div className="px-5 py-2.5">
                      <dt className="text-sm text-slate-500">Formula</dt>
                      <dd className="mt-1 rounded-sm bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800">
                        Permitted BUA = Plot area × FAR
                      </dd>
                    </div>
                    <div className="px-5 py-2.5">
                      <dt className="text-sm text-slate-500">Reference</dt>
                      <dd className="mt-1 text-sm text-slate-700">
                        Local development control byelaw, configured per municipal body
                      </dd>
                    </div>
                  </dl>
                  <div className="flex items-baseline justify-between border-t border-slate-200 bg-blue-50 px-5 py-3.5">
                    <span className="text-sm font-semibold text-slate-900">Result</span>
                    <span className="font-mono text-lg font-semibold tracking-tight text-blue-700">
                      10,000.00 m²
                    </span>
                  </div>
                </SampleCard>
              </Reveal>

              {/* And the same standard applied to a generated answer. */}
              <Reveal delay={0.14}>
                <SampleCard icon={Sparkles} title="Citations in a reply">
                  <ul className="divide-y divide-slate-200" data-testid={LANDING.citationSample}>
                    {CITATION_SAMPLE.map((c) => (
                      <li key={c.code} className="flex items-start gap-3 px-5 py-2.5">
                        {c.ok ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                        ) : (
                          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                        )}
                        <div className="min-w-0">
                          <div className="font-mono text-sm text-slate-900">{c.code}</div>
                          <div className={`mt-0.5 text-xs ${c.ok ? "text-slate-500" : "text-amber-700"}`}>
                            {c.note}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                  <div className="border-t border-slate-200 bg-blue-50 px-5 py-3.5 text-sm leading-relaxed text-slate-700">
                    A reference the registry cannot confirm stays in the answer and is marked, so
                    you can see exactly which one to check before you rely on it.
                  </div>
                </SampleCard>
              </Reveal>
            </div>
          </div>

          <Reveal delay={0.16}>
            <div className="mt-12 grid gap-6 border-t border-slate-200 pt-8 text-sm leading-relaxed text-slate-500 sm:grid-cols-2">
              <p>
                Full precision is kept internally and rounded at display only, so nothing drifts
                between a screen and the report it prints to. GIS, compliance, cost, engineering,
                planning, feasibility and scheme comparison each write their own narrative from
                their own computed state, stored with the project.
              </p>
              <p>
                An intent gate and a cache keyed on the project version stop a short question
                paying for thirteen engineering modules and eleven optimisers. Apt explains the
                engine's output; it is not a substitute for an engineer's sign-off. Bring your own
                model key — with none configured the AI features say so rather than failing on
                click.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Closing call to action */}
      <section className="bg-slate-950 py-20" data-testid={LANDING.cta}>
        <div className="mx-auto max-w-3xl px-6 text-center">
          <Reveal y={0}>
            <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Start with a plot boundary.
            </h2>
          </Reveal>
          <Reveal delay={0.06}>
            <p className="mx-auto mt-4 max-w-xl leading-relaxed text-slate-300">
              Draw the site, set the byelaw configuration, and read the scheme back with every
              number traceable to its source.
            </p>
          </Reveal>
          <Reveal delay={0.12}>
            <div className="mt-9 flex flex-wrap justify-center gap-3">
              <ReactiveButton
                as={Link}
                to={workspaceHref}
                size="lg"
                icon={<ArrowRight className="h-4 w-4" />}
                data-testid={LANDING.ctaPrimary}
              >
                {workspaceLabel}
              </ReactiveButton>
              <ReactiveButton
                as={Link}
                to="/login"
                variant="outline"
                size="lg"
                className="border-slate-700 bg-transparent text-slate-200 hover:border-slate-600 hover:bg-slate-800 hover:text-white"
              >
                Sign in
              </ReactiveButton>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-white py-10" data-testid={LANDING.footer}>
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <BrandMark className="h-7 w-auto" />
            <span className="text-sm font-semibold tracking-tight text-slate-900">Aptimizer</span>
          </div>
          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {NAV_LINKS.map(([label, href]) => (
              <a key={href} href={href} className="text-sm text-slate-500 transition-colors hover:text-slate-900">
                {label}
              </a>
            ))}
          </nav>
          <p className="font-mono text-xs text-slate-500">
            Civil engineering and real estate planning. Built for Indian codes.
          </p>
        </div>
      </footer>
    </div>
  );
}
