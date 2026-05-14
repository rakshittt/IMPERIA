FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EVENTLET_NO_GREENDNS=yes \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY api.py ./api.py
COPY cli ./cli
COPY tradingagents ./tradingagents

RUN mkdir -p /home/appuser/.tradingagents && chown -R appuser:appuser /app /home/appuser/.tradingagents

USER appuser

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
