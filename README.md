# 🤖 J.A.R.V.I.S. — AI Assistant Interface

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-00D4FF?style=for-the-badge)

An **Iron Man-inspired personal AI assistant** with a futuristic HUD web interface, real voice interaction, and a genuine tool-executing backend. Part showpiece, part real engineering: every tool it claims to run is a real implemented function, every test is real, and every architectural claim below is verifiable in the code.

> *"At your service, sir."*

## ✨ What it looks like

Open `http://localhost:8000` and you get a dark, cyan-glow command deck:

- **Pulsing arc-reactor core** — CSS-animated reactor that "spins up" while JARVIS speaks
- **Boot-up sequence** — terminal-style initialization log on every load
- **Live voice waveform** — real microphone audio visualized via the Web Audio API
- **Communications log** — chat transcript with JARVIS/persona styling
- **System diagnostics panel** — live CPU / memory / disk bars, polled from the backend every 3s
- **Settings deck** — brain-mode toggle + LLM endpoint configuration

No mockups here — clone it and the HUD above is exactly what renders.

## 🧠 Two brains, honestly labeled

| Mode | How it works | Setup |
|---|---|---|
| **Offline command mode** (default) | Rule-based intent router (`backend/brain.py`): keyword/regex matching routes your text to real tools. Fast, private, zero setup. | None — just run it |
| **LLM brain mode** | Your prompt goes to any OpenAI-compatible chat-completions endpoint with a JARVIS system prompt + real tool definitions; the server runs a tool-calling loop (max 4 steps) executing the actual tools below. | Your own API key, entered in the HUD settings |

Your key is stored **only in the browser's localStorage** and travels **only to your chosen endpoint** — it is never stored or logged server-side.

## 🛠️ Real tools (all implemented, all tested)

| Tool | What it really does |
|---|---|
| `get_time` | Current local time & date |
| `system_stats` | Live CPU %, RAM, disk via `psutil` |
| `web_search` | DuckDuckGo Instant Answer API (no key needed), graceful offline fallback |
| `calculator` | Safe AST-based math eval — **never `eval()`**; rejects `__import__`, lambdas, attribute access |
| `notes` | Add / list / delete notes, persisted to a local JSON file |
| `timer` | In-memory countdown timers with status & cancel |
| `joke` | A small built-in list of terrible tech jokes |

## 🎙️ Voice commands that actually work

Say *"Hey Jarvis"* (wake-word mode) or hit **push-to-talk**, then:

| Say | What happens |
|---|---|
| "Hey Jarvis, what time is it" | Speaks the current time |
| "Hey Jarvis, system status" | Reads CPU / memory / disk |
| "Hey Jarvis, calculate 18 times 24" | Safe math → "That comes to 432, sir." |
| "Hey Jarvis, search for the speed of light" | Web search → spoken summary |
| "Hey Jarvis, take a note: buy more arc reactors" | Saved to the notes file |
| "Hey Jarvis, list my notes" | Reads your notes back |
| "Hey Jarvis, delete note 2" | Deletes note #2 |
| "Hey Jarvis, set a timer for 5 minutes" | Starts a countdown, reports status |
| "Hey Jarvis, timer status" | Remaining time |
| "Hey Jarvis, tell me a joke" | Regrettable humor, on demand |
| "Hey Jarvis, help" | Lists everything it can do |

## 🏗️ How it works

```
┌──────────────────────────── FRONTEND (no build step) ────────────────────────────┐
│  index.html + style.css + app.js                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Arc-reactor  │  │ SpeechRecognition│  │ speechSynthesis  │  │ Web Audio    │  │
│  │ HUD + chat   │  │ wake phrase /    │  │ (en-GB male      │  │ waveform     │  │
│  │ + diagnostics│  │ push-to-talk     │  │  voice preferred)│  │ visualizer   │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────────────┘  └──────────────┘  │
└─────────┼──────────────────┼────────────────────────────────────────────────────┘
          │  POST /api/command {text}            │  POST /api/llm {text,key,…}
          ▼                                     ▼
┌──────────────────────────── BACKEND (FastAPI) ───────────────────────────────────┐
│  brain.py: regex intent router ──► tools.py (real functions)                     │
│  app.py: /api/llm ──► OpenAI-compatible tool-calling loop (≤4 steps)            │
│         GET /api/health · GET /api/tools · static HUD served at /                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quickstart

```bash
# Option 1 — Docker
docker build -t jarvis .
docker run -p 8000:8000 jarvis

# Option 2 — local
pip install -r requirements.txt
uvicorn backend.app:app --port 8000
```

Then open **http://localhost:8000**, allow the microphone, and say **"Hey Jarvis"**.

**LLM mode (optional):** click the settings panel → switch to **LLM** → enter any OpenAI-compatible base URL + key + model → save. Free & private option: run [Ollama](https://ollama.com) locally and set the base URL to `http://localhost:11434/v1` (any placeholder key works).

## 🧪 Tests

42 tests, ~5 seconds, zero network calls (web search is mocked):

```bash
pytest -q        # 42 passed
ruff check backend tests
```

Coverage: calculator edge cases (incl. rejecting `__import__('os').system(...)`, huge exponents, division by zero), notes CRUD against a temp dir, timer start/status/expiry/cancel, system-stat keys, mocked search success + network failure, every intent route, and every API endpoint (incl. LLM-without-key → `400`).

## 📁 Project structure

```
jarvis-ai-assistant/
├── backend/
│   ├── app.py        # FastAPI: /api/* routes, LLM tool-calling loop, serves the HUD
│   ├── brain.py      # Offline intent router (honest rule-based matching)
│   └── tools.py      # Real tool implementations + registry for /api/tools & LLM mode
├── frontend/
│   ├── index.html    # HUD layout
│   ├── style.css     # Iron Man aesthetic
│   └── app.js        # Voice in/out, chat, stats polling, settings (no build step)
├── tests/            # 42 pytest tests, no network
├── Dockerfile
└── .github/workflows/ci.yml
```

## ⚠️ Honest capabilities & limitations

- **Offline mode is rule-based**, not an LLM — it matches command patterns to tools. It says so in the UI.
- **LLM mode needs your own key** (or a free local endpoint like Ollama). Without one it tells you exactly that.
- **Speech recognition** needs Chrome/Edge (Web Speech API); the push-to-talk and typed input work everywhere.
- **Web search** uses DuckDuckGo's free Instant Answer API; if the network is down, JARVIS says so instead of hallucinating.
- This is a **prototype interface**, not a production assistant — built to demonstrate real full-stack + voice + LLM-tooling engineering.

## 📄 License

MIT — see [LICENSE](LICENSE).
