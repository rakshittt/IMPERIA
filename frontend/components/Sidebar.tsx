"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Search,
  SlidersHorizontal,
  BrainCircuit,
  Scale,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";

export const NAV_ITEMS = [
  { href: "/", label: "Market", icon: Activity },
  { href: "/stock/AAPL", label: "Stock Research", icon: Search },
  { href: "/screener", label: "Screener", icon: SlidersHorizontal },
  { href: "/compare", label: "Compare", icon: Scale },
  { href: "/research", label: "Deep Research", icon: BrainCircuit },
  { href: "/ask", label: "Ask AI", icon: Sparkles },
];

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname();

  return (
    <>
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white font-bold text-sm">
          I
        </div>
        <div>
          <div className="text-sm font-semibold text-white">IMPERIA</div>
          <div className="text-[10px] text-zinc-500">US equity intelligence</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isStock = href.startsWith("/stock/");
          const active = isStock
            ? path.startsWith("/stock/")
            : href === "/"
            ? path === "/"
            : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={clsx(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand/20 text-brand-light"
                  : "text-zinc-400 hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 px-4 py-3 text-[10px] text-zinc-600">
        US equities &amp; major ETFs only.
        <br />
        Not investment advice.
      </div>
    </>
  );
}

export default function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-56 flex-col border-r border-white/10 bg-zinc-900 lg:flex">
      <SidebarContent />
    </aside>
  );
}
