// Public landing page.
//
// Content is drawn from what the platform actually does. The pipeline steps,
// the module list and the code references below match the engineering scope,
// so nothing here promises a capability the product does not have.
import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Boxes,
  Building2,
  CheckCircle2,
  Compass,
  Droplets,
  FileText,
  Flame,
  Grid3x3,
  Layers,
  Leaf,
  Route,
  Ruler,
  ShieldCheck,
  Sparkles,
  Waves,
} from "lucide-react";
import { motion, useMotionValueEvent, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { LANDING } from "@/constants/testIds";
import BlueprintPlot from "@/components/landing/BlueprintPlot";
import CountUp from "@/components/landing/CountUp";
import ReactiveButton from "@/components/landing/ReactiveButton";
import { Reveal, RevealItem, Stagger } from "@/components/landing/Reveal";

// The layout pipeline, in the order the engine runs it.
const PIPELINE = [
  {
    icon: Compass,
    title: "Clean the boundary",
    body: "The drawn polygon is repaired and closed before anything is measured against it.",
  },
  {
    icon: Ruler,
    title: "Offset the setbacks",
    body: "Front, rear and side setbacks are applied per edge to give the buildable envelope.",
  },
  {
    icon: Grid3x3,
    title: "Seed the towers",
    body: "Footprints are packed on a grid, sweeping rotation and floor count for the best yield.",
  },
  {
    icon: Sparkles,
    title: "Refine the layout",
    body: "Genetic refinement scores unit yield, inter tower spacing, open space and circulation.",
  },
  {
    icon: Route,
    title: "Route the roads",
    body: "A perimeter fire tender ring is reserved first, then internal drives where they are needed.",
  },
  {
    icon: Building2,
    title: "Place the amenities",
    body: "Low rise blocks for gym, clubhouse and pool land in the remaining open space.",
  },
];

// Engineering modules and the code each one answers to.
const MODULES = [
  { icon: Layers, name: "Structural load estimator", code: "IS 875" },
  { icon: Waves, name: "Seismic analysis", code: "IS 1893" },
  { icon: Boxes, name: "Foundation design", code: "IS 6403, IS 1904" },
  { icon: Layers, name: "Concrete mix design", code: "IS 10262" },
  { icon: Droplets, name: "Water supply demand", code: "IS 1172" },
  { icon: Waves, name: "Storm water and harvesting", code: "IS 3764" },
  { icon: Route, name: "Parking provision", code: "NBC 2016" },
  { icon: Flame, name: "Fire safety checks", code: "NBC 2016 Part 4" },
  { icon: ShieldCheck, name: "Accessibility checks", code: "NBC 2016 Part 3" },
  { icon: Leaf, name: "Green rating", code: "GRIHA, IGBC" },
  { icon: Grid3x3, name: "Column grid optimizer", code: "Optimisation" },
];

const METRICS = [
  { value: 6, suffix: "", label: "stage layout pipeline" },
  { value: 11, suffix: "", label: "engineering modules" },
  { value: 9, suffix: "", label: "IS and NBC references" },
];

function SectionLabel({ children }) {
  return (
    <div className="flex items-center gap-3">
      <span className="h-px w-8 bg-blue-600" />
      <span className="font-mono text-xs uppercase tracking-[0.18em] text-blue-700">{children}</span>
    </div>
  );
}

export default function Landing() {
  const { user } = useAuth();
  const signedIn = Boolean(user);
  const reduced = useReducedMotion();
  const heroRef = useRef(null);
  const [navSolid, setNavSolid] = useState(false);

  // Page level scroll progress bar.
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.3 });

  // Drift the hero drawing slightly slower than the page for depth.
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const plotY = useTransform(heroProgress, [0, 1], [0, reduced ? 0 : 64]);

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    setNavSolid(v > 0.01);
  });

  const workspaceHref = signedIn ? "/projects" : "/register";
  const workspaceLabel = signedIn ? "Open workspace" : "Start a project";

  return (
    <div className="min-h-screen text-left" data-testid={LANDING.root}>
      {/* Scroll progress. Fixed above the nav, brand coloured. */}
      <motion.div
        aria-hidden="true"
        data-testid={LANDING.scrollProgress}
        style={{ scaleX: progress }}
        className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-blue-600"
      />

      {/* Nav. Solid at all times, gains a border and shadow once scrolled. */}
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
            <span className="grid h-8 w-8 place-items-center rounded-sm bg-blue-600">
              <Ruler className="h-4 w-4 text-white" />
            </span>
            <span className="text-lg font-semibold tracking-tight text-slate-900">Aptimizer</span>
          </Link>

          <nav className="hidden items-center gap-8 md:flex">
            {[
              ["Pipeline", "#pipeline"],
              ["Modules", "#modules"],
              ["Traceability", "#traceability"],
            ].map(([label, href]) => (
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
            <ReactiveButton
              as={Link}
              to="/login"
              variant="ghost"
              size="sm"
              data-testid={LANDING.navSignIn}
            >
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

      {/* Hero */}
      <section ref={heroRef} className="relative overflow-hidden" data-testid={LANDING.hero}>
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-[1.05fr_0.95fr] lg:py-28">
          <div>
            <Reveal y={0} immediate>
              <SectionLabel>Civil engineering platform</SectionLabel>
            </Reveal>

            <Reveal delay={0.06} immediate>
              <h1 className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
                Plot boundary in.
                <br />
                <span className="text-blue-600">Compliant scheme out.</span>
              </h1>
            </Reveal>

            <Reveal delay={0.12} immediate>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
                Draw the plot, set the brief, and Aptimizer returns a buildable development scheme.
                Envelope, tower placement, unit mix, compliance checks, BOQ and cost estimate all
                come from one project model.
              </p>
            </Reveal>

            <Reveal delay={0.18} immediate>
              <div className="mt-9 flex flex-wrap items-center gap-3">
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
                  href="#pipeline"
                  variant="outline"
                  size="lg"
                  data-testid={LANDING.heroSecondaryCta}
                >
                  See how it works
                </ReactiveButton>
              </div>
            </Reveal>

            <Reveal delay={0.24} immediate>
              <p className="mt-8 max-w-md text-sm leading-relaxed text-slate-500">
                Built for Indian byelaws. FAR, setbacks, ground coverage and parking norms are
                configuration per municipal body, never hardcoded constants.
              </p>
            </Reveal>
          </div>

          {/* Hero drawing, drifting on scroll */}
          <motion.div style={{ y: plotY }} className="relative">
            <div className="rounded-md border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between border-b border-slate-200 pb-3">
                <span className="font-mono text-xs uppercase tracking-wider text-slate-500">
                  Site plan / stage 3
                </span>
                <span className="rounded-sm bg-emerald-50 px-2 py-0.5 font-mono text-xs text-emerald-700">
                  Contained
                </span>
              </div>
              <BlueprintPlot className="h-auto w-full" />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Metrics band */}
      <section className="border-y border-slate-200 bg-white" data-testid={LANDING.metrics}>
        <Stagger className="mx-auto grid max-w-6xl grid-cols-2 gap-px px-6 py-10 sm:grid-cols-4">
          {METRICS.map((m) => (
            <RevealItem key={m.label} className="px-2">
              <div className="font-mono text-4xl font-semibold tracking-tight text-slate-900">
                <CountUp value={m.value} suffix={m.suffix} data-testid={LANDING.metricValue} />
              </div>
              <div className="mt-1 text-sm text-slate-500">{m.label}</div>
            </RevealItem>
          ))}
          <RevealItem className="px-2">
            <div className="font-mono text-4xl font-semibold tracking-tight text-slate-900">INR</div>
            <div className="mt-1 text-sm text-slate-500">lakh and crore grouping</div>
          </RevealItem>
        </Stagger>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="scroll-mt-24 py-24" data-testid={LANDING.pipeline}>
        <div className="mx-auto max-w-6xl px-6">
          <Reveal y={0}>
            <SectionLabel>Layout pipeline</SectionLabel>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="mt-5 max-w-2xl text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Six stages, run in the order a site plan is drafted.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 max-w-2xl text-slate-600">
              The plot polygon is a hard constraint. No footprint, podium, amenity block or road may
              cross it, and containment is checked before any layout is returned.
            </p>
          </Reveal>

          <Stagger className="mt-14 grid gap-px border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE.map((step, i) => {
              const Icon = step.icon;
              return (
                <RevealItem key={step.title} data-testid={LANDING.pipelineStep}>
                  <div className="group h-full bg-white p-7 transition-colors duration-200 hover:bg-slate-50">
                    <div className="flex items-center justify-between">
                      <span className="grid h-10 w-10 place-items-center rounded-sm border border-slate-200 bg-slate-50 text-slate-700 transition-colors duration-200 group-hover:border-blue-200 group-hover:bg-blue-50 group-hover:text-blue-700">
                        <Icon className="h-5 w-5" />
                      </span>
                      <span className="font-mono text-xs text-slate-400">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <h3 className="mt-5 text-base font-semibold tracking-tight text-slate-900">
                      {step.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600">{step.body}</p>
                  </div>
                </RevealItem>
              );
            })}
          </Stagger>
        </div>
      </section>

      {/* Modules */}
      <section
        id="modules"
        className="scroll-mt-24 border-y border-slate-200 bg-white py-24"
        data-testid={LANDING.modules}
      >
        <div className="mx-auto max-w-6xl px-6">
          <Reveal y={0}>
            <SectionLabel>Engineering modules</SectionLabel>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="mt-5 max-w-2xl text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Every module answers to a code.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 max-w-2xl text-slate-600">
              Clause references travel with the result. Nothing returns a bare number.
            </p>
          </Reveal>

          <Stagger step={0.04} className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {MODULES.map((mod) => {
              const Icon = mod.icon;
              return (
                <RevealItem key={mod.name} data-testid={LANDING.moduleCard}>
                  <div className="group flex h-full items-start gap-4 rounded-md border border-slate-200 bg-white p-5 transition-[border-color,box-shadow,transform] duration-200 ease-out hover:border-blue-300 hover:shadow-sm motion-safe:hover:-translate-y-0.5">
                    <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-sm bg-slate-100 text-slate-600 transition-colors duration-200 group-hover:bg-blue-600 group-hover:text-white">
                      <Icon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold tracking-tight text-slate-900">
                        {mod.name}
                      </div>
                      <div className="mt-1 font-mono text-xs text-slate-500">{mod.code}</div>
                    </div>
                  </div>
                </RevealItem>
              );
            })}
          </Stagger>
        </div>
      </section>

      {/* Traceability */}
      <section id="traceability" className="scroll-mt-24 py-24" data-testid={LANDING.traceability}>
        <div className="mx-auto grid max-w-6xl items-center gap-14 px-6 lg:grid-cols-2">
          <div>
            <Reveal y={0}>
              <SectionLabel>Traceability</SectionLabel>
            </Reveal>
            <Reveal delay={0.05}>
              <h2 className="mt-5 text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
                Audit the number on screen.
              </h2>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-4 max-w-lg leading-relaxed text-slate-600">
                Each calculation screen shows the inputs it used, the formula it applied, the
                reference it came from and the result. Lengths in metres, areas in square metres,
                money in INR. Values round at display only, so nothing drifts internally.
              </p>
            </Reveal>

            <Stagger delay={0.16} className="mt-8 space-y-3">
              {[
                "Inputs and formula shown beside every result",
                "Reference carried through to the PDF report",
                "Full precision kept internally, rounded at display",
              ].map((line) => (
                <RevealItem key={line} className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  <span className="text-sm text-slate-700">{line}</span>
                </RevealItem>
              ))}
            </Stagger>
          </div>

          {/* Worked example. Marked as a sample so it is not read as a real project. */}
          <Reveal delay={0.1}>
            <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-5 py-3">
                <span className="flex items-center gap-2 text-sm font-semibold tracking-tight text-slate-900">
                  <FileText className="h-4 w-4 text-slate-500" />
                  Permitted built-up area
                </span>
                <span className="font-mono text-xs uppercase tracking-wider text-slate-400">
                  Sample
                </span>
              </div>

              <dl className="divide-y divide-slate-200">
                <div className="flex items-baseline justify-between px-5 py-3">
                  <dt className="text-sm text-slate-500">Plot area</dt>
                  <dd className="font-mono text-sm text-slate-900">4,000.00 m²</dd>
                </div>
                <div className="flex items-baseline justify-between px-5 py-3">
                  <dt className="text-sm text-slate-500">Permitted FAR</dt>
                  <dd className="font-mono text-sm text-slate-900">2.50</dd>
                </div>
                <div className="px-5 py-3">
                  <dt className="text-sm text-slate-500">Formula</dt>
                  <dd className="mt-1 rounded-sm bg-slate-50 px-3 py-2 font-mono text-sm text-slate-800">
                    Permitted BUA = Plot area × FAR
                  </dd>
                </div>
                <div className="px-5 py-3">
                  <dt className="text-sm text-slate-500">Reference</dt>
                  <dd className="mt-1 text-sm text-slate-700">
                    Local development control byelaw, configured per municipal body
                  </dd>
                </div>
              </dl>

              <div className="flex items-baseline justify-between border-t border-slate-200 bg-blue-50 px-5 py-4">
                <span className="text-sm font-semibold text-slate-900">Result</span>
                <span className="font-mono text-lg font-semibold tracking-tight text-blue-700">
                  10,000.00 m²
                </span>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Closing call to action */}
      <section className="bg-slate-900 py-20" data-testid={LANDING.cta}>
        <div className="mx-auto max-w-3xl px-6 text-center">
          <Reveal y={0}>
            <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Start with a plot boundary.
            </h2>
          </Reveal>
          <Reveal delay={0.06}>
            <p className="mx-auto mt-4 max-w-xl text-slate-300">
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

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-10" data-testid={LANDING.footer}>
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-6 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-sm bg-slate-900">
              <Ruler className="h-3.5 w-3.5 text-white" />
            </span>
            <span className="text-sm font-semibold tracking-tight text-slate-900">Aptimizer</span>
          </div>
          <p className="font-mono text-xs text-slate-500">
            Civil engineering and real estate planning. Built for Indian codes.
          </p>
        </div>
      </footer>
    </div>
  );
}
