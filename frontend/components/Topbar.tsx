"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Menu, Search, X } from "lucide-react";
import { searchStocks } from "@/lib/api";
import { SidebarContent } from "@/components/Sidebar";

export default function Topbar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ ticker: string; name: string }>>([]);
  const [open, setOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 1) { setResults([]); setOpen(false); return; }
    try {
      const data = await searchStocks(q);
      setResults((data.results ?? []).slice(0, 6));
      setOpen(true);
    } catch { setResults([]); }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(query), 250);
    return () => clearTimeout(t);
  }, [query, search]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pick = (ticker: string) => {
    setQuery("");
    setOpen(false);
    router.push(`/stock/${ticker}`);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-30 flex h-14 items-center gap-3 border-b border-white/10 bg-zinc-950/90 px-3 backdrop-blur lg:left-56 lg:px-4">
      <button
        type="button"
        onClick={() => setNavOpen(true)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-zinc-300 transition-colors hover:bg-white/5 hover:text-white lg:hidden"
        aria-label="Open navigation"
      >
        <Menu size={17} />
      </button>

      <div ref={ref} className="relative min-w-0 flex-1 max-w-2xl">
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-zinc-800/60 px-3 py-2">
          <Search size={14} className="text-zinc-500 shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search stocks — Apple, NVDA, BRK-B…"
            className="w-full bg-transparent text-sm text-white placeholder-zinc-500 outline-none"
          />
        </div>
        {open && results.length > 0 && (
          <div className="absolute top-full mt-1 w-full rounded-lg border border-white/10 bg-zinc-900 shadow-xl overflow-hidden z-50">
            {results.map((r) => (
              <button
                key={r.ticker}
                onClick={() => pick(r.ticker)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-white/5 transition-colors"
              >
                <span className="font-mono text-sm font-semibold text-white">{r.ticker}</span>
                <span className="text-sm text-zinc-400 truncate">{r.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {navOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            onClick={() => setNavOpen(false)}
            aria-label="Close navigation"
          />
          <aside className="relative flex h-full w-64 flex-col border-r border-white/10 bg-zinc-900 shadow-2xl">
            <button
              type="button"
              onClick={() => setNavOpen(false)}
              className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-white/5 hover:text-white"
              aria-label="Close navigation"
            >
              <X size={16} />
            </button>
            <SidebarContent onNavigate={() => setNavOpen(false)} />
          </aside>
        </div>
      )}
    </header>
  );
}
