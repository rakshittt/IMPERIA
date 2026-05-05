import time

import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.api.routes import research
from tradingagents.persistence import db as db_module
from tradingagents.persistence.db import PersistenceDB
from tradingagents.persistence.portfolio import get_persisted_research
from tradingagents.workers import background_jobs


@pytest.fixture()
def persistence_db(tmp_path, monkeypatch):
    test_db = PersistenceDB(tmp_path / "jobs.db")
    monkeypatch.setattr(db_module, "_DB", test_db)
    return test_db


@pytest.mark.unit
def test_submit_research_job_completes(persistence_db):
    def runner(portfolio, analysis_date, profile, research_id):
        return {"id": research_id, "final_portfolio_feedback": "done"}

    job = background_jobs.submit_research_job(runner, [{"ticker": "AAPL"}], "2026-01-01", {})
    for _ in range(20):
        status = background_jobs.get_research_job(job["research_id"])
        if status and status["status"] == "completed":
            break
        time.sleep(0.05)
    assert background_jobs.get_research_job(job["research_id"])["status"] == "completed"


@pytest.mark.unit
def test_submit_research_job_failure(persistence_db):
    def runner(portfolio, analysis_date, profile, research_id):
        raise RuntimeError("boom")

    job = background_jobs.submit_research_job(runner, [], None, {})
    for _ in range(20):
        status = background_jobs.get_research_job(job["research_id"])
        if status and status["status"] == "failed":
            break
        time.sleep(0.05)
    assert "boom" in background_jobs.get_research_job(job["research_id"])["error"]
    assert "boom" in get_persisted_research(job["research_id"])["error"]


@pytest.mark.unit
def test_research_status_event_json(persistence_db):
    def runner(portfolio, analysis_date, profile, research_id):
        return {"ok": True}

    job = background_jobs.submit_research_job(runner, [], None, {})
    event = background_jobs.research_status_event(job["research_id"])
    assert job["research_id"] in event


@pytest.mark.unit
def test_missing_research_job_returns_none(persistence_db):
    assert background_jobs.get_research_job("missing") is None


@pytest.mark.unit
def test_research_route_missing_id_404(persistence_db, monkeypatch):
    monkeypatch.setattr(research, "get_research_job", lambda research_id: None)
    client = TestClient(create_app())
    response = client.get("/api/research/missing")
    assert response.status_code == 404


@pytest.mark.unit
def test_submit_returns_queued_status(persistence_db):
    def runner(portfolio, analysis_date, profile, research_id):
        return {"ok": True}

    job = background_jobs.submit_research_job(runner, [], None, {}, research_id="fixed")
    assert job == {"research_id": "fixed", "id": "fixed", "status": "queued"}
