/* JARVIS HUD logic — voice in/out, chat, stats, settings. No build step. */
"use strict";

const $ = (id) => document.getElementById(id);
const chat = $("chat"), cmdInput = $("cmd");

/* ---------------- Settings (localStorage only) ---------------- */
const settings = {
  mode: localStorage.getItem("jarvis.mode") || "offline",
  baseUrl: localStorage.getItem("jarvis.baseUrl") || "https://api.openai.com/v1",
  apiKey: localStorage.getItem("jarvis.apiKey") || "",
  model: localStorage.getItem("jarvis.model") || "gpt-4o-mini",
};
$("llmUrl").value = settings.baseUrl;
$("llmModel").value = settings.model;
if (settings.apiKey) $("llmKey").value = settings.apiKey;

function applyMode() {
  $("modeOffline").classList.toggle("active", settings.mode === "offline");
  $("modeLLM").classList.toggle("active", settings.mode === "llm");
  $("modeLabel").textContent = settings.mode === "offline" ? "OFFLINE COMMAND MODE" : "LLM BRAIN MODE";
  $("modeDesc").textContent = settings.mode === "offline"
    ? "Offline command mode: fast, private, rule-based routing. No key needed."
    : "LLM brain mode: open-ended conversation with real tool calling. Requires your key in settings.";
  localStorage.setItem("jarvis.mode", settings.mode);
}
$("modeOffline").onclick = () => { settings.mode = "offline"; applyMode(); };
$("modeLLM").onclick = () => { settings.mode = "llm"; applyMode(); };
$("saveSettings").onclick = () => {
  settings.baseUrl = $("llmUrl").value.trim() || "https://api.openai.com/v1";
  settings.apiKey = $("llmKey").value.trim();
  settings.model = $("llmModel").value.trim() || "gpt-4o-mini";
  localStorage.setItem("jarvis.baseUrl", settings.baseUrl);
  localStorage.setItem("jarvis.apiKey", settings.apiKey);
  localStorage.setItem("jarvis.model", settings.model);
  addMsg("jarvis", "Settings saved, sir. Your key never leaves this browser except to your chosen endpoint.");
};
applyMode();

/* ---------------- Boot sequence ---------------- */
const BOOT_LINES = [
  "Initializing J.A.R.V.I.S. interface…",
  "Loading offline intent router… OK",
  "Binding tool suite [time, stats, search, calc, notes, timer, joke]… OK",
  "Calibrating arc reactor… 98.7%",
  "Voice modules: STT ready · TTS ready",
  "All systems nominal. Awaiting your command, sir.",
];
(function boot() {
  const el = $("bootlog");
  BOOT_LINES.forEach((line, i) => setTimeout(() => { el.textContent += line + "\n"; el.scrollTop = el.scrollHeight; }, 320 * (i + 1)));
})();

/* ---------------- Clock ---------------- */
setInterval(() => {
  $("clock").textContent = new Date().toLocaleTimeString("en-GB");
}, 1000);

/* ---------------- Chat ---------------- */
function addMsg(who, text) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  const label = document.createElement("span");
  label.className = "who mono";
  label.textContent = who === "jarvis" ? "J.A.R.V.I.S." : "YOU";
  div.appendChild(label);
  div.appendChild(document.createTextNode(text));
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function sendCommand(text) {
  const clean = text.trim();
  if (!clean) return;
  addMsg("user", clean);
  cmdInput.value = "";
  const typing = addMsg("jarvis", "▌");
  typing.classList.add("typing");
  try {
    let resp;
    if (settings.mode === "llm") {
      resp = await fetch("/api/llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean, base_url: settings.baseUrl, api_key: settings.apiKey, model: settings.model }),
      });
      const data = await resp.json();
      typing.remove();
      if (!resp.ok) { addMsg("jarvis", data.detail || "LLM request failed, sir."); return; }
      addMsg("jarvis", data.response);
    } else {
      resp = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean }),
      });
      const data = await resp.json();
      typing.remove();
      addMsg("jarvis", data.response || "(no response)");
    }
    const last = chat.lastElementChild;
    if (last && last.classList.contains("jarvis")) speak(last.textContent.replace(/^J\.A\.R\.V\.I\.S\./, ""));
  } catch (e) {
    typing.remove();
    addMsg("jarvis", "I'm having trouble reaching my own backend, sir. Is the server running?");
  }
}
$("sendBtn").onclick = () => sendCommand(cmdInput.value);
cmdInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendCommand(cmdInput.value); });

/* ---------------- Voice OUT (speechSynthesis) ---------------- */
let voiceOn = true, jarvisVoice = null;
function pickVoice() {
  const voices = speechSynthesis.getVoices();
  jarvisVoice = voices.find((v) => v.lang.startsWith("en-GB") && /male|daniel|george|brian/i.test(v.name))
    || voices.find((v) => v.lang.startsWith("en-GB"))
    || voices.find((v) => v.lang.startsWith("en")) || null;
}
if ("speechSynthesis" in window) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
function speak(text) {
  if (!voiceOn || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.slice(0, 400));
  if (jarvisVoice) u.voice = jarvisVoice;
  u.rate = 1.02; u.pitch = 0.95;
  speechSynthesis.speak(u);
}
$("muteBtn").onclick = () => {
  voiceOn = !voiceOn;
  if (!voiceOn) speechSynthesis.cancel();
  $("muteBtn").textContent = voiceOn ? "🔊 VOICE ON" : "🔇 VOICE OFF";
};

