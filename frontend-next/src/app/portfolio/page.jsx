'use client';
import { useState } from 'react';
import { runResearch } from '@/lib/api';

function mdToHtml(md) {
  if (!md) return '';
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
  html = html.replace(/((?:<li>.*<\/li><br>?)+)/g, '<ul>$1</ul>');
  return `<p>${html}</p>`;
}

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

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState([{ ticker: '', weight: '' }]);
  const [riskTolerance, setRiskTolerance] = useState('moderate');
  const [loading, setLoading] = useState(false);
  const [research, setResearch] = useState(null);

  function addRow() {
    setHoldings([...holdings, { ticker: '', weight: '' }]);
  }

  function updateRow(i, field, val) {
    const copy = [...holdings];
    copy[i] = { ...copy[i], [field]: val };
    setHoldings(copy);
  }

  function removeRow(i) {
    setHoldings(holdings.filter((_, j) => j !== i));
  }

  async function handleAnalyze() {
    const portfolio = holdings
      .filter(h => h.ticker.trim())
      .map(h => ({
        ticker: h.ticker.trim().toUpperCase(),
        weight: parseFloat(h.weight) || 1,
      }));
    if (!portfolio.length) return;

    // Normalize weights
    const total = portfolio.reduce((s, h) => s + h.weight, 0);
    portfolio.forEach(h => (h.weight = h.weight / total));

    setLoading(true);
    try {
      const data = await runResearch(portfolio, { risk_tolerance: riskTolerance, time_horizon: 'medium-term' });
      setResearch(data);
    } catch (err) {
      alert('Analysis failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto' }}>
      <h1 className="page-title">Portfolio Research</h1>
      <p className="page-subtitle">Enter your US equity holdings for deep multi-agent analysis.</p>

      {/* Holdings input */}
      <div className="card section-gap" style={{ padding: 24 }}>
        <div className="card-title" style={{ marginBottom: 16 }}>Holdings</div>
        {holdings.map((h, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'center' }}>
            <input
              style={{ flex: 2, background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: 14, outline: 'none' }}
              placeholder="Ticker (e.g. AAPL)"
              value={h.ticker}
              onChange={e => updateRow(i, 'ticker', e.target.value.toUpperCase())}
            />
            <input
              style={{ flex: 1, background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: 14, outline: 'none' }}
              placeholder="Weight"
              type="number"
              step="0.1"
              min="0"
              value={h.weight}
              onChange={e => updateRow(i, 'weight', e.target.value)}
            />
            {holdings.length > 1 && (
              <button className="btn-ghost" onClick={() => removeRow(i)} style={{ fontSize: 16 }}>✕</button>
            )}
          </div>
        ))}
        <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
          <button className="btn" onClick={addRow}>+ Add Holding</button>
          <select
            value={riskTolerance}
            onChange={e => setRiskTolerance(e.target.value)}
            style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: 13 }}
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
          <button className="btn btn-accent" onClick={handleAnalyze} disabled={loading} style={{ marginLeft: 'auto' }}>
            {loading ? 'Analyzing...' : '⚡ Run Deep Research'}
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card section-gap" style={{ padding: 40, textAlign: 'center' }}>
          <div className="skeleton" style={{ width: 48, height: 48, borderRadius: '50%', margin: '0 auto 16px' }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: 15 }}>Running multi-agent research pipeline...</p>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginTop: 8 }}>This typically takes 2-4 minutes.</p>
        </div>
      )}

      {/* Results */}
      {research && (
        <>
          <div className="section-gap">
            <div className="ai-summary">
              <div className="ai-tag">✦ Portfolio Assessment</div>
              <div className="ai-text" dangerouslySetInnerHTML={{ __html: mdToHtml(research.final_portfolio_feedback) }} />
            </div>
          </div>

          {(research.bullish_research || research.bearish_research) && (
            <div className="section-gap">
              <div className="card-title" style={{ marginBottom: 12 }}>Portfolio Thesis</div>
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

          <div className="section-gap">
            <div className="card-title" style={{ marginBottom: 12 }}>Research Trace</div>
            <AgentSection title="Research Synthesis" icon="🧠" color="#20B2AA" content={research.research_synthesis} defaultOpen />
            <AgentSection title="Market & Technical" icon="📈" color="#4A9EF5" content={research.market_report} />
            <AgentSection title="Fundamentals" icon="📊" color="#22C55E" content={research.fundamentals_report} />
            <AgentSection title="News" icon="📰" color="#F59E0B" content={research.news_report} />
            <AgentSection title="Sentiment" icon="💬" color="#8B5CF6" content={research.sentiment_report} />
            <AgentSection title="Macro" icon="🌍" color="#06B6D4" content={research.macro_report} />
            <AgentSection title="Trader" icon="⚡" color="#F97316" content={research.trader_report} />
            <AgentSection title="Risk (CRO)" icon="🛡️" color="#EF4444" content={research.risk_report} />
          </div>
        </>
      )}
    </div>
  );
}
