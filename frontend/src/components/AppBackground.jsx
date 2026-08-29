import KineticGrid from "@/components/ui/kinetic-grid";

/**
 * AppBackground
 *
 * The single, app-wide instance of the kinetic grid. Mounted once in App so
 * it survives route changes (remounting would restart the animation, and
 * lose the resize/DPR setup, on every navigation) and sits behind all page
 * content.
 *
 * KineticGrid's own wrapper defaults to a normal-flow `min-h-screen` block
 * (right for the "wraps page content" demo usage) -- here there's no content
 * to wrap, so the overrides below take it out of document flow entirely:
 * fixed to the viewport, behind everything (-z-10), and never intercepting
 * clicks meant for real UI.
 */
const AppBackground = () => {
  return (
    <KineticGrid
      theme="light"
      className="fixed inset-0 -z-10 min-h-0 pointer-events-none"
    />
  );
};

export default AppBackground;