/* ---------------- Voice IN (SpeechRecognition) + waveform ---------------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null, wakeMode = false, micStream = null, analyser = null;

function initWaveform(stream) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaStreamSource(stream);
  analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  src.connect(analyser);
  const canvas = $("waveform"), g = canvas.getContext("2d");
  const data = new Uint8Array(analyser.frequencyBinCount);
  (function draw() {
    requestAnimationFrame(draw);
    analyser.getByteFrequencyData(data);
    g.clearRect(0, 0, canvas.width, canvas.height);
    const n = data.length, w = canvas.width / n;
    for (let i = 0; i < n; i++) {
      const h = (data[i] / 255) * canvas.height;
      g.fillStyle = "rgba(0,212,255,.85)";
      g.fillRect(i * w, canvas.height - h, w - 1, h);
    }
  })();
}

async function ensureMic() {
  if (micStream) return micStream;
  micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  initWaveform(micStream);
  return micStream;
}

function makeRecognizer(continuous, onFinal) {
  const r = new SR();
  r.lang = "en-US";
  r.continuous = continuous;
  r.interimResults = true;
  r.onresult = (e) => {
    let interim = "", final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
      else interim += e.results[i][0].transcript;
    }
    cmdInput.value = (final || interim).trim();
    cmdInput.placeholder = interim ? "hearing: " + interim.slice(-40) : "Type a command, sir… (or speak)";
    if (final) onFinal(final.trim());
  };
  r.onerror = (e) => { if (e.error === "not-allowed") addMsg("jarvis", "Microphone access was denied, sir. Check your browser permissions."); };
  return r;
}

$("pttBtn").onclick = async () => {
  if (!SR) { addMsg("jarvis", "Speech recognition isn't supported in this browser, sir. Try Chrome."); return; }
  try { await ensureMic(); } catch { addMsg("jarvis", "I couldn't access the microphone, sir."); return; }
  if (recog) { recog.stop(); recog = null; $("pttBtn").classList.remove("active"); return; }
  recog = makeRecognizer(false, (text) => { recog.stop(); recog = null; $("pttBtn").classList.remove("active"); sendCommand(text); });
  recog.start();
  $("pttBtn").classList.add("active");
  addMsg("jarvis", "Listening, sir. Speak now.");
};

$("wakeBtn").onclick = async () => {
  if (!SR) { addMsg("jarvis", "Speech recognition isn't supported in this browser, sir. Try Chrome."); return; }
  wakeMode = !wakeMode;
  $("wakeBtn").classList.toggle("active", wakeMode);
  if (wakeMode) {
    try { await ensureMic(); } catch { addMsg("jarvis", "I couldn't access the microphone, sir."); wakeMode = false; return; }
    addMsg("jarvis", "Wake-word listening engaged. Say “Hey Jarvis” followed by your command.");
    const listen = () => {
      if (!wakeMode) return;
      const r = makeRecognizer(true, (text) => {
        const m = text.toLowerCase().match(/(?:hey\s+)?jarvis[,\s]+(.+)/);
        if (m && m[1]) { r.stop(); sendCommand(m[1]); setTimeout(listen, 1500); }
      });
      r.onend = () => { if (wakeMode) setTimeout(listen, 400); };
      r.start();
    };
    listen();
  } else {
    addMsg("jarvis", "Wake-word listening disengaged, sir.");
  }
};

/* ---------------- System stats polling ---------------- */
async function pollStats() {
  try {
    const resp = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "system status" }),
    });
    const data = await resp.json();
    const s = data.data && data.data.stats;
    if (!s) return;
    $("cpuBar").style.width = s.cpu_percent + "%"; $("cpuVal").textContent = s.cpu_percent + "%";
    $("memBar").style.width = s.memory_percent + "%"; $("memVal").textContent = s.memory_percent + "%";
    $("diskBar").style.width = s.disk_percent + "%"; $("diskVal").textContent = s.disk_percent + "%";
  } catch { /* server not up yet — retry next tick */ }
}
pollStats();
setInterval(pollStats, 3000);

/* ---------------- Reactor reacts to voice ---------------- */
setInterval(() => {
  const core = $("reactorCore");
  if (!voiceOn) return;
  if (speechSynthesis.speaking) core.style.animationDuration = "0.9s";
  else core.style.animationDuration = "2.6s";
}, 500);

/* Greet on load */
setTimeout(() => addMsg("jarvis", "Good to see you, sir. All systems are now fully operational. Try “Hey Jarvis, tell me a joke.”"), 2400);
