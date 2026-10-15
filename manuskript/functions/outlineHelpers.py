#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Outline hierarchy, Chapter/Scene placement, and Associated Notes helpers.

Matches the exact logic in the Web App (`web/src/lib/outline.ts`).
"""

import json
import re
import time
import uuid

from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QStandardItem

from manuskript.enums import Outline
from manuskript.functions import iconFromColorString, toInt


def parse_associated_notes(raw):
    """Parse JSON string stored in Outline.associatedNotes into a list of dicts."""
    if not raw or not str(raw).strip():
        return []
    try:
        parsed = json.loads(str(raw))
        if not isinstance(parsed, list):
            return []
        out = []
        for idx, n in enumerate(parsed):
            if isinstance(n, dict) and isinstance(n.get("title"), str):
                nid = str(n.get("id")) if n.get("id") else f"note_{idx}"
                out.append({
                    "id": nid,
                    "title": str(n["title"]),
                    "text": str(n.get("text") or "")[:2000],
                })
        return out
    except Exception:
        return []


def dump_associated_notes(notes_list):
    """Serialize list of associated notes back to string ('' when empty)."""
    if not notes_list:
        return ""
    clean = []
    for idx, n in enumerate(notes_list):
        if isinstance(n, dict) and n.get("title"):
            clean.append({
                "id": str(n.get("id") or f"note_{int(time.time() * 1000)}_{idx}"),
                "title": str(n["title"]).strip(),
                "text": str(n.get("text") or "")[:2000],
            })
    return json.dumps(clean) if clean else ""


def add_associated_note(item, title, text=""):
    """Append a new associated note to an outlineItem and persist to Outline.associatedNotes."""
    if item is None:
        return None
    clean_title = (title or "").strip()
    if not clean_title:
        return None
    notes = parse_associated_notes(item.data(Outline.associatedNotes))
    new_note = {
        "id": f"note_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
        "title": clean_title,
        "text": (text or "")[:2000],
    }
    notes.append(new_note)
    item.setData(Outline.associatedNotes, dump_associated_notes(notes))
    return new_note


def update_associated_note(item, note_id, title=None, text=None):
    """Update an existing associated note on an outlineItem."""
    if item is None:
        return False
    notes = parse_associated_notes(item.data(Outline.associatedNotes))
    changed = False
    for n in notes:
        if n["id"] == note_id:
            if title is not None and title.strip():
                n["title"] = title.strip()
            if text is not None:
                n["text"] = str(text)[:2000]
            changed = True
            break
    if changed:
        item.setData(Outline.associatedNotes, dump_associated_notes(notes))
    return changed


def delete_associated_note(item, note_id):
    """Delete an associated note by ID from an outlineItem."""
    if item is None:
        return False
    notes = parse_associated_notes(item.data(Outline.associatedNotes))
    next_notes = [n for n in notes if n["id"] != note_id]
    if len(next_notes) != len(notes):
        item.setData(Outline.associatedNotes, dump_associated_notes(next_notes))
        return True
    return False


def label_name_for_item(item, mdl_labels):
    """Return the label name string for `item` from `mdl_labels` (1-based index)."""
    if item is None or mdl_labels is None:
        return ""
    idx = toInt(item.data(Outline.label))
    if idx >= 1 and idx < mdl_labels.rowCount():
        std_item = mdl_labels.item(idx, 0)
        if std_item is not None:
            return std_item.text() or ""
    return ""


def ensure_chapter_label_index(mdl_labels):
    """Find the 1-based index of the 'Chapter' label in `mdl_labels`, creating it if absent."""
    if mdl_labels is None:
        return ""
    for i in range(1, mdl_labels.rowCount()):
        it = mdl_labels.item(i, 0)
        if it and (it.text() or "").strip().lower() == "chapter":
            return str(i)
    icon = iconFromColorString("#0000ff")
    mdl_labels.appendRow(QStandardItem(icon, "Chapter"))
    return str(mdl_labels.rowCount() - 1)


def is_chapter_item(item, mdl_labels=None):
    """Return True if `item` is a Chapter (by label 'Chapter' or title starting with 'Chapter')."""
    if item is None:
        return False
    lname = label_name_for_item(item, mdl_labels).strip().lower()
    if lname == "chapter":
        return True
    if lname and lname != "chapter":
        return False
    return bool(re.match(r"^chapter\b", item.title() or "", re.IGNORECASE))


def sibling_depth_offset(item, mdl_labels=None):
    """Return 1 if `item` is a non-folder scene sitting beneath a `.md` Chapter sibling."""
    if item is None or item.isFolder() or is_chapter_item(item, mdl_labels):
        return 0
    parent = item.parent()
    if parent is None:
        return 0
    siblings = parent.children()
    try:
        idx = siblings.index(item)
    except ValueError:
        return 0
    for i in range(idx - 1, -1, -1):
        sib = siblings[i]
        if sib.isFolder():
            return 0
        if is_chapter_item(sib, mdl_labels):
            return 1
    return 0


def _all_folders(root_item):
    out = []
    for c in root_item.children():
        if c.isFolder():
            out.append(c)
        out.extend(_all_folders(c))
    return out


def resolve_placement_for_add(mdl_outline, mdl_labels, adding_type, active_item=None):
    """Return `(parent_index, row)` for adding `'folder'`, `'chapter'`, or `'scene'`.

    Matches `resolvePlacementForAdd` in `web/src/lib/outline.ts`:
    - A Chapter is a `.md` item with label `'Chapter'`.
    - Adding a Scene when a Chapter (or scene under a chapter) is active inserts the new scene
      at the end of that chapter's scenes (before the next chapter or folder).
    - Adding a Chapter when a Chapter/Scene is active inserts the new chapter after the current
      chapter and its scenes.
    """
    root = mdl_outline.rootItem

    def idx_of(item_obj):
        if item_obj is None or item_obj == root:
            return QModelIndex()
        return mdl_outline.indexFromItem(item_obj)

    if adding_type in ("scene", "chapter") and active_item is not None and not active_item.isFolder():
        parent_item = active_item.parent() or root
        siblings = parent_item.children()
        try:
            idx = siblings.index(active_item)
        except ValueError:
            idx = -1
        if idx >= 0:
            insert_pos = idx + 1
            while (
                insert_pos < len(siblings)
                and not siblings[insert_pos].isFolder()
                and not is_chapter_item(siblings[insert_pos], mdl_labels)
            ):
                insert_pos += 1
            return idx_of(parent_item), insert_pos
        return idx_of(parent_item), parent_item.childCount()

    if adding_type == "scene":
        if active_item is not None and active_item.isFolder():
            return idx_of(active_item), active_item.childCount()
        folders = _all_folders(root)
        target_parent = folders[-1] if folders else root
        return idx_of(target_parent), target_parent.childCount()

    if adding_type == "chapter":
        if active_item is not None and active_item.isFolder():
            if is_chapter_item(active_item, mdl_labels):
                p = active_item.parent() or root
                return idx_of(p), p.childCount()
            return idx_of(active_item), active_item.childCount()
        folders = _all_folders(root)
        target_parent = folders[0] if folders else root
        return idx_of(target_parent), target_parent.childCount()

    # adding_type == "folder"
    if active_item is not None:
        if active_item.isFolder():
            return idx_of(active_item), active_item.childCount()
        p = active_item.parent() or root
        return idx_of(p), p.childCount()
    return QModelIndex(), root.childCount()
