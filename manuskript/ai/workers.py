# --!-- coding: utf8 --!--
"""Background threads for chat streaming and model listing."""

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from manuskript.ai import providers as P


def _httpError(resp):
    try:
        body = resp.text.strip()
    except Exception:
        body = ""
    return "HTTP %s: %s" % (resp.status_code, body[:400])


class ChatWorker(QThread):
    chunk = pyqtSignal(str)
    thinking = pyqtSignal()
    usage = pyqtSignal(int, int)      # prompt tokens, output tokens
    failed = pyqtSignal(str)
    completed = pyqtSignal(bool)      # True if cancelled

    def __init__(self, req, parent=None):
        """req: dict with provider, endpoint, apiKey, model, system, history,
        temperature, thinking. Everything is frozen at send time."""
        QThread.__init__(self, parent)
        self.req = req
        self._cancel = False
        self._resp = None

    def cancel(self):
        self._cancel = True
        resp = self._resp
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def run(self):
        r = self.req
        prov = r["provider"]
        inTok = outTok = None
        text = ""
        resp = None
        try:
            payload = P.buildPayload(prov, r["model"], r["system"], r["history"],
                                     r.get("temperature"), r.get("thinking", "Off"))
            url = P.chatUrl(prov, r["endpoint"], r["model"])
            hdr = P.headers(prov, r["apiKey"])
            resp = requests.post(url, json=payload, headers=hdr,
                                 stream=True, timeout=(10, 600))
            self._resp = resp
            if resp.status_code != 200:
                if not self._cancel:
                    self.failed.emit(_httpError(resp))
                return
            for line in resp.iter_lines():
                if self._cancel:
                    break
                ev = P.parseStreamLine(prov, line)
                if ev is None:
                    continue
                if ev.error:
                    if not self._cancel:
                        self.failed.emit(ev.error)
                    return
                if ev.inTokens is not None:
                    inTok = ev.inTokens
                if ev.outTokens is not None:
                    outTok = ev.outTokens
                if ev.text:
                    text += ev.text
                    if not self._cancel:
                        self.chunk.emit(ev.text)
                elif ev.thinking:
                    if not self._cancel:
                        self.thinking.emit()
                if (inTok is not None or outTok is not None) and not self._cancel:
                    self.usage.emit(inTok or 0, outTok or 0)
                if ev.done:
                    break
            if not self._cancel and (inTok is None or outTok is None):
                joined = r["system"] + "".join(m["content"] for m in r["history"])
                self.usage.emit(inTok if inTok is not None else P.estimateTokens(joined),
                                outTok if outTok is not None else P.estimateTokens(text))
            self.completed.emit(self._cancel)
        except BaseException as e:
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            if self._cancel:
                self.completed.emit(True)
            else:
                self.failed.emit("%s: %s" % (type(e).__name__, str(e)[:300]))
        finally:
            self._resp = None
            if resp is not None:
                try:
                    resp.close()
                except Exception:
                    pass


class ModelsWorker(QThread):
    done = pyqtSignal(str, list)      # provider, model names
    failed = pyqtSignal(str, str)     # provider, message

    def __init__(self, provider, endpoint, apiKey, parent=None):
        QThread.__init__(self, parent)
        self.provider, self.endpoint, self.apiKey = provider, endpoint, apiKey

    def run(self):
        try:
            resp = requests.get(P.modelsUrl(self.provider, self.endpoint),
                                headers=P.headers(self.provider, self.apiKey),
                                timeout=15)
            if resp.status_code != 200:
                self.failed.emit(self.provider, _httpError(resp))
                return
            self.done.emit(self.provider, P.parseModels(self.provider, resp.json()))
        except BaseException as e:
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise
            self.failed.emit(self.provider, "%s: %s" % (type(e).__name__, str(e)[:200]))
