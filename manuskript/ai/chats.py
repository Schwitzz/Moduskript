# --!-- coding: utf8 --!--
"""Chat history stored as JSON files OUTSIDE the project folder.

Manuskript may delete and rewrite a project folder when saving, so chats
live in the app data directory and are tagged with the project path.
"""

import json
import os
import time
import uuid


class ChatStore:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, chatId):
        return os.path.join(self.folder, "%s.json" % chatId)

    @staticmethod
    def newId():
        return uuid.uuid4().hex[:12]

    @staticmethod
    def makeTitle(agent, firstPrompt):
        words = " ".join((firstPrompt or "").split())
        if len(words) > 40:
            words = words[:40].rstrip() + "..."
        return "%s: %s" % (agent, words or "New chat")

    def save(self, chat):
        """chat: dict with id, title, project, messages. Atomic write."""
        chat["updated"] = time.time()
        chat.setdefault("created", chat["updated"])
        tmp = self._path(chat["id"]) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(chat, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path(chat["id"]))

    def load(self, chatId):
        try:
            with open(self._path(chatId), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def delete(self, chatId):
        try:
            os.remove(self._path(chatId))
        except OSError:
            pass

    def list(self, project=None):
        """Newest first. If `project` is given, only that project's chats."""
        out = []
        for name in os.listdir(self.folder):
            if not name.endswith(".json"):
                continue
            chat = self.load(name[:-5])
            if not chat or "id" not in chat:
                continue
            if project is not None and chat.get("project") != project:
                continue
            out.append(chat)
        out.sort(key=lambda c: c.get("updated", 0), reverse=True)
        return out
