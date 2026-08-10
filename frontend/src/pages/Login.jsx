import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Ruler, ArrowRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      toast.success("Signed in");
      navigate("/projects");
    } catch (err) {
      setError(apiError(err.response?.data?.detail, err.message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_0.9fr]">
      <div className="hidden lg:block relative bg-slate-900">
        <img
          src="https://images.pexels.com/photos/4134179/pexels-photo-4134179.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="Architectural blueprints"
          className="absolute inset-0 h-full w-full object-cover opacity-35"
        />
        <div className="relative h-full flex flex-col justify-between p-12">
          <div className="flex items-center gap-2 text-white">
            <div className="h-8 w-8 grid place-items-center bg-blue-600 rounded-sm">
              <Ruler className="h-4 w-4" />
            </div>
            <span className="font-semibold tracking-tight text-lg">Aptimizer</span>
          </div>
          <div className="max-w-lg">
            <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-white leading-[1.05]">
              Plot to BOQ.
              <br />
              <span className="text-blue-400">One calculation chain.</span>
            </h1>
            <p className="mt-5 text-slate-300 text-base max-w-md">
              Apartment planning, area statements, FAR/FSI compliance, quantity take-off, cost estimation and reports —
              live from a single project model.
            </p>
            <div className="mt-10 grid grid-cols-3 gap-px bg-white/15 border border-white/15">
              {[
                ["FAR / FSI", "auto-computed"],
                ["BOQ", "PDF + Excel"],
                ["Compliance", "editable rules"],
              ].map(([k, v]) => (
                <div key={k} className="bg-slate-900/80 px-4 py-3">
                  <div className="font-mono text-sm text-white">{k}</div>
                  <div className="text-[11px] text-slate-400">{v}</div>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">CIVIL ENGINEERING PLANNING PLATFORM</p>
        </div>
      </div>

      <div className="flex items-center justify-center p-8 bg-white">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5" data-testid="login-form">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
            <p className="text-sm text-slate-500 mt-1">Access your projects and calculations.</p>
          </div>
          {error && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-sm px-3 py-2" data-testid="login-error">
              {error}
            </div>
          )}
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wide text-slate-500">Email</Label>
            <Input
              data-testid="login-email-input"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-sm"
              placeholder="admin@aptimizer.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wide text-slate-500">Password</Label>
            <Input
              data-testid="login-password-input"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-sm"
            />
          </div>
          <Button type="submit" disabled={busy} data-testid="login-submit-button" className="w-full rounded-sm">
            {busy ? "Signing in…" : "Sign in"}
            <ArrowRight className="h-4 w-4 ml-1.5" />
          </Button>
          <p className="text-sm text-slate-500">
            No account?{" "}
            <Link to="/register" className="text-blue-600 hover:underline" data-testid="go-register-link">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
