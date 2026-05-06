# IMPERIA Developer Instructions

IMPERIA is a backend-first US equity intelligence product. Keep the repo focused on backend, engine, dataflows, persistence, tests, and docs.

## Rules

- Do not reintroduce frontend files until the new IMPERIA frontend is intentionally scoped.
- Preserve the internal `tradingagents` Python package path for compatibility.
- Do not rewrite the core graph in `tradingagents/graph/`; specialist agents should be additive.
- Never hardcode API keys. Read keys from `os.environ`.
- Use free/open data sources only for the fast path.
- Use DeepSeek helpers in `tradingagents/utils/deepseek.py` for synthesis calls.
- Use HTTP helpers in `tradingagents/utils/http.py` for new external calls.
- Add tests for route, dataflow, agent, and persistence changes.

## Important Commands

```bash
pytest -q
uvicorn api:app --reload
python scripts/smoke_test.py
```
