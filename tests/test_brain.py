"""Tests for the offline intent router — every route gets exercised."""

import pytest

from backend import brain, tools


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "NOTES_PATH", str(tmp_path / "notes.json"))
    tools._reset_timers()
    yield
    tools._reset_timers()


def test_route_time():
    r = brain.route("hey jarvis, what time is it")
    assert r["action"] == "get_time"
    assert "sir" in r["response"]


def test_route_stats_returns_data():
    r = brain.route("system status")
    assert r["action"] == "system_stats"
    assert "nominal" in r["response"].lower()
    assert "stats" in r["data"] and "cpu_percent" in r["data"]["stats"]


def test_route_calculate():
    r = brain.route("calculate 12 * 12")
    assert r["action"] == "calculator"
    assert "144" in r["response"]


def test_route_calculate_falls_back_to_search(monkeypatch):
    monkeypatch.setattr(tools, "web_search", lambda q: f"searched:{q}")
    r = brain.route("what is the capital of france")
    assert r["action"] == "web_search"
    assert "searched" in r["response"]


def test_route_search(monkeypatch):
    monkeypatch.setattr(tools, "web_search", lambda q: f"searched:{q}")
    r = brain.route("search for arc reactor specs")
    assert r["action"] == "web_search"


def test_route_question_mark_search(monkeypatch):
    monkeypatch.setattr(tools, "web_search", lambda q: f"searched:{q}")
    r = brain.route("who invented the arc reactor?")
    assert r["action"] == "web_search"


def test_route_notes_flow():
    r = brain.route("take a note: suit needs new repulsors")
    assert r["action"] == "notes_add"
    r = brain.route("list my notes")
    assert r["action"] == "notes_list"
    assert "repulsors" in r["response"]
    r = brain.route("delete note 1")
    assert r["action"] == "notes_delete"


def test_route_timer_flow():
    r = brain.route("set a timer for 5 minutes")
    assert r["action"] == "timer_start"
    assert r["data"]["seconds"] == 300
    tid = r["data"]["timer_id"]
    r = brain.route("timer status")
    assert tid in r["response"]
    r = brain.route("cancel timer")
    assert "cancelled" in r["response"].lower()


def test_route_joke():
    r = brain.route("tell me a joke")
    assert r["action"] == "joke"


def test_route_greeting():
    r = brain.route("hello jarvis")
    assert r["action"] == "greet"


def test_route_help():
    r = brain.route("help")
    assert r["action"] == "help"
    assert "calculate" in r["response"].lower()


def test_route_fallback():
    r = brain.route("launch the hulkbuster protocol")
    assert r["action"] == "fallback"
    assert "don't have a protocol" in r["response"]


def test_route_empty_fallback():
    r = brain.route("xyzzy plugh")
    assert r["action"] == "fallback"
