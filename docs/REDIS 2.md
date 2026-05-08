# Redis Production-Style Mode

Redis is implemented as a required production-style backend capability for IMPERIA.

Environment:

```bash
REDIS_URL=redis://localhost:6379
IMPERIA_CACHE_BACKEND=redis
```

Redis support is used for:

- agent output cache
- production-style rate limiting
- research event buffers
- provider/data cache integration points
- LLM usage/cost dashboard support

SQLite remains the local/demo fallback so deterministic endpoints still work when Redis is unavailable. If `IMPERIA_CACHE_BACKEND=redis` and Redis is unreachable, provider health reports a degraded warning.

Docker Compose includes a Redis service for local production-style runs.
