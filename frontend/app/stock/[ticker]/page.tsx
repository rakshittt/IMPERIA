"use client";
import { useEffect, useState, useCallback } from "react";
import type { ElementType } from "react";
import { useParams } from "next/navigation";
import {
  TrendingUp, TrendingDown, Newspaper, RadioTower,
  CalendarDays, FileText, Sparkles, ListChecks, AlertTriangle,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import {
  getStockQuote, getStockProfile, getStockChart, getStockNews,
  getStockSentiment, getStockEarnings, getFilingBrief, getInvestorChecklist,
  getRisks, getStockResearchSnapshot, askAI,
} from "@/lib/api";
import {
  Card, CardHeader, Skeleton, ErrorState, PctChange, Money, Badge,
  CitationList, WarningList, DisclaimerBar, Button, Input,
} from "@/components/ui";

type Tab = "overview" | "news" | "sentiment" | "earnings" | "filings" | "checklist" | "risks" | "ask";

const TABS: { id: Tab; label: string; icon: ElementType }[] = [
  { id: "overview", label: "Overview", icon: TrendingUp },
  { id: "news", label: "News", icon: Newspaper },
  { id: "sentiment", label: "Sentiment", icon: RadioTower },
  { id: "earnings", label: "Earnings", icon: CalendarDays },
  { id: "filings", label: "SEC Filings", icon: FileText },
  { id: "checklist", label: "Checklist", icon: ListChecks },
  { id: "risks", label: "Risks", icon: AlertTriangle },
  { id: "ask", label: "Ask AI", icon: Sparkles },
];

function formatDate(d: string) {
  try { return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }); }
  catch { return d; }
}

