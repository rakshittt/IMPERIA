"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { TrendingUp, TrendingDown, BarChart3, Newspaper } from "lucide-react";
import { getMarketSummary, getMarketMovers, getMarketBreadth } from "@/lib/api";
import { Card, CardHeader, Skeleton, ErrorState, PctChange, Money } from "@/components/ui";

interface IndexRow { name: string; ticker?: string; symbol?: string; price: number; change: number; change_pct: number }
interface MoverRow { ticker: string; price: number; change_pct: number }
interface BreadthData { advancing: number; declining: number; unchanged: number; total?: number }
interface NewsRow { title: string; url: string; source?: string; published_at?: string }

export default function HomePage() {
  const [indices, setIndices] = useState<IndexRow[]>([]);
  const [gainers, setGainers] = useState<MoverRow[]>([]);
  const [losers, setLosers] = useState<MoverRow[]>([]);
  const [breadth, setBreadth] = useState<BreadthData | null>(null);
  const [news, setNews] = useState<NewsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [summary, movers, breadthData] = await Promise.all([
          getMarketSummary(),
          getMarketMovers(5),
          getMarketBreadth(),
        ]);
        if (cancelled) return;
        const summaryObj = summary as Record<string, unknown>;
        setIndices((summaryObj.indices as IndexRow[]) ?? []);
        const moversObj = movers as Record<string, unknown>;
        setGainers((moversObj.gainers as MoverRow[]) ?? []);
        setLosers((moversObj.losers as MoverRow[]) ?? []);
        const b = breadthData as Record<string, unknown>;
        setBreadth({
          advancing: Number(b.advancing ?? 0),
          declining: Number(b.declining ?? 0),
          unchanged: Number(b.unchanged ?? 0),
          total: Number(b.total ?? 0),
        });
        const articles = (summaryObj.top_news ?? summaryObj.news ?? []) as NewsRow[];
        setNews(articles.slice(0, 8));
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load market data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [refreshKey]);

  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => {
          setError(null);
          setLoading(true);
          setRefreshKey((key) => key + 1);
        }}
      />
    );
  }

  const preferred = ["SPY", "QQQ", "DIA", "IWM"];
  const displayIndices = preferred
    .map((s) => indices.find((i) => i.ticker === s || i.symbol === s))
    .filter(Boolean) as IndexRow[];
  const indexCards = displayIndices.length > 0 ? displayIndices : indices.slice(0, 4);
  const total = Math.max((breadth?.advancing ?? 0) + (breadth?.declining ?? 0) + (breadth?.unchanged ?? 0), 1);
  const breadthPct = Math.round(((breadth?.advancing ?? 0) / total) * 100);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Market Overview</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Live snapshot from IMPERIA dataflows</p>
      </div>

      {/* Index cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}><Skeleton rows={3} /></Card>
            ))
          : indexCards.map((idx) => (
              <Card key={idx.symbol ?? idx.ticker}>
                <div className="text-xs text-zinc-500 mb-1">{idx.name}</div>
                <div className="text-xl font-bold font-mono">{idx.price?.toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
                <div className="mt-1 text-sm">
                  <PctChange value={idx.change_pct} />
                </div>
              </Card>
            ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Gainers */}
        <Card>
          <CardHeader title="Top Gainers" icon={<TrendingUp size={14} />} />
          {loading ? <Skeleton rows={5} /> : gainers.length === 0 ? (
            <p className="text-sm text-zinc-500">No data</p>
          ) : (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-white/5">
                {gainers.slice(0, 5).map((r) => (
                  <tr key={r.ticker} className="group">
                    <td className="py-2 pr-2">
                      <Link href={`/stock/${r.ticker}`} className="font-mono font-semibold text-white hover:text-brand-light transition-colors">
                        {r.ticker}
                      </Link>
                    </td>
                    <td className="py-2 text-right font-mono text-zinc-300">
                      <Money value={r.price} />
                    </td>
                    <td className="py-2 pl-2 text-right">
                      <PctChange value={r.change_pct} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* Losers */}
        <Card>
          <CardHeader title="Top Losers" icon={<TrendingDown size={14} />} />
          {loading ? <Skeleton rows={5} /> : losers.length === 0 ? (
            <p className="text-sm text-zinc-500">No data</p>
          ) : (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-white/5">
                {losers.slice(0, 5).map((r) => (
                  <tr key={r.ticker}>
                    <td className="py-2 pr-2">
                      <Link href={`/stock/${r.ticker}`} className="font-mono font-semibold text-white hover:text-brand-light transition-colors">
                        {r.ticker}
                      </Link>
                    </td>
                    <td className="py-2 text-right font-mono text-zinc-300">
                      <Money value={r.price} />
                    </td>
                    <td className="py-2 pl-2 text-right">
                      <PctChange value={r.change_pct} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* Breadth */}
        <Card>
          <CardHeader title="Market Breadth" icon={<BarChart3 size={14} />} />
          {loading ? <Skeleton rows={3} /> : breadth ? (
            <div className="space-y-3">
              <div className="h-2.5 rounded-full bg-zinc-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all"
                  style={{ width: `${breadthPct}%` }}
                />
              </div>
              <div className="grid grid-cols-3 text-center text-xs">
                <div><div className="text-emerald-400 font-semibold">{breadth.advancing.toLocaleString()}</div><div className="text-zinc-500">Advancing</div></div>
                <div><div className="text-zinc-400 font-semibold">{breadth.unchanged.toLocaleString()}</div><div className="text-zinc-500">Unchanged</div></div>
                <div><div className="text-red-400 font-semibold">{breadth.declining.toLocaleString()}</div><div className="text-zinc-500">Declining</div></div>
              </div>
              <div className="text-center text-[11px] text-zinc-600">{total.toLocaleString()} stocks tracked</div>
            </div>
          ) : <p className="text-sm text-zinc-500">No breadth data</p>}
        </Card>
      </div>

      {/* Market News */}
      <Card>
        <CardHeader title="Market News" icon={<Newspaper size={14} />} />
        {loading ? <Skeleton rows={6} /> : news.length === 0 ? (
          <p className="text-sm text-zinc-500">No news returned</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {news.map((article, i) => (
              <a
                key={i}
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col gap-1 rounded-lg border border-white/5 p-3 hover:border-white/10 hover:bg-white/[0.03] transition-colors"
              >
                <div className="text-sm font-medium text-zinc-200 group-hover:text-white line-clamp-2 transition-colors">
                  {article.title}
                </div>
                <div className="flex items-center gap-2 text-[10px] text-zinc-600">
                  {article.source && <span>{article.source}</span>}
                  {article.published_at && (
                    <span>{new Date(article.published_at).toLocaleDateString()}</span>
                  )}
                </div>
              </a>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
