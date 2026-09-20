"""API tests — health, tools, command routing, LLM-mode key requirement."""

import pytest
from fastapi.testclient import TestClient

from backend import tools
from backend.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "NOTES_PATH", str(tmp_path / "notes.json"))
    tools._reset_timers()
    yield
    tools._reset_timers()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["assistant"] == "JARVIS"


def test_tools_list():
    r = client.get("/api/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["tools"]}
    assert {
        "get_time",
        "system_stats",
        "web_search",
        "calculator",
        "notes_add",
        "joke",
    } <= names


def test_command_time():
    r = client.post("/api/command", json={"text": "what time is it"})
    assert r.status_code == 200
    assert r.json()["action"] == "get_time"


def test_command_stats():
    r = client.post("/api/command", json={"text": "system status"})
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "system_stats"
    assert body["data"]["stats"]["cpu_percent"] >= 0


def test_command_empty_rejected():
    r = client.post("/api/command", json={"text": "   "})
    assert r.status_code == 400


def test_llm_requires_key():
    r = client.post("/api/llm", json={"text": "hello", "api_key": ""})
    assert r.status_code == 400
    assert "API key" in r.json()["detail"]


def test_llm_empty_prompt_rejected():
    r = client.post(
        "/api/llm",
        json={"text": " ", "api_key": "sk-test", "base_url": "http://localhost:1"},
    )
    assert r.status_code == 400


def test_frontend_served_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "J.A.R.V.I.S." in r.text
