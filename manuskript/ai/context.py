# --!-- coding: utf8 --!--
"""Collect writing context from Manuskript's models and fit it to a budget."""

from manuskript.ai.providers import estimateTokens

# (key, label, priority). Lower number = kept first when trimming.
SOURCES = [
    ("selection", "Text selected by the author", 0),
    ("scene", "Current scene text", 1),
    ("summary", "Current scene summary and notes", 2),
    ("pov", "Point-of-view character", 3),
    ("book", "Book information", 4),
]


def assemble(parts, maxTokens):
    """parts: list of (key, label, text). Returns the context string.

    Pieces are kept in SOURCES priority order. The scene text (the only
    piece that can be huge) is cut from its start, keeping the most recent
    text, when it does not fit. Other pieces are dropped if they don't fit.
    """
    prio = {k: p for k, _l, p in SOURCES}
    chosen, used = [], 0
    for key, label, text in sorted(parts, key=lambda x: prio.get(x[0], 9)):
        text = (text or "").strip()
        if not text:
            continue
        cost = estimateTokens(text) + 8
        if used + cost > maxTokens:
            room = maxTokens - used - 8
            if key in ("scene", "selection") and room > 200:
                text = "[...]" + text[-int(room * 3.5):]
                cost = estimateTokens(text) + 8
            else:
                continue
        chosen.append((key, label, text))
        used += cost
    order = {k: i for i, (k, _l, _p) in enumerate(SOURCES)}
    chosen.sort(key=lambda x: order.get(x[0], 9))
    return "\n\n".join("### %s\n%s" % (label, text) for _k, label, text in chosen)


def _flatDataText(mw, row, col):
    item = mw.mdlFlatData.item(row, col)
    return item.text().strip() if item else ""


def gather(mw, flags):
    """Read the current context from the main window. `flags` is a dict
    {key: bool}. Returns a list of (key, label, text)."""
    from manuskript.enums import Outline, Character

    labels = {k: l for k, l, _p in SOURCES}
    out = []
    if not getattr(mw, "currentProject", None):
        return out

    editor = None
    try:
        editor = mw.mainEditor.currentEditor()
    except Exception:
        editor = None

    item = None
    if editor is not None:
        idx = getattr(editor, "currentIndex", None)
        if idx is not None and idx.isValid():
            item = idx.internalPointer()

    if flags.get("selection") and editor is not None:
        view = getattr(editor, "txtRedacText", None)
        if view is not None:
            sel = view.textCursor().selectedText().replace("\u2029", "\n")
            out.append(("selection", labels["selection"], sel))

    if item is not None:
        title = item.title()
        if flags.get("scene") and item.isText():
            out.append(("scene", "%s: \"%s\"" % (labels["scene"], title),
                        item.data(Outline.text)))
        if flags.get("summary"):
            bits = []
            for col, name in ((Outline.summaryFull, "Summary"),
                              (Outline.summarySentence, "One-line summary"),
                              (Outline.notes, "Notes")):
                val = item.data(col)
                if val:
                    bits.append("%s: %s" % (name, val))
            out.append(("summary", labels["summary"], "\n".join(bits)))
        if flags.get("pov"):
            pov = item.data(Outline.POV)
            char = mw.mdlCharacter.getCharacterByID(pov) if pov else None
            if char is not None:
                bits = ["Name: %s" % char.name()]
                for col, name in ((Character.motivation, "Motivation"),
                                  (Character.goal, "Goal"),
                                  (Character.conflict, "Conflict"),
                                  (Character.summaryFull, "Summary"),
                                  (Character.notes, "Notes")):
                    val = char.data(col.value)
                    if val:
                        bits.append("%s: %s" % (name, val))
                out.append(("pov", labels["pov"], "\n".join(bits)))

    if flags.get("book"):
        bits = []
        for col, name in ((0, "Title"), (4, "Genre")):
            val = _flatDataText(mw, 0, col)
            if val:
                bits.append("%s: %s" % (name, val))
        for col, name in ((1, "Summary (sentence)"), (2, "Summary (paragraph)")):
            val = _flatDataText(mw, 1, col)
            if val:
                bits.append("%s: %s" % (name, val))
        out.append(("book", labels["book"], "\n".join(bits)))
    return out
