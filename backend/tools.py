"""JARVIS tool implementations — every tool is a real, executable function.

All tools are pure Python with no mock data. ``web_search`` is the only tool
that touches the network, and it degrades gracefully when offline.
"""

from __future__ import annotations

import ast
import json
import math
import os
import random
import shutil
import threading
import time
from datetime import datetime

import httpx
import psutil

NOTES_PATH = os.environ.get("JARVIS_NOTES_PATH") or os.path.expanduser(
    "~/.jarvis_notes.json"
)

# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------


def get_time() -> str:
    """Return the current local time and date, JARVIS style."""
    now = datetime.now().astimezone()
    return now.strftime("It is %I:%M %p on %A, %B %d, %Y, sir.")


# ---------------------------------------------------------------------------
# System stats
# ---------------------------------------------------------------------------


def system_stats() -> dict:
    """Return live CPU / memory / disk telemetry from the host machine."""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "memory_used_gb": round(mem.used / 1e9, 2),
        "memory_total_gb": round(mem.total / 1e9, 2),
        "disk_percent": round(disk.used / disk.total * 100, 1),
    }


def format_stats(stats: dict) -> str:
    """Render system stats as a JARVIS-style status report."""
    return (
        "Systems nominal, sir. "
        f"CPU load at {stats['cpu_percent']}%. "
        f"Memory at {stats['memory_percent']}% "
        f"({stats['memory_used_gb']} of {stats['memory_total_gb']} GB). "
        f"Disk at {stats['disk_percent']}%."
    )


# ---------------------------------------------------------------------------
# Web search (DuckDuckGo Instant Answer API — no key required)
# ---------------------------------------------------------------------------


def web_search(query: str, timeout: float = 8.0) -> str:
    """Answer a question via DuckDuckGo's free Instant Answer API.

    Degrades gracefully: any network failure returns a polite message
    instead of raising.
    """
    try:
        resp = httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("AbstractText") or data.get("Answer")
        if answer:
            return f"According to my sources, sir: {answer}"
        topics = [
            t.get("Text")
            for t in data.get("RelatedTopics", [])
            if isinstance(t, dict) and t.get("Text")
        ]
        if topics:
            return f"Here's what I found, sir: {topics[0]}"
        return "My search came up empty, sir. No records matched your query."
    except Exception:  # noqa: BLE001 - graceful degradation is the feature here
        return "I'm afraid my uplink to the outside world is down, sir. Search unavailable."


# ---------------------------------------------------------------------------
# Calculator — safe AST-based evaluation, never raw eval()
# ---------------------------------------------------------------------------

