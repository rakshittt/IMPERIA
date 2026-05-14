"use client";
import { ReactNode } from "react";
import clsx from "clsx";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx("rounded-lg border border-white/[0.08] bg-zinc-900 p-4", className)}>
      {children}
    </div>
  );
}

export function CardHeader({ title, badge, icon }: { title: string; badge?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2 text-sm font-medium text-white">
        {icon && <span className="text-zinc-400">{icon}</span>}
        {title}
      </div>
      {badge && <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">{badge}</span>}
    </div>
  );
}

export function Skeleton({ rows = 3, className }: { rows?: number; className?: string }) {
  return (
    <div className={clsx("space-y-2 animate-pulse", className)}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 rounded bg-zinc-800" style={{ width: `${60 + (i * 13) % 40}%` }} />
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 text-center">
      <div className="text-sm text-zinc-400">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md border border-white/10 px-3 py-1.5 text-xs text-zinc-400 hover:bg-white/5 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-8 text-center">
      <div className="text-sm text-zinc-400">{message}</div>
      {hint && <div className="text-xs text-zinc-600">{hint}</div>}
    </div>
  );
}

export function Badge({ children, variant = "default" }: { children: ReactNode; variant?: "default" | "positive" | "negative" | "gold" }) {
  return (
    <span
      className={clsx("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium", {
        "bg-zinc-800 text-zinc-400": variant === "default",
        "bg-emerald-900/50 text-emerald-400": variant === "positive",
        "bg-red-900/50 text-red-400": variant === "negative",
        "bg-amber-900/50 text-amber-400": variant === "gold",
      })}
    >
      {children}
    </span>
  );
}

export function PctChange({ value }: { value?: number | null }) {
  if (value == null) return <span className="text-zinc-500">—</span>;
  const pos = value >= 0;
  return (
    <span className={pos ? "text-emerald-400" : "text-red-400"}>
      {pos ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

export function Money({ value, decimals = 2 }: { value?: number | null; decimals?: number }) {
  if (value == null || isNaN(value)) return <span className="text-zinc-500">—</span>;
  if (Math.abs(value) >= 1e12) return <span>${(value / 1e12).toFixed(1)}T</span>;
  if (Math.abs(value) >= 1e9) return <span>${(value / 1e9).toFixed(1)}B</span>;
  if (Math.abs(value) >= 1e6) return <span>${(value / 1e6).toFixed(1)}M</span>;
  return <span>${value.toFixed(decimals)}</span>;
}

export function Num({ value, suffix = "" }: { value?: number | null; suffix?: string }) {
  if (value == null || isNaN(value)) return <span className="text-zinc-500">—</span>;
  return <span>{value.toFixed(2)}{suffix}</span>;
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-lg font-semibold text-white mb-4">{children}</h2>;
}

export function Button({
  onClick,
  children,
  loading,
  variant = "primary",
  type = "button",
  disabled,
}: {
  onClick?: () => void;
  children: ReactNode;
  loading?: boolean;
  variant?: "primary" | "ghost";
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading || disabled}
      className={clsx(
        "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
        variant === "primary"
          ? "bg-brand text-white hover:bg-brand-dark"
          : "border border-white/10 text-zinc-400 hover:bg-white/5 hover:text-white",
      )}
    >
      {loading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
      )}
      {children}
    </button>
  );
}

export function Input({ value, onChange, placeholder, className }: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={clsx(
        "w-full rounded-lg border border-white/10 bg-zinc-800 px-3 py-2 text-sm text-white placeholder-zinc-500 outline-none focus:border-brand/50",
        className,
      )}
    />
  );
}

export function CitationList({ citations }: { citations?: Array<{ title?: string; url?: string; source_type?: string }> }) {
  if (!citations?.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {citations.slice(0, 6).map((c, i) => (
        c.url ? (
          <a
            key={i}
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-zinc-500 hover:text-zinc-300 hover:border-white/20 transition-colors max-w-[180px] truncate"
            title={c.title}
          >
            {c.title ?? c.source_type ?? "Source"}
          </a>
        ) : (
          <span key={i} className="rounded border border-white/10 px-2 py-0.5 text-[10px] text-zinc-600 max-w-[180px] truncate">
            {c.title ?? c.source_type}
          </span>
        )
      ))}
    </div>
  );
}

export function WarningList({ warnings }: { warnings?: string[] }) {
  if (!warnings?.length) return null;
  return (
    <div className="mt-2 space-y-1">
      {warnings.map((w, i) => (
        <div key={i} className="text-[11px] text-amber-500/80">{w}</div>
      ))}
    </div>
  );
}

export function DisclaimerBar() {
  return (
    <div className="mt-4 text-[10px] text-zinc-600 border-t border-white/5 pt-3">
      For educational and research purposes only. Not investment advice.
    </div>
  );
}
