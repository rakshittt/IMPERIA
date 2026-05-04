'use client';
import { usePathname, useRouter } from 'next/navigation';

const NAV = [
  { key: '/', icon: '🔍', label: 'Discover' },
  { key: '/portfolio', icon: '💼', label: 'Portfolio' },
  { key: '/watchlist', icon: '⭐', label: 'Watchlist' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand" onClick={() => router.push('/')} style={{ cursor: 'pointer' }}>
        <div className="logo">TA</div>
        <div>
          <div className="brand-text">TradingAgents</div>
          <div className="brand-sub">US Equity Research</div>
        </div>
      </div>
      <nav className="nav-section">
        <div className="nav-label">Research</div>
        {NAV.map(n => (
          <button
            key={n.key}
            className={`nav-item ${pathname === n.key ? 'active' : ''}`}
            onClick={() => router.push(n.key)}
          >
            <span style={{ fontSize: 16 }}>{n.icon}</span>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        <span className="status-dot" />
        <span>TradingAgents Engine v0.2.4</span>
      </div>
    </aside>
  );
}
