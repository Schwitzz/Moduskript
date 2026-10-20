# --!-- coding: utf8 --!--
"""Chat history synced between Desktop JSON files and the shared Web Server SQLite database (`chats.db`)."""

import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


def normalize_project_key(project: str | None) -> str:
    """Normalize a project path or name to a canonical project stem (e.g. '/a/b/Draft-0001.msk' -> 'Draft-0001')."""
    if not project:
        return ""
    s = str(project).strip().rstrip("/\\")
    if not s:
        return ""
    p = Path(s)
    if p.name.upper() == "MANUSKRIPT":
        p = p.parent
    stem = p.stem if p.suffix.lower() == ".msk" else p.name
    return stem


class ChatStore:
    def __init__(self, folder, db_path=None):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        if db_path is None:
            try:
                from moduskript.ai.config import shared_ai_dir
                self.db_path = str(shared_ai_dir() / "chats.db")
            except Exception:
                self.db_path = os.path.join(self.folder, "chats.db")
        else:
            self.db_path = str(db_path)
        self._init_db()
        self._migrate_json_files_to_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
        return conn

    def _init_db(self):
        try:
            with self._connect() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS chats (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        project TEXT NOT NULL,
                        created REAL NOT NULL,
                        updated REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        agent TEXT,
                        created REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id);
                    CREATE INDEX IF NOT EXISTS idx_chats_project ON chats(project);
                    CREATE INDEX IF NOT EXISTS idx_chats_updated ON chats(updated DESC);
                """)
                conn.commit()
        except Exception:
            pass

    def _migrate_json_files_to_db(self):
        """Import any legacy Desktop JSON chat files into the shared SQLite `chats.db`."""
        try:
            for name in os.listdir(self.folder):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(self.folder, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        chat = json.load(f)
                except (OSError, ValueError):
                    continue
                if not isinstance(chat, dict) or "id" not in chat:
                    continue
                if self._load_from_db(chat["id"]) is None:
                    self._save_to_db(chat)
        except Exception:
            pass

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

    def _save_to_db(self, chat):
        now = time.time()
        updated = float(chat.get("updated", now))
        created = float(chat.get("created", updated))
        proj_key = normalize_project_key(chat.get("project", ""))
        title = chat.get("title") or "New chat"
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO chats (id, title, project, created, updated) VALUES (?, ?, ?, ?, ?)",
                    (chat["id"], title, proj_key, created, updated),
                )
                conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat["id"],))
                for msg in chat.get("messages", []):
                    conn.execute(
                        "INSERT INTO messages (chat_id, role, content, agent, created) VALUES (?, ?, ?, ?, ?)",
                        (
                            chat["id"],
                            msg.get("role", "user"),
                            msg.get("content", ""),
                            msg.get("agent"),
                            float(msg.get("created", updated)),
                        ),
                    )
                conn.commit()
        except Exception:
            pass

    def _load_from_db(self, chatId):
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT id, title, project, created, updated FROM chats WHERE id = ?",
                    (chatId,),
                ).fetchone()
                if not row:
                    return None
                messages = conn.execute(
                    "SELECT role, content, agent, created FROM messages WHERE chat_id = ? ORDER BY rowid",
                    (chatId,),
                ).fetchall()
                return {
                    "id": row[0],
                    "title": row[1],
                    "project": row[2],
                    "created": row[3],
                    "updated": row[4],
                    "messages": [
                        {"role": r[0], "content": r[1], "agent": r[2], "created": r[3]}
                        for r in messages
                    ],
                }
        except Exception:
            return None

    def save(self, chat):
        """chat: dict with id, title, project, messages. Atomic write to JSON + shared SQLite DB."""
        chat["updated"] = time.time()
        chat.setdefault("created", chat["updated"])
        chat["project"] = normalize_project_key(chat.get("project", ""))
        tmp = self._path(chat["id"]) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(chat, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path(chat["id"]))
        self._save_to_db(chat)

    def load(self, chatId):
        db_chat = self._load_from_db(chatId)
        if db_chat is not None:
            return db_chat
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
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM messages WHERE chat_id = ?", (chatId,))
                conn.execute("DELETE FROM chats WHERE id = ?", (chatId,))
                conn.commit()
        except Exception:
            pass

    def list(self, project=None):
        """Newest first. Merges shared SQLite DB chats and local JSON chats for the project."""
        by_id = {}
        want_key = normalize_project_key(project) if project is not None else None
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, title, project, created, updated FROM chats ORDER BY updated DESC"
                ).fetchall()
                for r in rows:
                    c_proj = normalize_project_key(r[2])
                    if want_key is not None and want_key != "" and c_proj != want_key:
                        continue
                    by_id[r[0]] = {
                        "id": r[0],
                        "title": r[1],
                        "project": c_proj,
                        "created": r[3],
                        "updated": r[4],
                    }
        except Exception:
            pass

        for name in os.listdir(self.folder):
            if not name.endswith(".json"):
                continue
            try:
                with open(self._path(name[:-5]), encoding="utf-8") as f:
                    chat = json.load(f)
            except (OSError, ValueError):
                continue
            if not chat or "id" not in chat:
                continue
            c_proj = normalize_project_key(chat.get("project", ""))
            if want_key is not None and want_key != "" and c_proj != want_key:
                continue
            if chat["id"] not in by_id or chat.get("updated", 0) > by_id[chat["id"]].get("updated", 0):
                by_id[chat["id"]] = chat

        out = list(by_id.values())
        out.sort(key=lambda c: c.get("updated", 0), reverse=True)
        return out
