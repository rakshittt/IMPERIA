'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

function getWatchlist() {
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem('ta_watchlist') || '[]'); } catch { return []; }
}

function saveWatchlist(list) {
  localStorage.setItem('ta_watchlist', JSON.stringify(list));
}

export default function WatchlistPage() {
  const router = useRouter();
  const [tickers, setTickers] = useState([]);
  const [input, setInput] = useState('');

  useEffect(() => { setTickers(getWatchlist()); }, []);

  function add() {
    const t = input.trim().toUpperCase();
    if (!t || tickers.includes(t)) return;
    const updated = [...tickers, t];
    setTickers(updated);
    saveWatchlist(updated);
    setInput('');
  }

  function remove(t) {
    const updated = tickers.filter(x => x !== t);
    setTickers(updated);
    saveWatchlist(updated);
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h1 className="page-title">Watchlist</h1>
      <p className="page-subtitle">Track US stocks you're researching.</p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase())}
          placeholder="Add ticker..."
          onKeyDown={e => e.key === 'Enter' && add()}
          style={{ flex: 1, background: 'var(--bg-tertiary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: 14, outline: 'none' }}
        />
        <button className="btn btn-accent" onClick={add}>Add</button>
      </div>

      {tickers.length === 0 ? (
        <div className="card" style={{ padding: 32, textAlign: 'center' }}>
          <p style={{ color: 'var(--text-tertiary)' }}>No tickers in your watchlist yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tickers.map(t => (
            <div key={t} className="card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontWeight: 600, cursor: 'pointer', color: 'var(--accent)' }}
                onClick={() => router.push(`/stock/${t}`)}>
                {t}
              </span>
              <span style={{ flex: 1 }} />
              <button className="btn" style={{ fontSize: 12 }} onClick={() => router.push(`/stock/${t}`)}>Research</button>
              <button className="btn-ghost" onClick={() => remove(t)} style={{ fontSize: 14 }}>✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
