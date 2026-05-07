"""Evidence & Data Quality Auditor component."""

from __future__ import annotations

import json
import re
from typing import Any

from tradingagents.utils.safety import find_forbidden_phrases

from .shared import citation_ids, output

_CIT_RE = re.compile(r"\[cit:([a-zA-Z0-9_-]+)\]")


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    upstream = upstream or {}
    synth = upstream.get("synthesizer", {})
    registry = set(citation_ids(bundle))
    text = json.dumps(synth, default=str)
    cited = set(_CIT_RE.findall(text))
    fabricated = sorted(cited - registry)
    advice = find_forbidden_phrases(text)
    provider_meta = bundle.get("provider_metadata", [])
    failures = [row.get("source") or row.get("provider") for row in provider_meta if row.get("status") in {"failed", "missing", "unconfigured"}]
    stale = [row.get("source") or row.get("provider") for row in provider_meta if row.get("status") == "stale"]
    missing = [row.get("source") or row.get("provider") for row in provider_meta if row.get("status") in {"missing", "unconfigured"}]
    coverage = 1.0 if not cited else (len(cited - set(fabricated)) / len(cited))
    final_safe = not fabricated and not advice
    quality = "excellent" if registry and not failures and not stale else "partial" if registry else "insufficient"
    recommended_action = "release" if final_safe and coverage >= 0.85 else "reject_and_regenerate" if fabricated else "redact_and_release"
    warnings = []
    if failures:
        warnings.append("Provider failures or missing modules reduced data quality.")
    if fabricated:
        warnings.append("Fabricated citation IDs detected.")
    if advice:
        warnings.append("Advice-language violations detected.")
    return output(
        agent_name="Evidence & Data Quality Auditor",
        bundle=bundle,
        task="evidence_data_quality_audit",
        summary=f"Citation coverage={coverage:.2%}; data_quality={quality}; final_answer_safe={final_safe}.",
        key_findings=[f"valid_citation_ids={len(registry)}", f"fabricated_citations={len(fabricated)}", f"provider_failures={len(failures)}"],
        citations=list(registry),
        warnings=warnings,
        confidence=90 if final_safe else 20,
        citation_coverage=coverage,
        unsupported_claims=[],
        fabricated_citation_ids=fabricated,
        advice_language_violations=advice,
        citation_quality_score=int(coverage * 100),
        data_quality=quality,
        missing_data=[str(item) for item in missing if item],
        stale_data=[str(item) for item in stale if item],
        provider_failures=[str(item) for item in failures if item],
        confidence_impact="major" if failures or fabricated or advice else "minor",
        recommended_warnings=warnings + bundle.get("warnings", [])[:5],
        final_answer_safe=final_safe,
        recommended_action=recommended_action,
    )
