# Research Streaming

Deep research runs as a background job and exposes Server-Sent Events.

Submit:

```bash
curl -X POST "http://localhost:8000/api/research" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","question":"Analyze Nvidia as an AI infrastructure company.","window":"past_month"}'
```

Stream:

```bash
curl "http://localhost:8000/api/research/{research_id}/stream"
```

Compatibility stream path:

```text
GET /api/research/stream/{research_id}
```

Events include:

- queued
- running
- data_collection_started
- data_collection_completed
- agent_started
- agent_completed
- agent_failed
- synthesis_started
- synthesis_completed
- audit_started
- completed
- failed

Streaming is observable best-effort. If a job is missing, the stream exits cleanly with a not-found status event.