function asNumber(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export default function StockPage() {
  const params = useParams();
  const ticker = (params?.ticker as string ?? "AAPL").toUpperCase();
  const [tab, setTab] = useState<Tab>("overview");
  const [quote, setQuote] = useState<Record<string, unknown> | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [overviewData, setOverviewData] = useState<Record<string, unknown> | null>(null);
  const [chartData, setChartData] = useState<Array<{ date: string; close: number }>>([]);
  const [quoteLoading, setQuoteLoading] = useState(true);
  const [tabData, setTabData] = useState<Record<string, unknown> | null>(null);
  const [tabLoading, setTabLoading] = useState(false);
  const [tabError, setTabError] = useState<string | null>(null);
  const [askQuery, setAskQuery] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [answers, setAnswers] = useState<Array<{ q: string; a: string; citations?: unknown[] }>>([]);

  // Load quote + profile
  useEffect(() => {
    let cancelled = false;
    setQuoteLoading(true);
    setQuote(null);
    setProfile(null);
    setOverviewData(null);
    setChartData([]);
    (async () => {
      try {
        const [q, p, chart, snapshot] = await Promise.all([
          getStockQuote(ticker).catch(() => null),
          getStockProfile(ticker).catch(() => null),
          getStockChart(ticker, "3mo").catch(() => null),
          getStockResearchSnapshot(ticker).catch(() => null),
        ]);
        if (cancelled) return;
        setQuote(q);
        setProfile(p);
        setOverviewData(snapshot as Record<string, unknown> | null);
        const pts = (chart as Record<string, unknown>)?.points as Array<{ date: string; close: number }> ?? [];
        setChartData(pts.slice(-60));
      } finally {
        if (!cancelled) setQuoteLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [ticker]);

  const loadTab = useCallback(async (t: Tab) => {
    if (t === "ask" || t === "overview") return;
    setTabLoading(true);
    setTabError(null);
    setTabData(null);
    try {
      let data: Record<string, unknown> | null = null;
      if (t === "news") data = await getStockNews(ticker);
      else if (t === "sentiment") data = await getStockSentiment(ticker);
      else if (t === "earnings") data = await getStockEarnings(ticker);
      else if (t === "filings") data = await getFilingBrief(ticker);
      else if (t === "checklist") data = await getInvestorChecklist(ticker);
      else if (t === "risks") data = await getRisks(ticker);
      setTabData(data);
    } catch (e: unknown) {
      setTabError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setTabLoading(false);
    }
  }, [ticker]);

  useEffect(() => { loadTab(tab); }, [tab, loadTab]);

  const handleAsk = async () => {
    if (!askQuery.trim()) return;
    const q = askQuery.trim();
    setAskQuery("");
    setAskLoading(true);
    try {
      const res = await askAI(q, ticker);
      const r = res as Record<string, unknown>;
      setAnswers((prev) => [
        ...prev,
        { q, a: String(r.answer ?? r.data ?? "No answer returned."), citations: r.citations as unknown[] },
      ]);
    } catch (e: unknown) {
      setAnswers((prev) => [...prev, { q, a: `Error: ${e instanceof Error ? e.message : "Unknown"}` }]);
    } finally {
      setAskLoading(false);
    }
  };

  const quoteObj = (quote as Record<string, unknown>) ?? {};
  const profileObj = (profile as Record<string, unknown>) ?? {};
  const price = asNumber(quoteObj.price);
  const change = asNumber(quoteObj.change) ?? 0;
  const changePct = asNumber(quoteObj.change_pct ?? quoteObj.changePct) ?? 0;
  const marketCap = asNumber(quoteObj.market_cap ?? quoteObj.marketCap);

  return (
    <div className="max-w-5xl space-y-4">
      {/* Header / Quote */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono">{ticker}</h1>
            {Boolean(profileObj.sector) && (
              <Badge>{String(profileObj.sector)}</Badge>
            )}
          </div>
          <div className="text-sm text-zinc-400 mt-0.5">{String(profileObj.name ?? "")}</div>
        </div>
        {!quoteLoading && price != null && price > 0 && (
          <div className="text-right">
            <div className="text-3xl font-bold font-mono">${price.toFixed(2)}</div>
            <div className="text-sm mt-0.5 flex items-center justify-end gap-1">
              {changePct >= 0 ? <TrendingUp size={12} className="text-emerald-400" /> : <TrendingDown size={12} className="text-red-400" />}
              <PctChange value={changePct} />
              <span className="text-zinc-500">({change >= 0 ? "+" : ""}{change.toFixed(2)})</span>
            </div>
          </div>
        )}
        {quoteLoading && <Skeleton rows={2} className="w-40" />}
      </div>

      {/* Chart */}
      {chartData.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 12, right: 12, bottom: 4, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "#52525b" }}
                tickFormatter={formatDate}
                interval={Math.max(1, Math.floor(chartData.length / 5))}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#52525b" }}
                domain={["auto", "auto"]}
                tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#a1a1aa" }}
                formatter={(v: unknown) => [`$${Number(v).toFixed(2)}`, "Close"]}
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke={changePct >= 0 ? "#34d399" : "#f87171"}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Key stats */}
      {!quoteLoading && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {[
            ["Market Cap", <Money key="mc" value={marketCap} />],
            ["Volume", <span key="vol">{(asNumber(quoteObj.volume) ?? 0).toLocaleString()}</span>],
            ["P/E", <span key="pe">{quoteObj.pe ? Number(quoteObj.pe).toFixed(1) : "—"}</span>],
            ["52W High", <Money key="52h" value={asNumber(quoteObj.week_52_high)} />],
            ["52W Low", <Money key="52l" value={asNumber(quoteObj.week_52_low)} />],
            ["Exchange", <span key="ex" className="text-zinc-300">{String(profileObj.exchange ?? "—")}</span>],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-lg border border-white/[0.08] bg-zinc-900 px-3 py-2">
              <div className="text-[10px] text-zinc-500 mb-0.5">{label}</div>
              <div className="text-sm font-semibold">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-white/[0.08] pb-0">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 whitespace-nowrap px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? "border-brand text-white"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[200px]">
        {tab === "ask" ? (
          <AskPanel ticker={ticker} query={askQuery} setQuery={setAskQuery} loading={askLoading} answers={answers} onSubmit={handleAsk} />
        ) : tabLoading ? (
          <Card><Skeleton rows={6} /></Card>
        ) : tabError ? (
          <Card><ErrorState message={tabError} onRetry={() => loadTab(tab)} /></Card>
        ) : (
          <TabContent tab={tab} data={tab === "overview" ? overviewData : tabData} ticker={ticker} profile={profileObj} />
        )}
      </div>
    </div>
  );
}

function TabContent({
  tab,
  data,
  ticker,
  profile,
}: {
  tab: Tab;
  data: Record<string, unknown> | null;
  ticker: string;
  profile: Record<string, unknown>;
}) {
  const d = (data as Record<string, unknown>) ?? {};
  const raw = (d.data ?? d) as Record<string, unknown>;

  if (tab === "overview") {
    const summary = String(raw.what_happened_today ?? raw.answer ?? "");
    const fundamental = (raw.fundamental_snapshot ?? {}) as Record<string, unknown>;
    const metrics = (fundamental.metrics ?? {}) as Record<string, unknown>;
    const news = (raw.key_news ?? []) as Array<{ title?: string; url?: string; source?: string; published_at?: string }>;
    const risks = (raw.risks_to_watch ?? []) as string[];
    const stats = [
      ["Revenue Growth", metrics.revenue_growth != null ? `${(Number(metrics.revenue_growth) * 100).toFixed(1)}%` : "—"],
      ["Gross Margin", metrics.gross_margin != null ? `${(Number(metrics.gross_margin) * 100).toFixed(1)}%` : "—"],
      ["Net Margin", metrics.net_margin != null ? `${(Number(metrics.net_margin) * 100).toFixed(1)}%` : "—"],
      ["Debt / Equity", metrics.debt_to_equity != null ? Number(metrics.debt_to_equity).toFixed(1) : "—"],
    ];

    return (
      <div className="space-y-4">
        <Card>
          <CardHeader title="Research Snapshot" badge={raw.sentiment_label ? <Badge>{String(raw.sentiment_label)}</Badge> : undefined} />
          {summary ? (
            <p className="text-sm text-zinc-300 leading-relaxed">{summary}</p>
          ) : (
            <p className="text-sm text-zinc-500">Snapshot data is unavailable for {ticker}.</p>
          )}
          <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
          <WarningList warnings={d.warnings as string[]} />
          <DisclaimerBar />
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader title="Company Context" />
            <p className="text-sm text-zinc-300 leading-relaxed">
              {String(profile.description ?? raw.company_description ?? "No company description is available from the configured providers.")}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
              {stats.map(([label, value]) => (
                <div key={label} className="rounded-lg border border-white/[0.08] px-3 py-2">
                  <div className="text-[10px] text-zinc-500">{label}</div>
                  <div className="mt-0.5 font-mono font-semibold text-zinc-100">{value}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Watch Items" />
            {risks.length === 0 ? (
              <p className="text-sm text-zinc-500">No risk watchlist returned.</p>
            ) : (
              <ul className="space-y-2">
                {risks.slice(0, 4).map((risk, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                    <AlertTriangle size={12} className="mt-0.5 shrink-0 text-amber-500" />
                    {risk}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        {news.length > 0 && (
          <Card>
            <CardHeader title="Latest Signals" />
            <div className="grid gap-2 md:grid-cols-2">
              {news.slice(0, 4).map((item, i) => (
                <a
                  key={i}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-white/[0.08] p-3 transition-colors hover:border-white/15 hover:bg-white/[0.03]"
                >
                  <div className="line-clamp-2 text-sm font-medium text-zinc-200">{item.title}</div>
                  <div className="mt-1 text-[10px] text-zinc-600">
                    {[item.source, item.published_at ? new Date(item.published_at).toLocaleDateString() : null].filter(Boolean).join(" · ")}
                  </div>
                </a>
              ))}
            </div>
          </Card>
        )}
      </div>
    );
  }

  if (tab === "news") {
    const articles = (raw.articles ?? raw.news ?? []) as Array<{ title: string; url: string; source?: string; published_at?: string; snippet?: string }>;
    return (
      <div className="space-y-2">
        {articles.length === 0 ? (
          <Card><p className="text-sm text-zinc-500">No news returned.</p></Card>
        ) : articles.map((a, i) => (
          <Card key={i} className="hover:border-white/15 transition-colors">
            <a href={a.url} target="_blank" rel="noopener noreferrer" className="group">
              <div className="text-sm font-medium text-zinc-200 group-hover:text-white line-clamp-2">{a.title}</div>
              {a.snippet && <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{a.snippet}</p>}
              <div className="flex items-center gap-2 mt-1.5 text-[10px] text-zinc-600">
                {a.source && <span>{a.source}</span>}
                {a.published_at && <span>{new Date(a.published_at).toLocaleDateString()}</span>}
              </div>
            </a>
          </Card>
        ))}
        <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
      </div>
    );
  }

  if (tab === "sentiment") {
    const label = String(raw.sentiment_label ?? raw.research_sentiment ?? "uncertain");
    const score = Number(raw.confidence_score ?? 0);
    const summary = String(raw.summary ?? "");
    const labelColor = label === "bullish" ? "text-emerald-400" : label === "bearish" ? "text-red-400" : "text-zinc-400";
    return (
      <Card>
        <div className="flex items-center gap-3 mb-4">
          <span className={`text-2xl font-bold capitalize ${labelColor}`}>{label}</span>
          <Badge>{Math.round(score)}% confidence</Badge>
        </div>
        <div className="mb-3 h-2 rounded-full bg-zinc-800">
          <div className={`h-full rounded-full transition-all ${label === "bullish" ? "bg-emerald-500" : label === "bearish" ? "bg-red-500" : "bg-zinc-500"}`} style={{ width: `${Math.max(5, score)}%` }} />
        </div>
        {summary && <p className="text-sm text-zinc-300">{summary}</p>}
        <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
        <WarningList warnings={d.warnings as string[]} />
        <DisclaimerBar />
      </Card>
    );
  }

  if (tab === "earnings") {
    const next = (raw.next ?? raw.upcoming) as Record<string, unknown> ?? {};
    const history = (raw.history ?? []) as Array<{ report_date?: string; fiscal_period?: string; beat_miss?: string; eps_actual?: number; eps_estimate?: number }>;
    return (
      <div className="space-y-4">
        {Boolean(next.report_date) && (
          <Card>
            <CardHeader title="Next Earnings" badge={String(next.report_date)} />
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><div className="text-zinc-500 text-xs">EPS Est.</div><div className="font-semibold">{next.estimated_eps != null ? `$${Number(next.estimated_eps).toFixed(2)}` : "—"}</div></div>
              <div><div className="text-zinc-500 text-xs">Time</div><div className="font-semibold">{String(next.time_of_day ?? "—")}</div></div>
              <div><div className="text-zinc-500 text-xs">Quarter</div><div className="font-semibold">{String(next.fiscal_quarter ?? "—")}</div></div>
            </div>
          </Card>
        )}
        <Card>
          <CardHeader title="History" />
          {history.length === 0 ? <p className="text-sm text-zinc-500">No earnings history.</p> : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-[10px] text-zinc-500 border-b border-white/[0.08]">
                <th className="pb-1.5 font-medium">Period</th>
                <th className="pb-1.5 font-medium text-right">EPS Actual</th>
                <th className="pb-1.5 font-medium text-right">EPS Est.</th>
                <th className="pb-1.5 font-medium text-right">Result</th>
              </tr></thead>
              <tbody className="divide-y divide-white/5">
                {history.slice(0, 8).map((r, i) => (
                  <tr key={i}>
                    <td className="py-2 text-zinc-300">{r.fiscal_period ?? r.report_date}</td>
                    <td className="py-2 text-right font-mono">{r.eps_actual != null ? `$${r.eps_actual.toFixed(2)}` : "—"}</td>
                    <td className="py-2 text-right font-mono text-zinc-500">{r.eps_estimate != null ? `$${r.eps_estimate.toFixed(2)}` : "—"}</td>
                    <td className="py-2 text-right">
                      {r.beat_miss === "beat" ? <Badge variant="positive">Beat</Badge> : r.beat_miss === "miss" ? <Badge variant="negative">Miss</Badge> : <Badge>Inline</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    );
  }

  if (tab === "filings") {
    const filings = (raw.filings ?? raw.recent_filings ?? []) as Array<{ form?: string; filing_date?: string; url?: string; summary?: string }>;
    const summary = raw.executive_summary ?? raw.summary;
    return (
      <div className="space-y-4">
        {Boolean(summary) && (
          <Card><div className="text-sm text-zinc-300 leading-relaxed">{String(summary)}</div></Card>
        )}
        {filings.length > 0 && (
          <Card>
            <CardHeader title="Recent Filings" />
            <div className="space-y-2">
              {filings.slice(0, 8).map((f, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Badge>{f.form ?? "—"}</Badge>
                  <span className="text-xs text-zinc-400">{f.filing_date}</span>
                  {f.url && <a href={f.url} target="_blank" rel="noopener noreferrer" className="text-xs text-brand-light hover:underline ml-auto">View →</a>}
                </div>
              ))}
            </div>
          </Card>
        )}
        <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
        <DisclaimerBar />
      </div>
    );
  }

  if (tab === "checklist") {
    const groups: Array<[string, string[]]> = [
      ["Valuation", raw.valuation_checklist as string[]],
      ["Growth", raw.growth_checklist as string[]],
      ["Profitability", raw.profitability_checklist as string[]],
      ["Balance Sheet", raw.balance_sheet_checklist as string[]],
      ["Earnings", raw.earnings_checklist as string[]],
      ["Risks", raw.risk_checklist as string[]],
    ].filter(([, items]) => items?.length) as Array<[string, string[]]>;
    return (
      <Card>
        <CardHeader title="Investor Checklist" badge="not advice" />
        {groups.length === 0 ? <p className="text-sm text-zinc-500">No checklist data.</p> : (
          <div className="space-y-4">
            {groups.map(([name, items]) => (
              <div key={name}>
                <div className="text-xs font-semibold text-zinc-400 mb-1.5">{name}</div>
                <ul className="space-y-1">
                  {items.slice(0, 3).map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <span className="mt-0.5 text-zinc-600">›</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
        <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
        <DisclaimerBar />
      </Card>
    );
  }

  if (tab === "risks") {
    const risks = (raw.risks ?? []) as string[];
    const summary = raw.summary ?? raw.executive_summary;
    return (
      <Card>
        <CardHeader title="Risk Factors" />
        {Boolean(summary) && <p className="text-sm text-zinc-300 mb-3">{String(summary)}</p>}
        {risks.length === 0 ? <p className="text-sm text-zinc-500">No risks returned.</p> : (
          <ul className="space-y-2">
            {risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                <AlertTriangle size={12} className="text-amber-500 mt-0.5 shrink-0" />
                {r}
              </li>
            ))}
          </ul>
        )}
        <CitationList citations={d.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
        <DisclaimerBar />
      </Card>
    );
  }

  return null;
}

function AskPanel({ ticker, query, setQuery, loading, answers, onSubmit }: {
  ticker: string;
  query: string;
  setQuery: (v: string) => void;
  loading: boolean;
  answers: Array<{ q: string; a: string; citations?: unknown[] }>;
  onSubmit: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <form
          onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
          className="flex gap-2"
        >
          <Input
            value={query}
            onChange={setQuery}
            placeholder={`Ask anything about ${ticker} — earnings, risks, sentiment, valuation…`}
            className="flex-1"
          />
          <Button type="submit" loading={loading}>Ask</Button>
        </form>
      </Card>
      {answers.length > 0 && (
        <div className="space-y-3">
          {answers.map((item, i) => (
            <Card key={i}>
              <div className="text-xs text-zinc-500 mb-2">Q: {item.q}</div>
              <div className="prose-ai">{item.a}</div>
              <CitationList citations={item.citations as Array<{ title?: string; url?: string; source_type?: string }>} />
            </Card>
          ))}
        </div>
      )}
      <DisclaimerBar />
    </div>
  );
}
