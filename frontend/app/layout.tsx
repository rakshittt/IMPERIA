import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";

export const metadata: Metadata = {
  title: "IMPERIA — US Equity Intelligence",
  description: "Source-cited AI research for US stocks. Fast answers and deep multi-agent analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950">
        <Sidebar />
        <Topbar />
        <main className="mt-14 min-h-[calc(100vh-3.5rem)] p-4 lg:ml-56 lg:p-6">
          {children}
        </main>
      </body>
    </html>
  );
}
