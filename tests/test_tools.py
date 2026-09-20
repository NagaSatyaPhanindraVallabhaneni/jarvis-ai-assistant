"""Tests for JARVIS tools — calculator, notes, timers, stats, search, jokes."""

import json
import time

import pytest

from backend import tools


@pytest.fixture
def notes_path(tmp_path, monkeypatch):
    path = str(tmp_path / "notes.json")
    monkeypatch.setattr(tools, "NOTES_PATH", path)
    return path


# ---------------------------------------------------------------- calculator


def test_calculator_basic_arithmetic():
    assert "7" in tools.calculator("3 + 4")


def test_calculator_operator_precedence():
    assert "14" in tools.calculator("2 + 3 * 4")


def test_calculator_parentheses():
    assert "20" in tools.calculator("(2 + 3) * 4")


def test_calculator_math_functions():
    assert "3.0" in tools.calculator("sqrt(9)")
    assert "3.14159" in tools.calculator("pi")


def test_calculator_divide_by_zero():
    result = tools.calculator("1 / 0")
    assert "zero" in result.lower()


def test_calculator_rejects_malicious_input():
    for evil in [
        "__import__('os').system('ls')",
        "open('/etc/passwd').read()",
        "[x for x in range(10)]",
        "().__class__.__bases__",
        "lambda x: x",
        "exec('1')",
    ]:
        result = tools.calculator(evil)
        assert "beyond my protocols" in result, f"should reject: {evil}"


def test_calculator_rejects_huge_exponent():
    assert "beyond my protocols" in tools.calculator("10 ** 999999")


# ---------------------------------------------------------------- notes


def test_notes_crud(notes_path):
    assert "empty" in tools.list_notes().lower()
    assert "note number 1" in tools.add_note("buy milk")
    assert "note number 2" in tools.add_note("call pepper")
    listed = tools.list_notes()
    assert "buy milk" in listed and "call pepper" in listed
    assert "Deleted note 1" in tools.delete_note(1)
    assert "buy milk" not in tools.list_notes()


def test_notes_delete_missing(notes_path):
    assert "couldn't find" in tools.delete_note(99)


def test_notes_persist_json(notes_path):
    tools.add_note("persist me")
    with open(notes_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data[0]["text"] == "persist me"


# ---------------------------------------------------------------- timers


@pytest.fixture(autouse=True)
def _clean_timers():
    tools._reset_timers()
    yield
    tools._reset_timers()


def test_timer_lifecycle():
    tid = tools.start_timer(60)
    status = tools.timer_status(tid)
    assert "seconds remaining" in status
    assert "cancelled" in tools.cancel_timer(tid).lower()
    assert "no record" in tools.timer_status(tid)


def test_timer_expiry():
    tid = tools.start_timer(0.05)
    time.sleep(0.12)
    assert "completed" in tools.timer_status(tid)


def test_timer_unknown():
    assert "no record" in tools.timer_status("T999")


# ---------------------------------------------------------------- stats / time / joke / search


def test_system_stats_keys():
    stats = tools.system_stats()
    for key in (
        "cpu_percent",
        "memory_percent",
        "memory_used_gb",
        "memory_total_gb",
        "disk_percent",
    ):
        assert key in stats
    assert 0 <= stats["cpu_percent"] <= 100
    assert 0 <= stats["memory_percent"] <= 100


def test_format_stats_mentions_nominal():
    assert "nominal" in tools.format_stats(tools.system_stats()).lower()


def test_get_time_mentions_today():
    assert "sir" in tools.get_time()


def test_joke_from_builtin_list():
    assert tools.joke() in tools._JOKES
    assert len(tools._JOKES) >= 5


def test_web_search_mocked(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"AbstractText": "Mocked answer about Tony Stark."}

    monkeypatch.setattr("httpx.get", lambda *a, **k: FakeResp())
    result = tools.web_search("tony stark")
    assert "Mocked answer" in result


def test_web_search_network_failure_graceful(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("offline")

    monkeypatch.setattr("httpx.get", boom)
    result = tools.web_search("anything")
    assert "down" in result.lower() or "unavailable" in result.lower()


# ---------------------------------------------------------------- registry


def test_tool_registry_dispatch(notes_path):
    assert "sir" in str(tools.call_tool("get_time"))
    assert str(tools.call_tool("joke")) in tools._JOKES
    assert isinstance(tools.call_tool("system_stats"), dict)
    assert "note number 1" in tools.call_tool("notes_add", {"text": "via registry"})


def test_call_tool_unknown_raises():
    with pytest.raises(ValueError):
        tools.call_tool("self_destruct")
