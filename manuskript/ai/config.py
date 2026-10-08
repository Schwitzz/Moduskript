# --!-- coding: utf8 --!--
"""App-wide AI settings, stored in QSettings (never in the project)."""

import json

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import qApp

from manuskript.ai import providers as P

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


class AISettings:
    """Static accessors so every widget sees the same live values."""

    @staticmethod
    def provider():
        p = _get("provider", P.LOCAL)
        return p if p in P.PROVIDERS else P.LOCAL

    @staticmethod
    def setProvider(v):
        _set("provider", v)

    @staticmethod
    def endpoint():
        return _get("endpoint", "http://127.0.0.1:8080")

    @staticmethod
    def setEndpoint(v):
        _set("endpoint", v.strip())

    @staticmethod
    def apiKey(provider):
        return _get(KEY_NAMES[provider], "")

    @staticmethod
    def setApiKey(provider, v):
        _set(KEY_NAMES[provider], v.strip())

    @staticmethod
    def model(provider):
        return _get(MODEL_NAMES[provider], "")

    @staticmethod
    def setModel(provider, v):
        _set(MODEL_NAMES[provider], v.strip())

    @staticmethod
    def cachedModels(provider):
        """Last model list fetched for `provider` (shared by dock and settings)."""
        try:
            names = json.loads(_get("modelCache" + KEY_NAMES[provider], "[]"))
        except ValueError:
            return []
        return [n for n in names if isinstance(n, str)] if isinstance(names, list) else []

    @staticmethod
    def setCachedModels(provider, names):
        _set("modelCache" + KEY_NAMES[provider], json.dumps(list(names)))

    @staticmethod
    def contextSize():
        return _get("contextSize", 8192, int)

    @staticmethod
    def setContextSize(v):
        _set("contextSize", int(v))

    @staticmethod
    def temperature():
        return _get("temperature", 0.7, float)

    @staticmethod
    def setTemperature(v):
        _set("temperature", float(v))

    @staticmethod
    def thinking():
        v = _get("thinking", "Off")
        return v if v in P.THINKING_LEVELS else "Off"

    @staticmethod
    def setThinking(v):
        _set("thinking", v)

    @staticmethod
    def role():
        r = _get("role", "Co-author")
        return r if r in ROLES else "Co-author"

    @staticmethod
    def setRole(v):
        _set("role", v)

    @staticmethod
    def prompt(role):
        return _get("prompt" + role.replace("-", ""), DEFAULT_PROMPTS[role])

    @staticmethod
    def setPrompt(role, v):
        _set("prompt" + role.replace("-", ""), v)

    @staticmethod
    def ctxFlag(name):
        """Context source toggles: selection, scene, summary, pov, book."""
        return _get("ctx_" + name, True, bool)

    @staticmethod
    def setCtxFlag(name, v):
        _set("ctx_" + name, bool(v))
