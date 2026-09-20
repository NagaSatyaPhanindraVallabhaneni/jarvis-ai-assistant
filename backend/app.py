"""JARVIS AI Assistant — FastAPI backend.

Two modes:
  * Offline command mode  — POST /api/command routes text through the
    rule-based intent router (backend/brain.py). No network, no key needed.
  * LLM mode              — POST /api/llm forwards to any OpenAI-compatible
    chat-completions endpoint with a JARVIS system prompt and real tool
    calling. The user's key travels only from their browser to their chosen
    endpoint; it is never stored or logged server-side.

The single-page HUD in frontend/ is served at / (no build step).
"""

from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import brain, tools

log = logging.getLogger("jarvis")

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(HERE), "frontend")

JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, a witty and loyal AI assistant in the style of Iron Man's "
    "AI. Address the user as 'sir' occasionally, be concise, and be genuinely "
    "helpful. You have access to real tools — use them instead of guessing. "
    "When a tool result comes back, weave it into a natural spoken-style reply."
)

app = FastAPI(title="JARVIS AI Assistant", version="0.1.0")


class CommandRequest(BaseModel):
    text: str


class LLMRequest(BaseModel):
    text: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"


@app.get("/api/health")
def health():
    return {"status": "online", "assistant": "JARVIS", "mode": "standing by"}


@app.get("/api/tools")
def list_tools():
    return {"tools": tools.TOOL_DEFS}


@app.post("/api/command")
def command(req: CommandRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty command, sir.")
    return brain.route(req.text)


def _openai_tool_schemas() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools.TOOL_DEFS
    ]


def _llm_chat(
    base_url: str, api_key: str, model: str, user_text: str, max_steps: int = 4
) -> dict:
    """Run a small tool-calling loop against an OpenAI-compatible endpoint.

    The API key is used only in the Authorization header of the outbound
    request. It is never logged, never stored, and never returned.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    messages = [
        {"role": "system", "content": JARVIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    steps = 0
    try:
        while steps < max_steps:
            resp = httpx.post(
                url,
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "tools": _openai_tool_schemas(),
                    "tool_choice": "auto",
                },
                timeout=90,
            )
            resp.raise_for_status()
            assistant_msg = resp.json()["choices"][0]["message"]
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_msg.get("content"),
                    "tool_calls": assistant_msg.get("tool_calls"),
                }
            )
            tool_calls = assistant_msg.get("tool_calls") or []
            if not tool_calls:
                return {
                    "response": assistant_msg.get("content") or "…",
                    "steps": steps + 1,
                }
            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                    result = tools.call_tool(name, args)
                except Exception as exc:  # noqa: BLE001 - surface to the model
                    result = f"Tool '{name}' failed: {exc}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": str(result),
                    }
                )
            steps += 1
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM endpoint unreachable, sir: {exc}",
        ) from exc
    return {
        "response": "I've hit my reasoning limit, sir. Shall I try that again?",
        "steps": steps,
    }


@app.post("/api/llm")
def llm(req: LLMRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty prompt, sir.")
    if not req.api_key.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "LLM mode requires your own API key, sir. Add it in the HUD settings "
                "panel (stored only in your browser) or use any OpenAI-compatible "
                "endpoint — including a local one like Ollama or LM Studio."
            ),
        )
    # Key deliberately NOT logged.
    return _llm_chat(req.base_url, req.api_key, req.model, req.text)


# Serve the HUD last so /api/* routes take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
