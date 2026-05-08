# Cost And LLM Usage Tracking

IMPERIA tracks DeepSeek usage for backend observability.

Tracked fields include:

- request id
- research id
- model
- agent name
- ticker
- intent
- mode
- input/output/total tokens when the provider returns them
- latency
- success/failure
- cache hit
- timestamp
- error message type

Endpoints:

```text
GET /api/admin/llm-usage
GET /api/admin/cost
GET /api/admin/agent-runs
GET /api/health/llm
```

The cost dashboard intentionally does not hardcode DeepSeek pricing. It exposes usage counts and token estimates so pricing can be configured externally as provider pricing changes.
