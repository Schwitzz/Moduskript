# --!-- coding: utf8 --!--
"""App-wide AI settings, synced between QSettings and the shared Web Server AI directory."""

import json
from pathlib import Path

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import qApp

from moduskript.ai import providers as P

ROLES = ["Co-author", "Editor", "Publisher", "Reader"]

DEFAULT_PROMPTS = {
    "Co-author": (
        "You are a creative co-author. Help brainstorm, expand scenes and "
        "improve narrative flow. Offer concrete creative suggestions, keep "
        "the author's voice and push the story forward organically."),
    "Editor": (
        "You are a professional literary editor. Focus on pacing, grammar, "
        "structural consistency and clarity. Point out passive voice and "
        "repetitive phrasing, and offer precise rewrites that tighten the prose."),
    "Publisher": (
        "You are a commercial book publisher. Assess marketability, genre "
        "expectations, hook strength and audience appeal, and explain how to "
        "make the story more commercially viable."),
    "Reader": (
        "You are an avid reader of this genre. Give honest emotional "
        "reactions, say where you are confused or bored, and highlight your "
        "favourite moments, as a fan reading the story for the first time."),
}

KEY_NAMES = {P.LOCAL: "keyLocal", P.OPENAI: "keyOpenAI",
             P.ANTHROPIC: "keyAnthropic", P.GEMINI: "keyGemini"}
MODEL_NAMES = {P.LOCAL: "modelLocal", P.OPENAI: "modelOpenAI",
               P.ANTHROPIC: "modelAnthropic", P.GEMINI: "modelGemini"}


def _qs():
    return QSettings(qApp.organizationName(), qApp.applicationName())


def _get(name, default, typ=str):
    s = _qs()
    s.beginGroup("AI")
    try:
        return s.value(name, default, type=typ)
    finally:
        s.endGroup()


def _set(name, value):
    s = _qs()
    s.beginGroup("AI")
    s.setValue(name, value)
    s.endGroup()
    s.sync()


def shared_ai_dir() -> Path:
    """Return the shared `<dataDir>/ai` directory used by both Desktop and Web Server."""
    try:
        from moduskript.web_server import WebServerConfig
        d = Path(WebServerConfig.dataDir()) / "ai"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        from moduskript.functions import writablePath
        d = Path(writablePath("ai"))
        d.mkdir(parents=True, exist_ok=True)
        return d


def _read_shared_json(filename: str) -> dict:
    p = shared_ai_dir() / filename
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_shared_json(filename: str, data: dict) -> None:
    try:
        p = shared_ai_dir() / filename
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


