# --!-- coding: utf8 --!--
"""LLM provider definitions: URLs, headers, payloads, stream parsing.

This module has no Qt dependency so it can be unit tested on its own.
Cloud base URLs are hardcoded; only the local provider uses a user URL.
"""

import json

LOCAL = "Local / Llama.cpp"
OPENAI = "OpenAI"
ANTHROPIC = "Anthropic"
GEMINI = "Google Gemini"
PROVIDERS = [LOCAL, OPENAI, ANTHROPIC, GEMINI]

OPENAI_BASE = "https://api.openai.com/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = 4096

THINKING_LEVELS = ["Off", "low", "med", "high", "xhigh"]
REASONING_MAP = {"low": "low", "med": "medium", "high": "high", "xhigh": "high"}


def estimateTokens(text):
    """Rough token estimate used only when a provider reports no usage."""
    return max(1, int(len(text) / 3.5)) if text else 0


def localBase(endpoint):
    """Normalise a user supplied server URL to one ending in /v1."""
    base = (endpoint or "").strip().rstrip("/")
    if base.endswith("/v1"):
        return base
    return base + "/v1"


def chatUrl(provider, endpoint, model):
    if provider == OPENAI:
        return OPENAI_BASE + "/chat/completions"
    if provider == ANTHROPIC:
        return ANTHROPIC_BASE + "/messages"
    if provider == GEMINI:
        return "%s/models/%s:streamGenerateContent?alt=sse" % (
            GEMINI_BASE, _geminiName(model))
    return localBase(endpoint) + "/chat/completions"


def modelsUrl(provider, endpoint):
    if provider == OPENAI:
        return OPENAI_BASE + "/models"
    if provider == ANTHROPIC:
        return ANTHROPIC_BASE + "/models?limit=1000"
    if provider == GEMINI:
        return GEMINI_BASE + "/models?pageSize=1000"
    return localBase(endpoint) + "/models"


def headers(provider, apiKey):
    h = {"Content-Type": "application/json"}
    if provider == ANTHROPIC:
        h["x-api-key"] = apiKey
        h["anthropic-version"] = ANTHROPIC_VERSION
    elif provider == GEMINI:
        h["x-goog-api-key"] = apiKey
    elif apiKey:
        h["Authorization"] = "Bearer " + apiKey
    return h


def _geminiName(model):
    model = model or ""
    return model[len("models/"):] if model.startswith("models/") else model


def buildPayload(provider, model, system, history, temperature=None,
                 thinking="Off"):
    """Build the JSON body. `history` is a list of {role, content} dicts
    (role is 'user' or 'assistant'; extra keys such as 'agent' are ignored).
    Context size, temperature and thinking are sent to the local server only.
    """
    msgs = [{"role": m["role"], "content": m["content"]} for m in history]

    if provider == ANTHROPIC:
        payload = {"model": model, "max_tokens": ANTHROPIC_MAX_TOKENS,
                   "stream": True, "messages": msgs}
        if system:
            payload["system"] = system
        return payload

    if provider == GEMINI:
        payload = {"contents": [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]} for m in msgs]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    full = ([{"role": "system", "content": system}] if system else []) + msgs
    payload = {"model": model, "messages": full, "stream": True,
               "stream_options": {"include_usage": True}}
    if provider == LOCAL:
        if temperature is not None:
            payload["temperature"] = temperature
        if thinking == "Off":
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        elif thinking in REASONING_MAP:
            payload["reasoning_effort"] = REASONING_MAP[thinking]
    return payload


class StreamEvent:
    """Result of parsing one SSE data line."""

    def __init__(self, text="", thinking=False, inTokens=None,
                 outTokens=None, done=False, error=""):
        self.text = text
        self.thinking = thinking  # True while only reasoning is streaming
        self.inTokens = inTokens
        self.outTokens = outTokens
        self.done = done
        self.error = error


def parseStreamLine(provider, line):
    """Parse one raw line of an SSE stream. Returns StreamEvent or None."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    line = line.strip()
    if not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if data == "[DONE]":
        return StreamEvent(done=True)
    try:
        obj = json.loads(data)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    if "error" in obj:
        err = obj["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return StreamEvent(error=msg)

    if provider == ANTHROPIC:
        kind = obj.get("type")
        if kind == "content_block_delta":
            delta = obj.get("delta", {})
            if delta.get("type") == "thinking_delta":
                return StreamEvent(thinking=True)
            return StreamEvent(text=delta.get("text", ""))
        if kind == "message_start":
            use = obj.get("message", {}).get("usage", {})
            return StreamEvent(inTokens=use.get("input_tokens"))
        if kind == "message_delta":
            use = obj.get("usage", {})
            return StreamEvent(outTokens=use.get("output_tokens"))
        if kind == "message_stop":
            return StreamEvent(done=True)
        return None

    if provider == GEMINI:
        text = ""
        thinking = False
        for cand in obj.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if part.get("thought"):
                    thinking = True
                else:
                    text += part.get("text", "")
        use = obj.get("usageMetadata")
        return StreamEvent(
            text=text, thinking=thinking and not text,
            inTokens=use.get("promptTokenCount") if use else None,
            outTokens=use.get("candidatesTokenCount") if use else None)

    # OpenAI-compatible (OpenAI and local llama.cpp)
    use = obj.get("usage")
    inTok = use.get("prompt_tokens") if use else None
    outTok = use.get("completion_tokens") if use else None
    text, thinking = "", False
    for choice in obj.get("choices", []):
        delta = choice.get("delta") or {}
        text += delta.get("content") or ""
        if not text and (delta.get("reasoning_content") or delta.get("reasoning")):
            thinking = True
    return StreamEvent(text=text, thinking=thinking, inTokens=inTok,
                       outTokens=outTok)


def parseModels(provider, obj):
    """Extract a sorted list of model ids from a /models response."""
    names = []
    if provider == GEMINI:
        for m in obj.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(_geminiName(m.get("name", "")))
    else:
        for m in obj.get("data", obj.get("models", [])):
            if isinstance(m, dict):
                name = m.get("id") or m.get("name") or m.get("model")
                if name:
                    names.append(name)
    return sorted(set(names))
