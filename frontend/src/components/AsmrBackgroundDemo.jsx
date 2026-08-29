import { ASMRBackground } from "@/components/ui/asmr-background";

/**
 * Demo for ASMRBackground: the overlay lives here rather than in the ui
 * component, so the background stays reusable with any content.
 */
const AsmrBackgroundDemo = () => {
  return (
    <ASMRBackground>
      <div className="flex h-full flex-col items-center justify-center pointer-events-none">
        <div className="rounded-sm border border-white/5 bg-white/[0.02] px-8 py-4 backdrop-blur-sm">
          <h2 className="text-sm font-light uppercase tracking-[0.7em] text-white/30 md:text-xl">
            Atmospheric Friction
          </h2>
          <div className="my-4 h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          <p className="text-center text-[10px] tracking-widest text-white/10">
            INTERACTIVE KINETIC ENVIRONMENT
          </p>
        </div>
      </div>
    </ASMRBackground>
  );
};

export default AsmrBackgroundDemo;
