# --!-- coding: utf8 --!--
"""Colours for custom-painted views (corkboard cards, storyline).

These replace the hardcoded white / black / light grey. With the System
scheme (or "views follow theme" off) they return exactly the old colours.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

_cache = {}


def _themed():
    if "v" not in _cache:
        v = None
        try:
            from moduskript.appearance.config import Appearance
            if Appearance.viewsFollowTheme():
                s, d = Appearance.colours()
                if s is not None:
                    v = {"paper": d["card"], "ink": s.text,
                         "rule": d["cardBorder"], "hover": d["hover"]}
        except Exception:
            v = None
        _cache["v"] = v
    return _cache["v"]


def PAPER():
    """Card / node background (was white)."""
    v = _themed()
    return QColor(v["paper"]) if v else QColor(Qt.white)


def INK():
    """Card text and outlines (was black)."""
    v = _themed()
    return QColor(v["ink"]) if v else QColor(Qt.black)


def RULE():
    """Ruled lines and summary strip on cards (was #EEE)."""
    v = _themed()
    return QColor(v["rule"]) if v else QColor("#EEE")


def HOVER():
    """Hover highlight in the storyline view (was light grey)."""
    v = _themed()
    return QColor(v["hover"]) if v else QColor(Qt.lightGray)
