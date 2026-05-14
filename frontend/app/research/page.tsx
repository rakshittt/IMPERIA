"use client";
import { useState, useEffect, useRef } from "react";
import { BrainCircuit, CheckCircle, Loader, AlertCircle } from "lucide-react";
import { submitResearch, getResearch, streamResearch } from "@/lib/api";
import { Card, CardHeader, Badge, DisclaimerBar, Button, Input, CitationList } from "@/components/ui";

interface StreamEvent { event: string; agent?: string; message?: string; status?: string; warnings?: string[] }
interface AgentStep { agent: string; done: boolean; output?: string }

export default function ResearchPage() {
  const [ticker, setTicker] = useState("");
  const [question, setQuestion] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "queued" | "running" | "completed" | "failed">("idle");
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  const start = async () => {
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    cleanupRef.current?.();
    setLoading(true);
    setStatus("queued");
    setSteps([]);
    setResult(null);
    setError(null);
    try {
      const job = await submitResearch(t, question.trim() || undefined);
      setJobId(job.research_id);
      setStatus("running");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit");
      setStatus("failed");
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!jobId || status !== "running") return;
    const cleanup = streamResearch(
      jobId,
      (ev) => {
        try {
          const data: StreamEvent = JSON.parse(ev.data);
          if (data.event === "agent_completed" && data.agent) {
            setSteps((prev) => {
              const exists = prev.find((s) => s.agent === data.agent);
              if (exists) return prev.map((s) => s.agent === data.agent ? { ...s, done: true, output: data.message } : s);
              return [...prev, { agent: data.agent!, done: true, output: data.message }];
            });
          } else if (data.event === "agent_started" && data.agent) {
            setSteps((prev) => {
              if (prev.find((s) => s.agent === data.agent)) return prev;
              return [...prev, { agent: data.agent!, done: false }];
            });
          } else if (data.event === "completed" || data.status === "completed") {
            setStatus("completed");
            setLoading(false);
            getResearch(jobId).then((r) => setResult(r as Record<string, unknown>)).catch(() => {});
          } else if (data.event === "failed" || data.status === "failed") {
            setStatus("failed");
            setLoading(false);
            setError("Research job failed.");
          }
        } catch {}
      },
      () => {
        if (jobId) {
          getResearch(jobId).then((r) => {
            const job = r as Record<string, unknown>;
            if (job.status === "completed") { setStatus("completed"); setResult(job); }
            else if (job.status === "failed") { setStatus("failed"); setError(String(job.error ?? "Failed")); }
            setLoading(false);
          }).catch(() => setLoading(false));
        } else {
          setLoading(false);
        }
      },
    );
    cleanupRef.current = cleanup;
    return cleanup;
  }, [jobId, status]);

  const report = (result?.result ?? result) as Record<string, unknown> ?? {};
  const execSummary = String(report.executive_summary ?? report.summary ?? report.answer ?? "");
  const agentOutputs = (report.agent_outputs ?? {}) as Record<string, { summary?: string; warnings?: string[] }>;
  const citations = (result?.citations ?? report.citations ?? []) as Array<{ title?: string; url?: string; source_type?: string }>;
  const warnings = (result?.warnings ?? report.warnings ?? []) as string[];

  const AGENT_LABELS: Record<string, string> = {
    news_event: "News & Events", price_action: "Price Action", fundamentals: "Fundamentals",
    valuation: "Valuation", earnings: "Earnings", sec_filings: "SEC Filings",
    market_context: "Market Context", sentiment: "Sentiment", risk: "Risk Factors",
    insider_activity: "Insider Activity", research_factors: "Research Factors",
    balanced_thesis: "Bull/Bear Thesis", synthesizer: "Synthesis", evidence_auditor: "Evidence Audit",
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Deep Research</h1>
        <p className="text-sm text-zinc-500 mt-0.5">Multi-agent AI research with source citations</p>
      </div>

      <Card>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Ticker</label>
            <Input value={ticker} onChange={setTicker} placeholder="e.g. NVDA, AAPL, MSFT" className="font-mono uppercase w-40" />
          </div>
          <div>
            <label className="text-xs text-zinc-500 mb-1 block">Research question <span className="text-zinc-600">(optional)</span></label>
            <Input value={question} onChange={setQuestion} placeholder="e.g. What are the key risks for NVDA in 2025?" />
          </div>
          <Button onClick={start} loading={loading} disabled={!ticker.trim()}>
            <BrainCircuit size={14} />
            Run Deep Research
          </Button>
        </div>
      </Card>

      {/* Agent progress */}
      {(status === "running" || status === "queued" || steps.length > 0) && (
        <Card>
          <CardHeader
            title="Research Progress"
            badge={<Badge variant={status === "completed" ? "positive" : status === "failed" ? "negative" : "default"}>{status}</Badge>}
          />
          <div className="space-y-1.5">
            {status === "queued" && <div className="flex items-center gap-2 text-sm text-zinc-400"><Loader size={13} className="animate-spin" />Queued…</div>}
            {steps.map((step) => (
              <div key={step.agent} className="flex items-center gap-2 text-sm">
                {step.done
                  ? <CheckCircle size={13} className="text-emerald-400 shrink-0" />
                  : <Loader size={13} className="animate-spin text-brand-light shrink-0" />}
                <span className={step.done ? "text-zinc-300" : "text-zinc-400"}>
                  {AGENT_LABELS[step.agent] ?? step.agent}
                </span>
                {step.done && <CheckCircle size={10} className="text-emerald-400/50" />}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Error */}
      {status === "failed" && error && (
        <Card className="border-red-900/50">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle size={14} />
            <span className="text-sm">{error}</span>
          </div>
        </Card>
      )}

      {/* Result */}
      {status === "completed" && (
        <div className="space-y-4">
          <Card>
            <CardHeader title="Executive Summary" badge={<Badge variant="positive">Completed</Badge>} />
            <div className="prose-ai">{execSummary || "Research complete. See agent outputs below."}</div>
            {citations.length > 0 && <CitationList citations={citations} />}
            {warnings.map((w, i) => (
              <div key={i} className="mt-1 text-[11px] text-amber-500/80">{w}</div>
            ))}
            <DisclaimerBar />
          </Card>

          {/* Agent breakdown */}
          {Object.keys(agentOutputs).length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm text-zinc-400 hover:text-white transition-colors mb-3 list-none flex items-center gap-2">
                <span className="border border-white/10 rounded px-2 py-0.5">Show agent outputs ({Object.keys(agentOutputs).length})</span>
              </summary>
              <div className="space-y-3">
                {Object.entries(agentOutputs).map(([agent, output]) => (
                  <Card key={agent}>
                    <CardHeader title={AGENT_LABELS[agent] ?? agent} />
                    <p className="text-sm text-zinc-300 leading-relaxed">{output?.summary ?? "No summary."}</p>
                    {output?.warnings?.map((w, i) => (
                      <div key={i} className="mt-1 text-[11px] text-amber-500/80">{w}</div>
                    ))}
                  </Card>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
