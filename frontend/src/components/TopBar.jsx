import { Link, useNavigate } from "react-router-dom";
import { Ruler, LogOut, User, Shield, LayoutGrid } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";

export const TopBar = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="border-b border-slate-200 bg-white" data-testid="top-bar">
      <div className="flex items-center gap-4 px-5 h-14">
        <Link to="/projects" className="flex items-center gap-2" data-testid="brand-link">
          <div className="h-7 w-7 grid place-items-center bg-slate-900 rounded-sm">
            <Ruler className="h-4 w-4 text-white" />
          </div>
          <span className="font-semibold tracking-tight text-[15px]">
            Aptimizer<span className="text-blue-600">.</span>
          </span>
        </Link>
        <div className="flex-1 min-w-0">{children}</div>
        <nav className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="text-xs h-8" onClick={() => navigate("/projects")} data-testid="nav-projects">
            <LayoutGrid className="h-3.5 w-3.5 mr-1.5" /> Projects
          </Button>
          {user?.role === "admin" && (
            <Button variant="ghost" size="sm" className="text-xs h-8" onClick={() => navigate("/admin")} data-testid="nav-admin">
              <Shield className="h-3.5 w-3.5 mr-1.5" /> Users
            </Button>
          )}
          <Button variant="ghost" size="sm" className="text-xs h-8" onClick={() => navigate("/profile")} data-testid="nav-profile">
            <User className="h-3.5 w-3.5 mr-1.5" />
            {user?.name || "Profile"}
            <span className="ml-1.5 px-1.5 py-0.5 bg-slate-100 rounded-sm text-[10px] uppercase font-mono">
              {user?.role}
            </span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-xs h-8 rounded-sm"
            data-testid="logout-btn"
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
          >
            <LogOut className="h-3.5 w-3.5" />
          </Button>
        </nav>
      </div>
    </header>
  );
};
