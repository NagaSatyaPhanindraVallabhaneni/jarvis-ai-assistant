"""Offline intent router — honest rule-based command routing, no LLM involved.

Each intent maps to a regex matched against the lowercased input. Order
matters: more specific patterns are checked first. Anything unmatched gets a
polite JARVIS-style fallback.
"""

from __future__ import annotations

import re

from . import tools

_INTENTS = [
    ("help", re.compile(r"\bhelp\b|\bwhat can you do\b|\bcommands\b|\babilities\b")),
    (
        "timer_status",
        re.compile(r"timer status|how much (time )?left|time remaining"),
    ),
    ("timer_cancel", re.compile(r"cancel timer|stop timer|delete timer")),
    (
        "timer_start",
        re.compile(
            r"(?:set|start) (?:a )?timer for (\d+(?:\.\d+)?)\s*(second|minute|hour)s?"
        ),
    ),
    (
        "stats",
        re.compile(
            r"\bsystem status\b|\bcpu\b|\bmemory\b|\bram\b|\bdisk\b|\bstats\b|diagnostics"
        ),
    ),
    (
        "time",
        re.compile(
            r"\bwhat time\b|\bcurrent time\b|\bthe time\b|\bwhat'?s the date\b"
            r"|\btoday'?s date\b|\bwhat day\b"
        ),
    ),
    (
        "notes_add",
        re.compile(
            r"(?:take a note|note that|remember that|write down|jot down)[:\s]+(.+)"
        ),
    ),
    (
        "notes_delete",
        re.compile(r"(?:delete|remove) note (\d+)"),
    ),
    (
        "notes_list",
        re.compile(r"\b(list|show|read) (my )?notes\b|\bmy notes\b"),
    ),
    ("joke", re.compile(r"\bjoke\b|\bmake me laugh\b|\bfunny\b")),
    (
        "calculate",
        re.compile(
            r"(?:calculate|compute|what is|what'?s|solve|evaluate)\s+"
            r"([\d\s\.\+\-\*\/\%\^\(\)a-z,]+)"
        ),
    ),
    (
        "search",
        re.compile(r"(?:search(?: the web)? for|look up|google|find out about)\s+(.+)"),
    ),
    (
        "question",
        re.compile(
            r"^(who|what|where|when|why|how|which|is|are|can|do|does)\b.*\?$|.*\?$"
        ),
    ),
    (
        "greet",
        re.compile(r"^(hi|hello|hey|greetings|yo)\b|good (morning|afternoon|evening)"),
    ),
]


def _mathy(text: str) -> bool:
    """Heuristic: does the text look like a math expression worth evaluating?"""
    stripped = re.sub(r"[0-9\s\.\+\-\*\/\%\^\(\)a-z]", "", text)
    return stripped == "" and bool(re.search(r"\d", text))


def route(text: str) -> dict:
    """Route a command string to a tool. Returns {response, action, data}."""
    original = text.strip()
    lowered = original.lower()

    for action, pattern in _INTENTS:
        match = pattern.search(lowered)
        if not match:
            continue

        if action == "help":
            return {
                "response": (
                    "At your service, sir. I can tell the time, report system status, "
                    "calculate, search the web, manage your notes, run timers, and "
                    "tell the occasional joke. Try 'Hey Jarvis, what time is it'."
                ),
                "action": "help",
                "data": None,
            }
        if action == "greet":
            return {
                "response": "Good to see you, sir. All systems are now fully operational.",
                "action": "greet",
                "data": None,
            }
        if action == "timer_status":
            return {
                "response": tools.timer_status(_last_timer()),
                "action": "timer_status",
                "data": None,
            }
        if action == "timer_cancel":
            return {
                "response": tools.cancel_timer(_last_timer()),
                "action": "timer_cancel",
                "data": None,
            }
        if action == "timer_start":
            amount = float(match.group(1))
            unit = match.group(2)
            seconds = amount * {"second": 1, "minute": 60, "hour": 3600}[unit]
            timer_id = tools.start_timer(seconds)
            _remember_timer(timer_id)
            plural = "s" if amount != 1 else ""
            return {
                "response": f"Timer {timer_id} engaged for {amount:g} {unit}{plural}, sir.",
                "action": "timer_start",
                "data": {"timer_id": timer_id, "seconds": seconds},
            }
        if action == "stats":
            stats = tools.system_stats()
            return {
                "response": tools.format_stats(stats),
                "action": "system_stats",
                "data": {"stats": stats},
            }
        if action == "time":
            return {"response": tools.get_time(), "action": "get_time", "data": None}
        if action == "notes_add":
            return {
                "response": tools.add_note(match.group(1)),
                "action": "notes_add",
                "data": None,
            }
        if action == "notes_delete":
            return {
                "response": tools.delete_note(int(match.group(1))),
                "action": "notes_delete",
                "data": None,
            }
        if action == "notes_list":
            return {
                "response": tools.list_notes(),
                "action": "notes_list",
                "data": None,
            }
        if action == "joke":
            return {"response": tools.joke(), "action": "joke", "data": None}
        if action == "calculate":
            expr = match.group(1).replace("divided by", "/").replace("times", "*")
            if _mathy(expr):
                return {
                    "response": tools.calculator(expr),
                    "action": "calculator",
                    "data": None,
                }
            # Not actually math — fall through to web search.
            return {
                "response": tools.web_search(match.group(1)),
                "action": "web_search",
                "data": None,
            }
        if action in ("search", "question"):
            query = match.group(1) if action == "search" else original
            return {
                "response": tools.web_search(query),
                "action": "web_search",
                "data": None,
            }

    return {
        "response": (
            "I'm afraid I don't have a protocol for that yet, sir. "
            "Try 'help' to see what I can do — or switch to LLM mode for open-ended conversation."
        ),
        "action": "fallback",
        "data": None,
    }


# Remember the most recently started timer so "timer status" works naturally.
_last_timer_id: str | None = None


def _remember_timer(timer_id: str) -> None:
    global _last_timer_id
    _last_timer_id = timer_id


def _last_timer() -> str:
    return _last_timer_id or "T1"
