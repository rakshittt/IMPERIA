# IMPERIA Developer Guide

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Run tests:

```bash
pytest -q
```

Run the API:

```bash
uvicorn api:app --reload
```

## Environment Variables

Required for SEC-friendly operation:

```bash
SEC_USER_AGENT="IMPERIA/0.3.0 contact=you@example.com"
```

Optional keys:

```bash
DEEPSEEK_API_KEY=
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
FINANCIAL_MODELING_PREP_API_KEY=
TWELVE_DATA_API_KEY=
EODHD_API_KEY=
NEWSAPI_API_KEY=
NEWSDATA_API_KEY=
THENEWSAPI_COM_API_TOKEN=
THENEWSAPI_API_TOKEN=
TAVILY_API_KEY=
```

Local storage:

```bash
TRADINGAGENTS_SQLITE_CACHE="$HOME/.tradingagents/cache/backend_cache.sqlite3"
PERSISTENCE_DB_PATH="./.tradingagents_data/user_data.db"
```

## Development Rules

- Keep the internal `tradingagents` package path stable unless you plan a coordinated import migration.
- Keep frontend code out of this repo until the new IMPERIA frontend is intentionally designed.
- Never hardcode API keys.
- New external calls should use `tradingagents.utils.http`.
- New DeepSeek calls should use `tradingagents.utils.deepseek`.
- New ticker/date inputs should use `tradingagents.utils.validation`.
- Add tests for every dataflow, route, or agent behavior change.

## Adding A Route

1. Add or reuse a dataflow/service function.
2. Add Pydantic request/response fields in `tradingagents/api/models.py` if needed.
3. Add the route in `tradingagents/api/routes/`.
4. Include it in `tradingagents/api/main.py` if it is a new router.
5. Add tests in `tests/`.

## Adding A Data Source

1. Confirm it is free-tier-safe.
2. Read credentials only from `os.environ`.
3. Add retries, timeout, and warning fallback.
4. Cache responses when a TTL makes sense.
5. Document limitations in `docs/backend_free_us_finance.md`.

## Running Deep Research

Use `/api/research` for non-blocking research jobs. The background queue is intentionally simple:

- `ThreadPoolExecutor(max_workers=3)`
- status persisted in SQLite
- process-local futures

Do not add Celery/Redis/RabbitMQ unless the deployment target truly needs distributed jobs.
