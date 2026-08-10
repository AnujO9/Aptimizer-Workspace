import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const NumField = ({ label, value, onChange, suffix, step = 1, testid, disabled }) => (
  <div className="space-y-1">
    <Label className="text-[11px] uppercase tracking-wide text-slate-500">{label}</Label>
    <div className="relative">
      <Input
        type="number"
        step={step}
        disabled={disabled}
        data-testid={testid}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
        className="h-9 rounded-sm font-mono text-sm pr-12"
      />
      {suffix && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-slate-400 font-mono">
          {suffix}
        </span>
      )}
    </div>
  </div>
);

export const TextField = ({ label, value, onChange, testid, disabled, placeholder }) => (
  <div className="space-y-1">
    <Label className="text-[11px] uppercase tracking-wide text-slate-500">{label}</Label>
    <Input
      data-testid={testid}
      disabled={disabled}
      placeholder={placeholder}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 rounded-sm text-sm"
    />
  </div>
);

export const Metric = ({ label, value, unit, testid, tone }) => (
  <div className="border border-slate-200 bg-white rounded-sm px-3 py-2" data-testid={testid}>
    <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
    <div
      className={`font-mono text-lg leading-tight ${
        tone === "danger" ? "text-red-600" : tone === "success" ? "text-emerald-600" : "text-slate-900"
      }`}
    >
      {value}
      {unit && <span className="text-[11px] text-slate-400 ml-1">{unit}</span>}
    </div>
  </div>
);

export const Section = ({ title, actions, children, testid, description }) => (
  <section className="border border-slate-200 bg-white rounded-sm" data-testid={testid}>
    <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-slate-900">{title}</h3>
        {description && <p className="text-[11px] text-slate-500">{description}</p>}
      </div>
      <div className="flex items-center gap-2">{actions}</div>
    </header>
    <div className="p-4">{children}</div>
  </section>
);
