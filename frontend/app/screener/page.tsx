"use client";
import { useState } from "react";
import Link from "next/link";
import { SlidersHorizontal, Search } from "lucide-react";
import { screenStocks } from "@/lib/api";
import { Card, CardHeader, Badge, Skeleton, ErrorState, Money, DisclaimerBar, Button, Input } from "@/components/ui";

interface ScreenerRow { ticker: string; name?: string; sector?: string; market_cap?: number; pe?: number; revenue_growth?: number; gross_margin?: number; warnings?: string[] }

const EXAMPLES = [
  "profitable tech stocks with P/E under 20",
  "healthcare companies with revenue growth over 15%",
  "undervalued dividend stocks with low debt",
  "small cap growth stocks in semiconductors",
];

export default function ScreenerPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ScreenerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ran, setRan] = useState(false);

  const run = async (q?: string) => {
    const text = (q ?? query).trim();
    if (!text) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const data = await screenStocks(text);
      const d = data as Record<string, unknown>;
      const raw = (d.data ?? d) as Record<string, unknown>;
      setResults((raw.results ?? raw.stocks ?? []) as ScreenerRow[]);
      setRan(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Screener failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Stock Screener</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Describe what you&apos;re looking for in plain English</p>
      </div>

      <Card>
        <form onSubmit={(e) => { e.preventDefault(); run(); }} className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <Input
                value={query}
                onChange={setQuery}
                placeholder="e.g. profitable tech stocks with P/E under 25…"
                className="pl-8"
              />
            </div>
            <Button type="submit" loading={loading}>
              <SlidersHorizontal size={14} />
              Screen
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => { setQuery(ex); run(ex); }}
                className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-zinc-400 hover:border-white/20 hover:text-white transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </form>
      </Card>

      {loading && <Card><Skeleton rows={6} /></Card>}
      {error && <ErrorState message={error} onRetry={() => run()} />}

      {!loading && ran && results.length === 0 && !error && (
        <Card><p className="text-sm text-zinc-500">No stocks matched your criteria.</p></Card>
      )}

      {!loading && results.length > 0 && (
        <Card>
          <CardHeader title={`${results.length} matches`} icon={<SlidersHorizontal size={14} />} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] text-zinc-500 border-b border-white/[0.08]">
                  <th className="pb-2 font-medium">Ticker</th>
                  <th className="pb-2 font-medium hidden md:table-cell">Sector</th>
                  <th className="pb-2 font-medium text-right">Mkt Cap</th>
                  <th className="pb-2 font-medium text-right">P/E</th>
                  <th className="pb-2 font-medium text-right hidden lg:table-cell">Rev Growth</th>
                  <th className="pb-2 font-medium text-right hidden lg:table-cell">Gross Margin</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {results.map((r) => (
                  <tr key={r.ticker} className="group hover:bg-white/[0.03] transition-colors">
                    <td className="py-2.5 pr-3">
                      <Link href={`/stock/${r.ticker}`} className="font-mono font-semibold text-white hover:text-brand-light transition-colors">
                        {r.ticker}
                      </Link>
                      {r.name && <div className="text-[10px] text-zinc-500 mt-0.5 truncate max-w-[140px]">{r.name}</div>}
                    </td>
                    <td className="py-2.5 hidden md:table-cell">
                      {r.sector && <Badge>{r.sector}</Badge>}
                    </td>
                    <td className="py-2.5 text-right font-mono"><Money value={r.market_cap} /></td>
                    <td className="py-2.5 text-right font-mono">{r.pe ? r.pe.toFixed(1) : "—"}</td>
                    <td className="py-2.5 text-right hidden lg:table-cell">
                      {r.revenue_growth != null ? `${(r.revenue_growth * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-2.5 text-right hidden lg:table-cell">
                      {r.gross_margin != null ? `${(r.gross_margin * 100).toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <DisclaimerBar />
        </Card>
      )}
    </div>
  );
}
