import json
import importlib.util
import os

# Load providers.py directly so the test needs no PyQt5 / Manuskript app.
_p = os.path.join(os.path.dirname(__file__), "..", "providers.py")
_spec = importlib.util.spec_from_file_location("ai_providers", _p)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)


def sse(obj):
    return "data: " + json.dumps(obj)


def test_urls_cloud_are_hardcoded():
    assert P.chatUrl(P.OPENAI, "http://x", "m") == "https://api.openai.com/v1/chat/completions"
    assert P.chatUrl(P.ANTHROPIC, "http://x", "m") == "https://api.anthropic.com/v1/messages"
    assert "x-goog" not in P.chatUrl(P.GEMINI, "", "models/g")
    assert "key=" not in P.chatUrl(P.GEMINI, "", "models/g")
    assert P.chatUrl(P.GEMINI, "", "models/g").startswith(
        "https://generativelanguage.googleapis.com/v1beta/models/g:")


def test_local_url_normalised():
    for ep in ("http://h:1", "http://h:1/", "http://h:1/v1", "http://h:1/v1/"):
        assert P.chatUrl(P.LOCAL, ep, "m") == "http://h:1/v1/chat/completions"
        assert P.modelsUrl(P.LOCAL, ep) == "http://h:1/v1/models"


def test_headers():
    assert P.headers(P.ANTHROPIC, "k")["x-api-key"] == "k"
    assert P.headers(P.GEMINI, "k")["x-goog-api-key"] == "k"
    assert P.headers(P.OPENAI, "k")["Authorization"] == "Bearer k"
    assert "Authorization" not in P.headers(P.LOCAL, "")


def test_anthropic_payload_has_max_tokens_and_top_level_system():
    pl = P.buildPayload(P.ANTHROPIC, "c", "SYS", [{"role": "user", "content": "hi"}], 0.5, "high")
    assert pl["max_tokens"] > 0 and pl["system"] == "SYS"
    assert all(m["role"] != "system" for m in pl["messages"])
    assert "temperature" not in pl


def test_cloud_payloads_omit_local_options():
    for prov in (P.OPENAI, P.ANTHROPIC, P.GEMINI):
        pl = P.buildPayload(prov, "m", "S", [], 0.5, "high")
        assert "temperature" not in pl and "reasoning_effort" not in pl
        assert "chat_template_kwargs" not in pl


def test_local_payload_options():
    off = P.buildPayload(P.LOCAL, "m", "S", [], 0.3, "Off")
    assert off["temperature"] == 0.3
    assert off["chat_template_kwargs"] == {"enable_thinking": False}
    hi = P.buildPayload(P.LOCAL, "m", "S", [], 0.3, "xhigh")
    assert hi["reasoning_effort"] == "high" and "chat_template_kwargs" not in hi


def test_history_agent_key_not_sent():
    pl = P.buildPayload(P.OPENAI, "m", "S", [{"role": "assistant", "content": "a", "agent": "Editor"}])
    assert pl["messages"][1] == {"role": "assistant", "content": "a"}


def test_parse_openai_stream_and_usage():
    ev = P.parseStreamLine(P.OPENAI, sse({"choices": [{"delta": {"content": "Hi"}}]}))
    assert ev.text == "Hi"
    ev = P.parseStreamLine(P.OPENAI, sse({"choices": [], "usage": {"prompt_tokens": 5, "completion_tokens": 7}}))
    assert (ev.inTokens, ev.outTokens) == (5, 7)
    assert P.parseStreamLine(P.OPENAI, "data: [DONE]").done
    assert P.parseStreamLine(P.OPENAI, ": keepalive") is None


def test_parse_reasoning_flag():
    ev = P.parseStreamLine(P.LOCAL, sse({"choices": [{"delta": {"reasoning_content": "hmm"}}]}))
    assert ev.thinking and ev.text == ""


def test_parse_anthropic_delta_text():
    ev = P.parseStreamLine(P.ANTHROPIC, sse({"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Yo"}}))
    assert ev.text == "Yo"
    ev = P.parseStreamLine(P.ANTHROPIC, sse({"type": "message_start", "message": {"usage": {"input_tokens": 9}}}))
    assert ev.inTokens == 9
    ev = P.parseStreamLine(P.ANTHROPIC, sse({"type": "message_delta", "usage": {"output_tokens": 4}}))
    assert ev.outTokens == 4


def test_parse_gemini():
    ev = P.parseStreamLine(P.GEMINI, sse({"candidates": [{"content": {"parts": [{"text": "Hey"}]}}],
                                         "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 1}}))
    assert ev.text == "Hey" and (ev.inTokens, ev.outTokens) == (3, 1)


def test_error_event():
    ev = P.parseStreamLine(P.OPENAI, sse({"error": {"message": "no credits"}}))
    assert ev.error == "no credits"


def test_parse_models():
    assert P.parseModels(P.OPENAI, {"data": [{"id": "b"}, {"id": "a"}]}) == ["a", "b"]
    g = {"models": [{"name": "models/g1", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/emb", "supportedGenerationMethods": ["embedContent"]}]}
    assert P.parseModels(P.GEMINI, g) == ["g1"]
