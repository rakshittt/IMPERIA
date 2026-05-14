"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Scale, ArrowRight } from "lucide-react";
import { compareStocks } from "@/lib/api";
import { Card, CardHeader, Skeleton, ErrorState, Badge, DisclaimerBar, Button, Input, CitationList, WarningList } from "@/components/ui";

type MetricRow = {
  label: string;
  section: string;
  key: string;
  lowerIsBetter?: boolean;
  fmt?: (v: unknown) => string;
};

function formatPercent(value: unknown) {
  return value != null && Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : "—";
}

function formatNumber(value: unknown) {
  return value != null && Number.isFinite(Number(value)) ? Number(value).toFixed(1) : "—";
}

function normalizeCompareResult(data: Record<string, unknown>) {
  const payload = ((data.data ?? data) as Record<string, unknown>) ?? {};
  return {
    ...payload,
    citations: data.citations ?? payload.citations,
    warnings: data.warnings ?? payload.warnings,
  };
}

export default function ComparePage() {
  const [tickerA, setTickerA] = useState("AAPL");
  const [tickerB, setTickerB] = useState("MSFT");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!tickerA || !tickerB) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await compareStocks(tickerA.toUpperCase(), tickerB.toUpperCase());
      setResult(normalizeCompareResult(data));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await compareStocks("AAPL", "MSFT");
        if (!cancelled) setResult(normalizeCompareResult(data));
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Comparison failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const r = result ?? {};
  const left = String(r.ticker_a ?? tickerA).toUpperCase();
  const right = String(r.ticker_b ?? tickerB).toUpperCase();

  const metrics: MetricRow[] = [
    { label: "P/E Ratio", section: "valuation_comparison", key: "pe", lowerIsBetter: true, fmt: formatNumber },
    { label: "Forward P/E", section: "valuation_comparison", key: "forward_pe", lowerIsBetter: true, fmt: formatNumber },
    { label: "Revenue Growth", section: "growth_comparison", key: "revenue_growth", fmt: formatPercent },
    { label: "Gross Margin", section: "profitability_comparison", key: "gross_margin", fmt: formatPercent },
    { label: "Net Margin", section: "profitability_comparison", key: "net_margin", fmt: formatPercent },
    { label: "ROE", section: "profitability_comparison", key: "roe", fmt: formatPercent },
    { label: "Debt / Equity", section: "balance_sheet_comparison", key: "debt_to_equity", lowerIsBetter: true, fmt: formatNumber },
  ];

  const metricValue = (row: MetricRow, ticker: string) => {
    const section = (r[row.section] ?? {}) as Record<string, unknown>;
    const values = (section[row.key] ?? {}) as Record<string, unknown>;
    return values[ticker];
  };

  const sentiment = (r.sentiment_comparison ?? {}) as Record<string, unknown>;
  const risks = (r.risks ?? {}) as Record<string, unknown>;
  const citations = (r.citations ?? []) as Array<{ title?: string; url?: string; source_type?: string }>;
  const warnings = (r.warnings ?? []) as string[];

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compare Stocks</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Side-by-side fundamental and sentiment comparison</p>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[120px]">
            <label className="text-xs text-zinc-500 mb-1 block">Stock A</label>
            <Input value={tickerA} onChange={setTickerA} placeholder="AAPL" className="font-mono uppercase" />
          </div>
          <Scale size={18} className="text-zinc-600 mb-2" />
          <div className="flex-1 min-w-[120px]">
            <label className="text-xs text-zinc-500 mb-1 block">Stock B</label>
            <Input value={tickerB} onChange={setTickerB} placeholder="MSFT" className="font-mono uppercase" />
          </div>
          <Button onClick={run} loading={loading}>
            <ArrowRight size={14} />
            Compare
          </Button>
        </div>
      </Card>

      {loading && <Card><Skeleton rows={8} /></Card>}
      {error && <ErrorState message={error} onRetry={run} />}

      {!loading && result && (
        <>
          {/* Header comparison */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { t: String(r.ticker_a ?? tickerA), label: String(r.name_a ?? "") },
              { t: String(r.ticker_b ?? tickerB), label: String(r.name_b ?? "") },
            ].map(({ t, label }) => (
              <Card key={t} className="text-center">
                <Link href={`/stock/${t}`} className="text-2xl font-bold font-mono hover:text-brand-light transition-colors">{t}</Link>
                {label && <div className="text-xs text-zinc-500 mt-1">{label}</div>}
              </Card>
            ))}
          </div>

          {/* Metrics table */}
          <Card>
            <CardHeader title="Key Metrics" />
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] text-zinc-500 border-b border-white/[0.08]">
                  <th className="pb-2 font-medium text-left">Metric</th>
                  <th className="pb-2 font-medium text-right font-mono">{String(r.ticker_a ?? tickerA)}</th>
                  <th className="pb-2 font-medium text-right font-mono">{String(r.ticker_b ?? tickerB)}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {metrics.map((row) => {
                  const { label, lowerIsBetter, fmt } = row;
                  const vA = metricValue(row, left);
                  const vB = metricValue(row, right);
                  const fmtFn = fmt ?? ((v: unknown) => v != null ? String(v) : "—");
                  const aStr = fmtFn(vA);
                  const bStr = fmtFn(vB);
                  const numA = Number(vA);
                  const numB = Number(vB);
                  const comparable = Number.isFinite(numA) && Number.isFinite(numB);
                  const aWins = comparable && (lowerIsBetter ? numA < numB : numA > numB);
                  const bWins = comparable && (lowerIsBetter ? numB < numA : numB > numA);
                  return (
                    <tr key={label}>
                      <td className="py-2 text-zinc-400">{label}</td>
                      <td className={`py-2 text-right font-mono ${aWins ? "text-emerald-400 font-semibold" : ""}`}>{aStr}</td>
                      <td className={`py-2 text-right font-mono ${bWins ? "text-emerald-400 font-semibold" : ""}`}>{bStr}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          {/* Sentiment comparison */}
          {(sentiment[left] || sentiment[right]) && (
            <div className="grid grid-cols-2 gap-4">
              {[
                { t: left, label: String(sentiment[left] ?? "uncertain") },
                { t: right, label: String(sentiment[right] ?? "uncertain") },
              ].map(({ t, label }) => {
                return (
                  <Card key={t}>
                    <CardHeader title={`${t} Sentiment`} />
                    <div className="space-y-2">
                      <Badge variant={label === "bullish" ? "positive" : label === "bearish" ? "negative" : "default"}>
                        {label}
                      </Badge>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {Object.keys(risks).length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {[left, right].map((symbol) => {
                const items = (risks[symbol] ?? []) as string[];
                return (
                  <Card key={symbol}>
                    <CardHeader title={`${symbol} Risks`} />
                    {items.length === 0 ? (
                      <p className="text-sm text-zinc-500">No risks returned.</p>
                    ) : (
                      <ul className="space-y-2">
                        {items.slice(0, 4).map((item, i) => (
                          <li key={i} className="text-sm text-zinc-300">{item}</li>
                        ))}
                      </ul>
                    )}
                  </Card>
                );
              })}
            </div>
          )}

          {/* Summary */}
          {Boolean(r.summary) && (
            <Card>
              <CardHeader title="AI Summary" />
              <p className="text-sm text-zinc-300 leading-relaxed">{String(r.summary)}</p>
            </Card>
          )}

          <Card>
            <CardHeader title="Sources & Caveats" />
            <CitationList citations={citations} />
            <WarningList warnings={warnings} />
            <DisclaimerBar />
          </Card>
        </>
      )}
    </div>
  );
}
