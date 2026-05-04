'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function TopBar() {
  const router = useRouter();
  const [query, setQuery] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    // If it looks like a ticker (all caps, 1-5 chars), go to stock page
    if (/^[A-Z]{1,5}$/.test(q)) {
      router.push(`/stock/${q}`);
    } else {
      router.push(`/search?q=${encodeURIComponent(q)}`);
    }
    setQuery('');
  }

  return (
    <header className="topbar">
      <form className="search-wrap" onSubmit={handleSubmit}>
        <span className="search-icon">🔍</span>
        <input
          value={query}
          onChange={e => setQuery(e.target.value.toUpperCase())}
          placeholder="Ask anything about US stocks — try AAPL, NVDA, or a question"
          autoComplete="off"
        />
      </form>
      <div className="topbar-actions">
        <button className="btn" onClick={() => router.push('/portfolio')}>
          <span>📊</span> Deep Research
        </button>
      </div>
    </header>
  );
}
