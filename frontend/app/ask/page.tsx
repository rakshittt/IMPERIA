"use client";
import { useState, useRef, useEffect } from "react";
import { Sparkles, Send } from "lucide-react";
import { askAI } from "@/lib/api";
import { CitationList, DisclaimerBar } from "@/components/ui";
import clsx from "clsx";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ title?: string; url?: string; source_type?: string }>;
  ticker?: string;
  mode?: string;
}

const STARTERS = [
  "What happened to NVDA today?",
  "Is Apple overvalued right now?",
  "What are the biggest risks for Tesla?",
  "Compare AMD and Intel fundamentals",
  "What sectors are outperforming this week?",
];

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);
    try {
      const tickerMatch = q.match(/\b([A-Z]{2,5})\b/);
      const ticker = tickerMatch?.[1];
      const res = await askAI(q, ticker);
      const r = res as Record<string, unknown>;
      const answer = String(r.answer ?? r.data ?? "I couldn't find an answer right now.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: answer,
          citations: r.citations as Message["citations"],
          ticker: String(r.ticker ?? ticker ?? ""),
          mode: String(r.mode ?? ""),
        },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry, something went wrong: ${e instanceof Error ? e.message : "unknown error"}.` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] max-w-3xl">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles size={20} className="text-brand-light" />
          Ask IMPERIA
        </h1>
        <p className="text-sm text-zinc-500 mt-0.5">Ask anything about US stocks, markets, or earnings</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div className="text-zinc-600 text-sm">Try one of these to get started:</div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-left rounded-xl border border-white/[0.08] bg-zinc-900 px-4 py-3 text-sm text-zinc-300 hover:border-white/15 hover:text-white transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={clsx("flex", msg.role === "user" ? "justify-end" : "justify-start")}
          >
            <div
              className={clsx(
                "max-w-[85%] rounded-2xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-brand text-white rounded-br-md"
                  : "bg-zinc-900 border border-white/[0.08] text-zinc-200 rounded-bl-md",
              )}
            >
              <div className="prose-ai whitespace-pre-wrap">{msg.content}</div>
              {msg.role === "assistant" && msg.citations && (
                <CitationList citations={msg.citations} />
              )}
              {msg.role === "assistant" && msg.mode && (
                <div className="mt-2 text-[10px] text-zinc-600">mode: {msg.mode}</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-900 border border-white/[0.08] rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="mt-4 border-t border-white/[0.08] pt-4">
        <div className="flex gap-2 items-end rounded-2xl border border-white/10 bg-zinc-900 px-3 py-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about any stock, earnings, risk, or market trend…"
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-white placeholder-zinc-500 outline-none max-h-32 leading-relaxed"
            style={{ minHeight: "1.5rem" }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || loading}
            className="shrink-0 rounded-xl bg-brand p-2 text-white hover:bg-brand-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send size={14} />
          </button>
        </div>
        <DisclaimerBar />
      </div>
    </div>
  );
}