_ALLOWED_BINOPS = {ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow}
_ALLOWED_UNARYOPS = {ast.UAdd, ast.USub}
_ALLOWED_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        op = type(node.op)
        if op is ast.Div and right == 0:
            raise ZeroDivisionError("division by zero")
        if op is ast.FloorDiv and right == 0:
            raise ZeroDivisionError("division by zero")
        if op is ast.Mod and right == 0:
            raise ZeroDivisionError("division by zero")
        if op is ast.Pow and abs(right) > 1000:
            raise ValueError("exponent too large")
        return {
            ast.Add: left + right,
            ast.Sub: left - right,
            ast.Mult: left * right,
            ast.Div: left / right,
            ast.FloorDiv: left // right,
            ast.Mod: left % right,
            ast.Pow: left**right,
        }[op]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        operand = _eval_node(node.operand)
        return +operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _ALLOWED_FUNCS.get(node.func.id)
        if fn is None or node.keywords:
            raise ValueError("unsupported function")
        return fn(*[_eval_node(a) for a in node.args])
    if isinstance(node, ast.Name) and node.id in _ALLOWED_CONSTS:
        return _ALLOWED_CONSTS[node.id]
    raise ValueError("unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a math expression safely (no raw eval)."""
    try:
        cleaned = expression.strip().replace("^", "**")
        node = ast.parse(cleaned, mode="eval")
        result = _eval_node(node)
        if isinstance(result, float):
            result = round(result, 6)
        return f"That comes to {result}, sir."
    except ZeroDivisionError:
        return "Even my arc reactor can't divide by zero, sir."
    except (SyntaxError, ValueError):
        return "I'm afraid that calculation is beyond my protocols, sir."


# ---------------------------------------------------------------------------
# Notes — persisted to a local JSON file
# ---------------------------------------------------------------------------


def _load_notes(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_notes(notes: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)


def add_note(text: str, path: str | None = None) -> str:
    path = path or NOTES_PATH
    notes = _load_notes(path)
    notes.append(
        {
            "text": text.strip(),
            "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    _save_notes(notes, path)
    return f"Noted, sir. That's note number {len(notes)}."


def list_notes(path: str | None = None) -> str:
    path = path or NOTES_PATH
    notes = _load_notes(path)
    if not notes:
        return "Your notebook is empty, sir."
    lines = [f"{i + 1}. {n['text']}" for i, n in enumerate(notes)]
    return "Your notes, sir:\n" + "\n".join(lines)


def delete_note(index: int, path: str | None = None) -> str:
    path = path or NOTES_PATH
    notes = _load_notes(path)
    if index < 1 or index > len(notes):
        return "I couldn't find that note, sir."
    removed = notes.pop(index - 1)
    _save_notes(notes, path)
    return f'Deleted note {index} ("{removed["text"]}"), sir.'


# ---------------------------------------------------------------------------
# Timer — in-memory countdown timers
# ---------------------------------------------------------------------------

_timers: dict = {}
_timers_lock = threading.Lock()


def start_timer(seconds: float) -> str:
    """Start a countdown timer; returns its id."""
    with _timers_lock:
        timer_id = f"T{len(_timers) + 1}"
        _timers[timer_id] = {"duration": seconds, "start": time.monotonic()}
    return timer_id


def timer_remaining(timer_id: str):
    """Seconds remaining on a timer, or None if it doesn't exist."""
    entry = _timers.get(timer_id)
    if entry is None:
        return None
    remaining = entry["duration"] - (time.monotonic() - entry["start"])
    return max(0.0, remaining)


def timer_status(timer_id: str) -> str:
    remaining = timer_remaining(timer_id)
    if remaining is None:
        return "I have no record of that timer, sir."
    if remaining <= 0:
        return f"Timer {timer_id} has completed, sir."
    return f"Timer {timer_id}: {remaining:.1f} seconds remaining, sir."


def cancel_timer(timer_id: str) -> str:
    with _timers_lock:
        if timer_id not in _timers:
            return "I have no record of that timer, sir."
        del _timers[timer_id]
    return f"Timer {timer_id} cancelled, sir."


def _reset_timers() -> None:
    """Test helper — clears all timers. Not part of the public tool set."""
    with _timers_lock:
        _timers.clear()


# ---------------------------------------------------------------------------
# Jokes
# ---------------------------------------------------------------------------

_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my suit's AI a joke once. It took 3 seconds to laugh — the latency was unbearable.",
    "Why did the developer go broke? He used up all his cache.",
    "There are only 10 kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks… 'Mind if I join you?'",
    "Why do Java developers wear glasses? Because they don't C#.",
    "My neural network told me a joke. I didn't get it — it was too deep.",
    "Debugging: being the detective in a crime movie where you are also the murderer.",
]


def joke() -> str:
    """Return a random joke from the built-in list."""
    return random.choice(_JOKES)


# ---------------------------------------------------------------------------
# Tool registry — powers /api/tools and the LLM tool-calling loop
# ---------------------------------------------------------------------------

TOOL_DEFS = [
    {
        "name": "get_time",
        "description": "Get the current local time and date.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "system_stats",
        "description": "Get live CPU, memory, and disk usage of the host machine.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "web_search",
        "description": "Search the web for a query and return a short answer.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Safely evaluate a math expression, e.g. '2 * (3 + 4)'.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "notes_add",
        "description": "Save a text note to the notebook.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "notes_list",
        "description": "List all saved notes.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "notes_delete",
        "description": "Delete a note by its 1-based number.",
        "parameters": {
            "type": "object",
            "properties": {"index": {"type": "integer"}},
            "required": ["index"],
        },
    },
    {
        "name": "timer_start",
        "description": "Start a countdown timer for a number of seconds.",
        "parameters": {
            "type": "object",
            "properties": {"seconds": {"type": "number"}},
            "required": ["seconds"],
        },
    },
    {
        "name": "timer_status",
        "description": "Check how much time is left on a timer by its id.",
        "parameters": {
            "type": "object",
            "properties": {"timer_id": {"type": "string"}},
            "required": ["timer_id"],
        },
    },
    {
        "name": "joke",
        "description": "Tell a (terrible) joke.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def call_tool(name: str, args: dict | None = None):
    """Dispatch a tool call by name. Raises ValueError for unknown tools."""
    args = args or {}
    handlers = {
        "get_time": lambda: get_time(),
        "system_stats": lambda: system_stats(),
        "web_search": lambda: web_search(args["query"]),
        "calculator": lambda: calculator(args["expression"]),
        "notes_add": lambda: add_note(args["text"]),
        "notes_list": lambda: list_notes(),
        "notes_delete": lambda: delete_note(int(args["index"])),
        "timer_start": lambda: start_timer(float(args["seconds"])),
        "timer_status": lambda: timer_status(args["timer_id"]),
        "joke": lambda: joke(),
    }
    if name not in handlers:
        raise ValueError(f"unknown tool: {name}")
    return handlers[name]()
