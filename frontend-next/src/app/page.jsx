'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchTrending, fetchMarketSnapshot, fmtPct } from '@/lib/api';

const PROMPTS = [
  'Is NVDA overvalued after the AI rally?',
  'Compare AAPL vs MSFT fundamentals',
  'What are the biggest risks for TSLA?',
  'Analyze FAANG portfolio concentration',
  'Is META a good value play right now?',
  'What does the macro environment mean for tech?',
];

export default function HomePage() {
  const router = useRouter();
  const [trending, setTrending] = useState([]);
  const [indices, setIndices] = useState([]);
  const [query, setQuery] = useState('');

  useEffect(() => {
    fetchTrending().then(setTrending).catch(() => {});
    fetchMarketSnapshot().then(setIndices).catch(() => {});
  }, []);

  function handleAsk(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    if (/^[A-Z]{1,5}$/.test(q)) {
      router.push(`/stock/${q}`);
    } else {
      router.push(`/stock/${q}`);
    }
    setQuery('');
  }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      {/* Hero search */}
      <div style={{ textAlign: 'center', paddingTop: 60, marginBottom: 48 }}>
        <h1 className="page-title" style={{ fontSize: 28, marginBottom: 8 }}>
          AI Equity Research
        </h1>
        <p className="page-subtitle" style={{ marginBottom: 24 }}>
          Ask anything about US stocks. Powered by multi-agent intelligence.
        </p>
        <form onSubmit={handleAsk} className="search-wrap" style={{ maxWidth: 560, margin: '0 auto' }}>
          <span className="search-icon">🔍</span>
          <input
            value={query}
            onChange={e => setQuery(e.target.value.toUpperCase())}
            placeholder="Enter a ticker — AAPL, NVDA, TSLA..."
            autoComplete="off"
            style={{ fontSize: 16, padding: '14px 16px 14px 44px', borderRadius: 14 }}
          />
        </form>
      </div>

      {/* Market snapshot */}
      {indices.length > 0 && (
        <div className="section-gap">
          <div className="card-title" style={{ marginBottom: 12 }}>US Markets</div>
          <div style={{ display: 'flex', gap: 12 }}>
            {indices.map(idx => (
              <div key={idx.name} className="card" style={{ flex: 1, padding: 16 }}>
                <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 4 }}>{idx.name}</div>
                <div style={{ fontSize: 18, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                  {idx.price?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <span className={`badge ${idx.changePct >= 0 ? 'badge-positive' : 'badge-negative'}`}>
                  {fmtPct(idx.changePct)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trending tickers */}
      <div className="section-gap">
        <div className="card-title" style={{ marginBottom: 12 }}>Trending</div>
        <div className="trending-strip">
          {(trending.length > 0 ? trending : ['AAPL','MSFT','NVDA','TSLA','META','AMZN','GOOGL','AMD'].map(t => ({ ticker: t, price: 0, changePct: 0 }))).map(t => (
            <div
              key={t.ticker}
              className="ticker-pill"
              onClick={() => router.push(`/stock/${t.ticker}`)}
            >
              <span className="symbol">{t.ticker}</span>
              {t.price > 0 && (
                <span className={`change ${t.changePct >= 0 ? 'badge-positive' : 'badge-negative'}`} style={{ background: 'none', padding: 0 }}>
                  {fmtPct(t.changePct)}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Suggested prompts */}
      <div className="section-gap">
        <div className="card-title" style={{ marginBottom: 12 }}>Research Ideas</div>
        <div className="prompts-grid">
          {PROMPTS.map((p, i) => (
            <button key={i} className="prompt-pill" onClick={() => {
              const match = p.match(/[A-Z]{2,5}/);
              if (match) router.push(`/stock/${match[0]}`);
            }}>
              {p}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
