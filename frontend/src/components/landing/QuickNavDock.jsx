import { Link } from "react-router-dom";
import { FileText, LayoutGrid, LogIn, Rocket, Sparkles, Workflow } from "lucide-react";
import { Dock, DockIcon, DockItem, DockLabel } from "../ui/dock";

const SECTION_ITEMS = [
  { title: "Pipeline", icon: Workflow, href: "#pipeline" },
  { title: "Modules", icon: LayoutGrid, href: "#modules" },
  { title: "Intelligence", icon: Sparkles, href: "#intelligence" },
  { title: "Traceability", icon: FileText, href: "#traceability" },
  { title: "Sign in", icon: LogIn, to: "/login" },
];

/**
 * Floating quick-nav dock, fixed to the bottom of the landing page.
 *
 * A deliberate exception to the site's own "restraint, not personality" rule
 * (see landing/Reveal.jsx) -- the Apple-style magnification is a flourish,
 * kept to this one playful shortcut. The primary nav stays the plain sticky
 * header it always was; this is a second, optional way to get around.
 */
export default function QuickNavDock({ workspaceHref, workspaceLabel }) {
  const items = [...SECTION_ITEMS, { title: workspaceLabel, icon: Rocket, to: workspaceHref }];

  return (
    <div
      className="fixed inset-x-0 bottom-6 z-30 hidden justify-center sm:flex"
      data-testid="landing-quick-nav-dock"
    >
      <Dock className="items-end pb-3">
        {items.map((item) => {
          const Icon = item.icon;
          const linkProps = item.to ? { to: item.to } : { href: item.href };
          return (
            <DockItem
              key={item.title}
              as={item.to ? Link : "a"}
              {...linkProps}
              className="aspect-square rounded-full bg-white shadow-sm ring-1 ring-slate-200 hover:ring-blue-300"
            >
              <DockLabel>{item.title}</DockLabel>
              <DockIcon>
                <Icon className="h-full w-full text-slate-600" />
              </DockIcon>
            </DockItem>
          );
        })}
      </Dock>
    </div>
  );
}
