# Admin API

IMPERIA includes backend-only admin APIs for local/demo observability. They are not frontend routes and they do not expose secrets.

Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/admin/status` | Product/module status |
| GET | `/api/admin/providers` | Provider configuration and required-module status |
| GET | `/api/admin/cache` | SQLite and Redis cache status |
| GET | `/api/admin/research-jobs` | Persisted research job summaries |
| GET | `/api/admin/agent-runs` | Expert-agent execution history |
| GET | `/api/admin/llm-usage` | DeepSeek usage records |
| GET | `/api/admin/cost` | Usage-only cost dashboard without hardcoded pricing |
| GET | `/api/admin/errors` | Internal admin error records |

Auth is not implemented yet. Treat these APIs as local/demo development tooling.
