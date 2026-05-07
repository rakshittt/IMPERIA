"""Runtime for the IMPERIA stock-first expert-agent graph."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from tradingagents.dataflows import earnings_data, market_data, news_aggregator
from tradingagents.dataflows.analyst_consensus import get_analyst_consensus
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.dataflows.form4_parser import get_form4_activity
from tradingagents.dataflows.fred_macro import get_macro_indicators
from tradingagents.dataflows.institutional_holders import get_institutional_holder_analysis
from tradingagents.dataflows.peer_comparison import get_peer_comparison
from tradingagents.dataflows.polymarket_sentiment import get_polymarket_sentiment
from tradingagents.dataflows.sec_edgar import get_sec_filings
from tradingagents.dataflows.thirteen_f_parser import get_thirteen_f_activity
from tradingagents.engine.stock_sentiment import get_stock_sentiment
from tradingagents.expert_agents.agents import AGENT_FUNCTIONS
from tradingagents.expert_agents.cache import AgentOutputCache, agent_cache_ttl
from tradingagents.expert_agents.planner import plan_query, selected_agents_for_intent
from tradingagents.expert_agents.prompts import AGENT_PROMPTS, UNIVERSAL_SYSTEM_PROMPT
from tradingagents.persistence.usage import record_agent_run
from tradingagents.schemas.agent_output import ExpertGraphResult
from tradingagents.utils.deepseek import deepseek_text
from tradingagents.utils.safety import find_forbidden_phrases
from tradingagents.utils.validation import normalize_ticker

logger = logging.getLogger(__name__)


def _news_window(router_window: str) -> str:
    return {
        "today": "today",
        "intraday": "today",
        "this_week": "past_week",
        "this_month": "past_month",
        "long_term": "past_month",
    }.get(router_window, "today")


def _citation(source_type: str, provider: str, title: str, ticker: str, url: str | None = None, cid: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "id": cid or f"c_{source_type}_{ticker.lower()}_{abs(hash((provider, title, url))) % 100000}",
        "citation_id": cid or f"c_{source_type}_{ticker.lower()}_{abs(hash((provider, title, url))) % 100000}",
        "source_type": source_type,
        "provider": provider,
        "title": title,
        "url": url,
        "ticker": ticker,
        **{key: value for key, value in extra.items() if value is not None},
    }


class ExpertAgentRuntime:
    """Evidence-first expert-agent runtime for fast and deep stock research."""

    def __init__(self) -> None:
        self.cache = AgentOutputCache()

    @staticmethod
    def _deepseek_enabled() -> bool:
        key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        return bool(key and key.lower() not in {"placeholder", "dummy", "test", "changeme"})

    @staticmethod
    def _compact_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
        """Keep DeepSeek prompts bounded and evidence-only."""

        return {
            "ticker": bundle.get("ticker"),
            "company_name": bundle.get("company_name"),
            "intent": bundle.get("intent"),
            "window": bundle.get("window"),
            "quote": bundle.get("quote"),
            "news": bundle.get("news", [])[:8],
            "metrics": bundle.get("metrics"),
            "filings": bundle.get("filings", [])[:5],
            "earnings": bundle.get("earnings"),
            "macro": bundle.get("macro"),
            "peers": bundle.get("peers", {}).get("peers", [])[:5],
            "sentiment": bundle.get("sentiment"),
            "polymarket": bundle.get("polymarket"),
            "analyst_consensus": bundle.get("analyst_consensus"),
            "form4": bundle.get("form4"),
            "thirteen_f": bundle.get("thirteen_f"),
            "institutional_holders": bundle.get("institutional_holders"),
            "citations": bundle.get("citations", [])[:30],
            "warnings": bundle.get("warnings", [])[:20],
        }

    def _refine_with_deepseek(
        self,
        agent_name: str,
        deterministic: dict[str, Any],
        bundle: dict[str, Any],
        upstream: dict[str, dict[str, Any]],
        *,
        mode: str,
        research_id: str | None = None,
    ) -> dict[str, Any]:
        if not self._deepseek_enabled() or agent_name == "evidence_auditor":
            return deterministic
        system = f"{UNIVERSAL_SYSTEM_PROMPT}\n\n{AGENT_PROMPTS.get(agent_name, '')}"
        compact = {
            "data_bundle": self._compact_bundle(bundle),
            "upstream_agent_outputs": {name: {"summary": row.get("summary"), "key_findings": row.get("key_findings", [])[:5], "warnings": row.get("warnings", [])[:5]} for name, row in upstream.items()},
            "deterministic_seed_output": deterministic,
            "required_base_fields": list(deterministic.keys()),
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": "Return a single JSON object. Use only this DATA BUNDLE:\n" + json.dumps(compact, default=str, separators=(",", ":"))},
        ]
        for attempt in range(2):
            text = deepseek_text(
                messages,
                mode="deep" if mode == "deep" else "fast",
                temperature=0.1,
                max_tokens=1600,
                agent_name=agent_name,
                ticker=bundle.get("ticker"),
                intent=bundle.get("intent"),
                research_id=research_id,
            )
            if not text:
                return {**deterministic, "warnings": deterministic.get("warnings", []) + ["DeepSeek unavailable; deterministic agent output used."]}
            try:
                candidate = json.loads(text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
            except json.JSONDecodeError:
                messages.append({"role": "user", "content": "The previous output was invalid JSON. Re-emit valid JSON only with no markdown."})
                continue
            required = set(deterministic) & {
                "agent_name",
                "ticker",
                "company_name",
                "task",
                "summary",
                "key_findings",
                "positive_signals",
                "negative_signals",
                "uncertainties",
                "confidence_score",
                "citations",
                "warnings",
                "not_investment_advice",
                "generated_at",
                "data_freshness",
            }
            if not required.issubset(candidate) or candidate.get("not_investment_advice") is not True:
                messages.append({"role": "user", "content": "The previous output failed the universal schema. Re-emit all required base fields exactly."})
                continue
            violations = find_forbidden_phrases(json.dumps(candidate, default=str))
            if violations:
                return {**deterministic, "warnings": deterministic.get("warnings", []) + ["DeepSeek output failed safety validation; deterministic agent output used."]}
            return candidate
        return {**deterministic, "warnings": deterministic.get("warnings", []) + ["DeepSeek JSON validation failed; deterministic agent output used."]}

    def assemble_evidence_bundle(self, ticker: str, *, query: str, intent: str, window: str) -> dict[str, Any]:
        symbol = normalize_ticker(ticker)
        news_window = _news_window(window)
        warnings: list[str] = []
        citations: list[dict[str, Any]] = []
        providers: list[str] = []
        metadata: list[dict[str, Any]] = []

        def mark(source: str, status: str, *, count: int = 0, error: str | None = None) -> None:
            metadata.append({"source": source, "status": status, "items_count": count, "error_message": error})

        quote = {}
        try:
            quote_model = market_data.get_quote(symbol)
            quote = quote_model.model_dump()
            providers.append(quote_model.source)
            warnings.extend(quote_model.warnings)
            citations.append(_citation("market_data", quote_model.source, f"{symbol} quote", symbol, f"https://finance.yahoo.com/quote/{symbol}", "c_yf_quote_" + symbol.lower()))
            mark("yfinance", "ok", count=1)
        except Exception as exc:
            warnings.append(f"Quote data unavailable ({type(exc).__name__}).")
            mark("yfinance", "failed", error=type(exc).__name__)

        news: list[dict[str, Any]] = []
        try:
            news = [item.model_dump() for item in news_aggregator.get_stock_news(symbol, limit=20, window=news_window)]
            for index, item in enumerate(news):
                cid = item.get("citation_id") or f"c_news_{symbol.lower()}_{index + 1}"
                item["citation_id"] = cid
                citations.append(
                    _citation(
                        "news",
                        item.get("provider") or item.get("source") or "news",
                        item.get("title") or "News article",
                        symbol,
                        item.get("url"),
                        cid,
                        published_at=item.get("published_at"),
                    )
                )
            providers.extend(sorted({item.get("provider") or item.get("source") for item in news if item.get("provider") or item.get("source")}))
            mark("NewsAPI", "ok" if news else "missing", count=len(news))
        except Exception as exc:
            warnings.append(f"News unavailable ({type(exc).__name__}).")
            mark("NewsAPI", "failed", error=type(exc).__name__)

        metrics: dict[str, Any] = {}
        try:
            metrics = compute_financial_metrics(symbol)
            warnings.extend(metrics.get("warnings", []))
            citations.extend(metrics.get("citations", []))
            providers.extend([source for source in metrics.get("sources", []) if source])
            mark("computed_metrics", "ok" if metrics.get("metrics") else "partial", count=len(metrics.get("metrics", {})))
        except Exception as exc:
            warnings.append(f"Financial metrics unavailable ({type(exc).__name__}).")
            mark("computed_metrics", "failed", error=type(exc).__name__)

        filings: list[dict[str, Any]] = []
        try:
            filings = get_sec_filings(symbol, limit=10)
            citations.extend(_citation("sec", "SEC EDGAR", item.get("filing_type") or "SEC filing", symbol, item.get("url"), f"c_edgar_{item.get('accession_number') or index}") for index, item in enumerate(filings))
            mark("SEC EDGAR", "ok" if filings else "missing", count=len(filings))
        except Exception as exc:
            warnings.append(f"SEC filings unavailable ({type(exc).__name__}).")
            mark("SEC EDGAR", "failed", error=type(exc).__name__)

        earnings_payload: dict[str, Any] = {"history": [], "stats": {}, "next": None, "warnings": []}
        try:
            next_event = earnings_data.get_next_earnings(symbol)
            history = [item.model_dump() for item in earnings_data.get_earnings_history(symbol, limit=8)]
            stats = earnings_data.get_earnings_surprise_stats(symbol).model_dump()
            earnings_payload = {"next": next_event.model_dump() if next_event else None, "history": history, "stats": stats, "warnings": stats.get("warnings", [])}
            warnings.extend(earnings_payload["warnings"])
            citations.append(_citation("earnings", stats.get("source", "free_earnings_data"), f"{symbol} earnings data", symbol, f"https://finance.yahoo.com/quote/{symbol}/analysis", "c_earn_" + symbol.lower()))
            mark("earnings", "ok" if history or next_event else "missing", count=len(history))
        except Exception as exc:
            warnings.append(f"Earnings data unavailable ({type(exc).__name__}).")
            mark("earnings", "failed", error=type(exc).__name__)

        macro = get_macro_indicators().model_dump()
        warnings.extend(macro.get("warnings", []))
        citations.extend(macro.get("citations", []))
        mark("FRED", "ok" if macro.get("indicators") else "unconfigured", count=len(macro.get("indicators", {})))

        sectors: list[dict[str, Any]] = []
        try:
            sectors = [item.model_dump() for item in market_data.get_sector_performance()]
            citations.append(_citation("market_data", "sector_etf_yfinance", "US sector ETF performance", symbol, "https://finance.yahoo.com"))
            mark("sector_etfs", "ok" if sectors else "missing", count=len(sectors))
        except Exception as exc:
            warnings.append(f"Sector ETF context unavailable ({type(exc).__name__}).")
            mark("sector_etfs", "failed", error=type(exc).__name__)

        peers = get_peer_comparison(symbol).model_dump()
        warnings.extend(peers.get("warnings", []))
        citations.extend(peers.get("citations", []))
        mark("peer_comparison", "ok" if peers.get("peers") else "partial", count=len(peers.get("peers", [])))

        sentiment = get_stock_sentiment(symbol, window=news_window).model_dump()
        warnings.extend(sentiment.get("warnings", []))
        citations.extend(sentiment.get("citations", []))
        mark("stock_sentiment", "ok", count=1)

        polymarket = get_polymarket_sentiment(symbol, metrics.get("profile", {}).get("name") or symbol).model_dump()
        warnings.extend(polymarket.get("warnings", []))
        citations.extend(polymarket.get("citations", []))
        mark("polymarket", "ok" if polymarket.get("signals") else "missing", count=len(polymarket.get("signals", [])))

        analyst = get_analyst_consensus(symbol).model_dump()
        warnings.extend(analyst.get("warnings", []))
        citations.extend(analyst.get("citations", []))
        mark("analyst_consensus", "ok" if analyst.get("buy_count") is not None else "unconfigured", count=1 if analyst.get("buy_count") is not None else 0)

        form4 = get_form4_activity(symbol).model_dump()
        warnings.extend(form4.get("warnings", []))
        citations.extend(form4.get("citations", []))
        mark("form4_parser", "ok" if form4.get("transactions") else "missing", count=len(form4.get("transactions", [])))

        thirteen_f = get_thirteen_f_activity(symbol).model_dump()
        warnings.extend(thirteen_f.get("warnings", []))
        citations.extend(thirteen_f.get("citations", []))
        mark("thirteen_f_parser", "ok" if thirteen_f.get("filings") else "missing", count=len(thirteen_f.get("filings", [])))

        holders = get_institutional_holder_analysis(symbol).model_dump()
        warnings.extend(holders.get("warnings", []))
        citations.extend(holders.get("citations", []))
        mark("institutional_holders", "ok" if holders.get("holders") else "missing", count=len(holders.get("holders", [])))

        seen: set[str] = set()
        deduped_citations: list[dict[str, Any]] = []
        for citation in citations:
            cid = citation.get("id") or citation.get("citation_id")
            if cid and cid not in seen:
                citation.setdefault("citation_id", cid)
                seen.add(cid)
                deduped_citations.append(citation)

        return {
            "ticker": symbol,
            "company_name": metrics.get("profile", {}).get("name") or symbol,
            "query": query,
            "intent": intent,
            "window": window,
            "quote": quote,
            "news": news,
            "metrics": metrics,
            "filings": filings,
            "earnings": earnings_payload,
            "macro": macro,
            "sectors": sectors,
            "peers": peers,
            "sentiment": sentiment,
            "polymarket": polymarket,
            "analyst_consensus": analyst,
            "form4": form4,
            "thirteen_f": thirteen_f,
            "institutional_holders": holders,
            "citations": deduped_citations,
            "warnings": sorted({warning for warning in warnings if warning}),
            "providers_used": sorted({provider for provider in providers if provider}),
            "provider_metadata": metadata,
        }

    def run_agent(self, agent_name: str, bundle: dict[str, Any], upstream: dict[str, dict[str, Any]], *, mode: str, research_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        cache_key = self.cache.make_key(agent_name, bundle["ticker"], bundle["intent"], bundle["window"], {"bundle": bundle, "upstream": upstream})
        cached = self.cache.get(cache_key)
        if cached is not None:
            record_agent_run(agent_name=agent_name, ticker=bundle["ticker"], intent=bundle["intent"], mode=mode, status="cached", cache_hit=True, research_id=research_id)
            return cached
        try:
            deterministic = AGENT_FUNCTIONS[agent_name](bundle, upstream)
            result = self._refine_with_deepseek(agent_name, deterministic, bundle, upstream, mode=mode, research_id=research_id)
            status = "completed"
        except Exception as exc:
            logger.warning("expert_agent_failed agent=%s ticker=%s error=%s", agent_name, bundle.get("ticker"), type(exc).__name__)
            result = {
                "agent_name": agent_name,
                "ticker": bundle.get("ticker", ""),
                "company_name": bundle.get("company_name", ""),
                "task": agent_name,
                "summary": f"{agent_name} failed gracefully.",
                "key_findings": [],
                "positive_signals": [],
                "negative_signals": [],
                "uncertainties": [],
                "confidence_score": 0,
                "citations": [],
                "warnings": [f"agent_failed: {type(exc).__name__}"],
                "not_investment_advice": True,
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "data_freshness": {"oldest_input_ts": None, "newest_input_ts": None, "stale_data_flag": False},
            }
            status = "failed"
        latency = int((time.perf_counter() - started) * 1000)
        self.cache.set(cache_key, result, ttl_seconds=agent_cache_ttl(agent_name))
        record_agent_run(
            agent_name=agent_name,
            ticker=bundle["ticker"],
            intent=bundle["intent"],
            mode=mode,
            status=status,
            latency_ms=latency,
            cache_hit=False,
            warnings=result.get("warnings", []),
            research_id=research_id,
        )
        return result

    def run(self, *, query: str, ticker: str, mode: str = "fast", window: str | None = None, intent: str | None = None, research_id: str | None = None, emit_event: Any | None = None) -> ExpertGraphResult:
        plan = plan_query(query, selected_ticker=ticker, window=window, explicit_mode=mode)
        if intent:
            plan.intent = intent  # type: ignore[assignment]
        actual_mode = mode if mode in {"fast", "deep"} else plan.mode_recommendation
        agents = selected_agents_for_intent(plan.intent, actual_mode)
        bundle = self.assemble_evidence_bundle(plan.ticker or ticker, query=query, intent=plan.intent, window=plan.time_window)
        if emit_event:
            emit_event("data_collection_completed", warnings=bundle.get("warnings", [])[:5])
        outputs: dict[str, dict[str, Any]] = {}
        for agent_name in agents:
            if emit_event:
                emit_event("agent_started", agent=agent_name)
            result = self.run_agent(agent_name, bundle, outputs, mode=actual_mode, research_id=research_id)
            outputs[agent_name] = result
            if emit_event:
                emit_event("agent_completed" if not result.get("warnings", [""])[0].startswith("agent_failed") else "agent_failed", agent=agent_name, warnings=result.get("warnings", []))
        final = outputs.get("synthesizer", {})
        audit = outputs.get("evidence_auditor", {})
        data_quality = audit.get("data_quality") or ("partial" if bundle.get("warnings") else "good")
        all_warnings = sorted({warning for warning in bundle.get("warnings", []) + [w for result in outputs.values() for w in result.get("warnings", [])] if warning})
        return ExpertGraphResult(
            ticker=bundle["ticker"],
            company_name=bundle.get("company_name", ""),
            intent=plan.intent,
            mode=actual_mode,  # type: ignore[arg-type]
            query=query,
            time_window=bundle["window"],
            final_report=final,
            agent_outputs=outputs,
            citations=bundle.get("citations", []),
            warnings=all_warnings,
            data_quality=data_quality,
            providers_used=bundle.get("providers_used", []),
        )


def run_stock_research(ticker: str, question: str | None = None, *, window: str | None = None, mode: str = "deep", research_id: str | None = None, emit_event: Any | None = None) -> dict[str, Any]:
    """Run stock-first expert research and return a persisted-job-friendly dict."""

    query = question or f"Deep research report on {ticker}"
    runtime = ExpertAgentRuntime()
    result = runtime.run(query=query, ticker=ticker, mode=mode, window=window, research_id=research_id, emit_event=emit_event)
    payload = result.model_dump(mode="json")
    payload.update(
        {
            "id": research_id,
            "research_id": research_id,
            "status": "completed",
            "executive_summary": payload.get("final_report", {}).get("executive_summary"),
            "final_research_summary": payload.get("final_report", {}).get("final_research_summary"),
            "data_quality_warnings": payload.get("warnings", []),
        }
    )
    return payload