class AISettings:
    """Static accessors synced between QSettings and `<dataDir>/ai/*.json`."""

    @staticmethod
    def _provider_entry(prov: str) -> dict:
        data = _read_shared_json("ai_providers.json")
        entry = data.get(prov)
        return entry if isinstance(entry, dict) else {}

    @staticmethod
    def _update_provider_entry(prov: str, **updates) -> None:
        data = _read_shared_json("ai_providers.json")
        for p in P.PROVIDERS:
            if p not in data or not isinstance(data[p], dict):
                data[p] = {
                    "api_key": _get(KEY_NAMES[p], ""),
                    "model": _get(MODEL_NAMES[p], ""),
                    "endpoint": _get("endpoint", "http://127.0.0.1:8080") if p == P.LOCAL else "",
                    "context_size": _get("contextSize", 8192, int),
                    "temperature": _get("temperature", 0.7, float),
                    "thinking": _get("thinking", "Off"),
                }
        cur = dict(data.get(prov, {}))
        cur.update(updates)
        data[prov] = cur
        _write_shared_json("ai_providers.json", data)

    @staticmethod
    def provider():
        data = _read_shared_json("ai_providers.json")
        shared_p = data.get("_active_provider")
        if shared_p in P.PROVIDERS:
            return shared_p
        p = _get("provider", P.LOCAL)
        return p if p in P.PROVIDERS else P.LOCAL

    @staticmethod
    def setProvider(v):
        _set("provider", v)
        data = _read_shared_json("ai_providers.json")
        data["_active_provider"] = v
        _write_shared_json("ai_providers.json", data)

    @staticmethod
    def endpoint():
        entry = AISettings._provider_entry(P.LOCAL)
        if entry.get("endpoint"):
            return str(entry["endpoint"]).strip()
        return _get("endpoint", "http://127.0.0.1:8080")

    @staticmethod
    def setEndpoint(v):
        val = v.strip()
        _set("endpoint", val)
        AISettings._update_provider_entry(P.LOCAL, endpoint=val)

    @staticmethod
    def apiKey(provider):
        entry = AISettings._provider_entry(provider)
        if entry.get("api_key"):
            return str(entry["api_key"]).strip()
        return _get(KEY_NAMES[provider], "")

    @staticmethod
    def setApiKey(provider, v):
        val = v.strip()
        _set(KEY_NAMES[provider], val)
        AISettings._update_provider_entry(provider, api_key=val)

    @staticmethod
    def model(provider):
        entry = AISettings._provider_entry(provider)
        if entry.get("model"):
            return str(entry["model"]).strip()
        return _get(MODEL_NAMES[provider], "")

    @staticmethod
    def setModel(provider, v):
        val = v.strip()
        _set(MODEL_NAMES[provider], val)
        AISettings._update_provider_entry(provider, model=val)

    @staticmethod
    def cachedModels(provider):
        """Last model list fetched for `provider` (shared by dock, settings, and Web)."""
        try:
            names = json.loads(_get("modelCache" + KEY_NAMES[provider], "[]"))
        except ValueError:
            names = []
        if isinstance(names, list) and names:
            return [n for n in names if isinstance(n, str)]
        cache = _read_shared_json("ai_models_cache.json")
        for k, v in cache.items():
            if k.startswith(provider + "|") and isinstance(v, dict):
                m = v.get("models", [])
                if isinstance(m, list) and m:
                    return [n for n in m if isinstance(n, str)]
        return []

    @staticmethod
    def setCachedModels(provider, names):
        clean = [n for n in names if isinstance(n, str)]
        _set("modelCache" + KEY_NAMES[provider], json.dumps(clean))
        cache = _read_shared_json("ai_models_cache.json")
        ep = AISettings.endpoint() if provider == P.LOCAL else ""
        import time
        cache[f"{provider}|{ep}"] = {"ts": time.time(), "models": clean}
        _write_shared_json("ai_models_cache.json", cache)

    @staticmethod
    def contextSize():
        entry = AISettings._provider_entry(P.LOCAL)
        if isinstance(entry.get("context_size"), int) and entry["context_size"] >= 512:
            return int(entry["context_size"])
        return _get("contextSize", 8192, int)

    @staticmethod
    def setContextSize(v):
        val = int(v)
        _set("contextSize", val)
        AISettings._update_provider_entry(P.LOCAL, context_size=val)

    @staticmethod
    def temperature():
        entry = AISettings._provider_entry(P.LOCAL)
        if isinstance(entry.get("temperature"), (int, float)):
            return float(entry["temperature"])
        return _get("temperature", 0.7, float)

    @staticmethod
    def setTemperature(v):
        val = float(v)
        _set("temperature", val)
        AISettings._update_provider_entry(P.LOCAL, temperature=val)

    @staticmethod
    def thinking():
        entry = AISettings._provider_entry(P.LOCAL)
        t = entry.get("thinking")
        if t in P.THINKING_LEVELS:
            return t
        v = _get("thinking", "Off")
        return v if v in P.THINKING_LEVELS else "Off"

    @staticmethod
    def setThinking(v):
        _set("thinking", v)
        AISettings._update_provider_entry(P.LOCAL, thinking=v)

    @staticmethod
    def role():
        data = _read_shared_json("ai_providers.json")
        r = data.get("_active_role") or _get("role", "Co-author")
        return r if r in ROLES else "Co-author"

    @staticmethod
    def setRole(v):
        _set("role", v)
        data = _read_shared_json("ai_providers.json")
        data["_active_role"] = v
        _write_shared_json("ai_providers.json", data)

    @staticmethod
    def prompt(role):
        agents = _read_shared_json("ai_agents.json")
        if isinstance(agents.get(role), str) and agents[role].strip():
            return agents[role]
        return _get("prompt" + role.replace("-", ""), DEFAULT_PROMPTS[role])

    @staticmethod
    def setPrompt(role, v):
        _set("prompt" + role.replace("-", ""), v)
        agents = _read_shared_json("ai_agents.json")
        agents[role] = v
        _write_shared_json("ai_agents.json", agents)

    @staticmethod
    def ctxFlag(name):
        """Context source toggles: selection, scene, summary, pov, book."""
        return _get("ctx_" + name, True, bool)

    @staticmethod
    def setCtxFlag(name, v):
        _set("ctx_" + name, bool(v))
