'use client';
import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { fetchQuote, runResearch, fmtPrice, fmtPct, fmtNum } from '@/lib/api';

function AgentSection({ title, icon, color, content, defaultOpen }) {
  const [open, setOpen] = useState(!!defaultOpen);
  if (!content) return null;
  return (
    <div className="agent-section">
      <div className="agent-header" onClick={() => setOpen(!open)}>
        <div className="agent-icon" style={{ background: color + '18', color }}>{icon}</div>
        <div className="agent-name">{title}</div>
        <span className={`agent-chevron ${open ? 'open' : ''}`}>▶</span>
      </div>
      {open && <div className="agent-body" dangerouslySetInnerHTML={{ __html: mdToHtml(content) }} />}
    </div>
  );
}

function mdToHtml(md) {
  if (!md) return '';
  // Simple markdown → HTML (bold, headers, lists, tables, blockquotes)
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
  // Wrap consecutive <li> in <ul>
  html = html.replace(/((?:<li>.*<\/li><br>?)+)/g, '<ul>$1</ul>');
  return `<p>${html}</p>`;
}

export default function StockPage({ params }) {
  const { ticker } = use(params);
  const router = useRouter();
  const [quote, setQuote] = useState(null);
  const [research, setResearch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [quoteLoading, setQuoteLoading] = useState(true);

  useEffect(() => {
    setQuoteLoading(true);
    fetchQuote(ticker)
      .then(setQuote)
      .catch(() => setQuote({ ticker, name: ticker, price: null }))
      .finally(() => setQuoteLoading(false));
  }, [ticker]);

  async function handleResearch() {
    setLoading(true);
    try {
      const data = await runResearch(
        [{ ticker: ticker.toUpperCase(), weight: 1.0 }],
        { risk_tolerance: 'moderate', time_horizon: 'medium-term' }
      );
      setResearch(data);
    } catch (err) {
      alert('Research failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  const METRICS = quote ? [
    { label: 'Market Cap', value: fmtNum(quote.marketCap) },
    { label: 'P/E', value: quote.pe?.toFixed(1) ?? '—' },
    { label: 'Fwd P/E', value: quote.forwardPe?.toFixed(1) ?? '—' },
    { label: 'EPS', value: quote.eps ? `$${quote.eps.toFixed(2)}` : '—' },
    { label: 'Beta', value: quote.beta?.toFixed(2) ?? '—' },
    { label: 'Div Yield', value: quote.dividend ? fmtPct(quote.dividend * 100) : '—' },
    { label: '52w High', value: fmtPrice(quote.fiftyTwoWeekHigh) },
    { label: '52w Low', value: fmtPrice(quote.fiftyTwoWeekLow) },
    { label: 'Volume', value: fmtNum(quote.volume) },
    { label: 'Avg Volume', value: fmtNum(quote.avgVolume) },
  ] : [];

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      {/* Stock Header */}
      <div className="stock-header">
        <div className="stock-ticker">{ticker.toUpperCase()} · {quote?.exchange || ''}</div>
        <div className="stock-name">{quoteLoading ? '...' : quote?.name || ticker}</div>
        <div className="stock-meta">{quote?.sector}{quote?.industry ? ` · ${quote.industry}` : ''}</div>
        {quote?.price != null && (
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span className="stock-price">{fmtPrice(quote.price)}</span>
            <span className={`stock-change ${quote.changePct >= 0 ? '' : ''}`}
              style={{ color: quote.changePct >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
              {quote.change >= 0 ? '+' : ''}{quote.change?.toFixed(2)} ({fmtPct(quote.changePct)})
            </span>
          </div>
        )}
      </div>

      {/* Run Research CTA */}
      {!research && !loading && (
        <div className="section-gap" style={{ textAlign: 'center' }}>
          <div className="card" style={{ padding: 32 }}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 16, fontSize: 15 }}>
              Run deep multi-agent analysis on {ticker.toUpperCase()}
            </p>
            <button className="btn btn-accent" onClick={handleResearch} style={{ fontSize: 15, padding: '12px 28px' }}>
              ⚡ Generate AI Research
            </button>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 12, marginTop: 12 }}>
              5 analysts · Adversarial debate · Risk assessment · ~2-4 min
            </p>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="section-gap" style={{ textAlign: 'center' }}>
          <div className="card" style={{ padding: 40 }}>
            <div style={{ marginBottom: 16 }}>
              <div className="skeleton" style={{ width: 48, height: 48, borderRadius: '50%', margin: '0 auto 16px' }} />
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 8 }}>Agents are researching {ticker}...</p>
            <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>
              Market Analyst → Fundamentals → News → Sentiment → Macro → Bull/Bear Debate → Risk → Final Assessment
            </p>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      {METRICS.length > 0 && (
        <div className="section-gap">
          <div className="card-title" style={{ marginBottom: 12 }}>Key Metrics</div>
          <div className="metrics-grid">
            {METRICS.map(m => (
              <div key={m.label} className="metric-item">
                <div className="metric-label">{m.label}</div>
                <div className="metric-value">{m.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Research Results */}
      {research && (
        <>
          {/* AI Summary */}
          <div className="section-gap">
            <div className="ai-summary">
              <div className="ai-tag">✦ AI Research Summary</div>
              <div className="ai-text" dangerouslySetInnerHTML={{
                __html: mdToHtml(research.research_synthesis || research.final_portfolio_feedback || '')
              }} />
            </div>
          </div>

          {/* Bull / Bear */}
          {(research.bullish_research || research.bearish_research) && (
            <div className="section-gap">
              <div className="card-title" style={{ marginBottom: 12 }}>Investment Thesis</div>
              <div className="thesis-pair">
                <div className="thesis-card bull">
                  <div className="thesis-label">🟢 Bull Case</div>
                  <div className="thesis-body" dangerouslySetInnerHTML={{ __html: mdToHtml(research.bullish_research) }} />
                </div>
                <div className="thesis-card bear">
                  <div className="thesis-label">🔴 Bear Case</div>
                  <div className="thesis-body" dangerouslySetInnerHTML={{ __html: mdToHtml(research.bearish_research) }} />
                </div>
              </div>
            </div>
          )}

          {/* Agent Reports */}
          <div className="section-gap">
            <div className="card-title" style={{ marginBottom: 12 }}>Agent Research Trace</div>
            <AgentSection title="Portfolio Assessment" icon="👔" color="#20B2AA" content={research.final_portfolio_feedback} defaultOpen />
            <AgentSection title="Market & Technical Analysis" icon="📈" color="#4A9EF5" content={research.market_report} />
            <AgentSection title="Fundamentals Analysis" icon="📊" color="#22C55E" content={research.fundamentals_report} />
            <AgentSection title="News Intelligence" icon="📰" color="#F59E0B" content={research.news_report} />
            <AgentSection title="Sentiment & Social" icon="💬" color="#8B5CF6" content={research.sentiment_report} />
            <AgentSection title="Macro Environment" icon="🌍" color="#06B6D4" content={research.macro_report} />
            <AgentSection title="Trader Assessment" icon="⚡" color="#F97316" content={research.trader_report} />
            <AgentSection title="Risk Analysis (CRO)" icon="🛡️" color="#EF4444" content={research.risk_report} />
          </div>
        </>
      )}

      {/* Disclaimer */}
      {research && (
        <div style={{ padding: 16, fontSize: 11, color: 'var(--text-tertiary)', textAlign: 'center', marginTop: 24 }}>
          This analysis is AI-generated educational research. Not financial advice. Consult a qualified professional before making investment decisions.
        </div>
      )}
    </div>
  );
}
