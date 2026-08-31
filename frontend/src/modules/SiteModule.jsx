import PlotModule from "./PlotModule";
import DevControlsModule from "./DevControlsModule";

/** Plot geometry and the controls that govern it, on one page.
 *
 *  They were two menu entries that always had to be read together: the setbacks edited in
 *  the second are what the first builds its envelope from.
 */
export default function SiteModule(props) {
  return (
    <div className="space-y-4">
      <PlotModule {...props} goToModule={() => {
        document.getElementById("site-controls")?.scrollIntoView({ behavior: "smooth" });
      }} />
      <div id="site-controls" className="scroll-mt-24">
        <DevControlsModule {...props} />
      </div>
    </div>
  );
}
