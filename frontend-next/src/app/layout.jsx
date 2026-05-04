import './globals.css';
import Sidebar from '@/components/layout/Sidebar';
import TopBar from '@/components/layout/TopBar';

export const metadata = {
  title: 'TradingAgents — AI Equity Research',
  description: 'AI-native research terminal for US-listed equities and ETFs.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <Sidebar />
          <div className="main-area">
            <TopBar />
            <main className="content-scroll">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
