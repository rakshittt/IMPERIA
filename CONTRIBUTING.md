# Contributing To IMPERIA

Thanks for helping improve IMPERIA.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## Rules

- Keep the backend stock-first and US-equities only.
- Do not add frontend code until the frontend is intentionally designed.
- Do not hardcode API keys.
- Do not add paid-only data dependencies as required dependencies.
- Preserve citations and warnings when adding new data sources.
- Keep responses educational and not investment advice.

