# --!-- coding: utf8 --!--
"""Applies the chosen appearance to the running QApplication.

Call `apply(app)` once at start-up, BEFORE manuskript.ui.style is imported:
that module reads the palette a single time when first loaded.
"""

import logging
import os

from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPalette

from manuskript.appearance import stylesheet
from manuskript.appearance.config import Appearance, FONT_BUNDLED

LOGGER = logging.getLogger(__name__)

_FONT_FILE = os.path.join(os.path.dirname(__file__), "fonts", "InterVariable.ttf")
_loaded = {}


def loadBundledFont():
    """Register Inter with Qt. Returns its family name, or '' on failure."""
    if "family" in _loaded:
        return _loaded["family"]
    family = ""
    if os.path.isfile(_FONT_FILE):
        fid = QFontDatabase.addApplicationFont(_FONT_FILE)
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        family = fams[0] if fams else ""
    if not family:
        LOGGER.warning("Bundled Inter font could not be loaded.")
    _loaded["family"] = family
    return family


def resolveFont(choice):
    """Map a font choice to an installed family name ('' = system default)."""
    if choice == FONT_BUNDLED:
        return loadBundledFont()
    if choice == "System default":
        return ""
    return choice if choice in QFontDatabase().families() else ""


def buildPalette(s, d):
    """Qt palette for scheme `s` with derived colours `d`."""
    p = QPalette()
    c = QColor
    for role, col in (
        (QPalette.Window, s.window), (QPalette.WindowText, s.text),
        (QPalette.Base, s.editor), (QPalette.AlternateBase, s.panel),
        (QPalette.Text, s.text), (QPalette.Button, s.panel),
        (QPalette.ButtonText, s.text), (QPalette.BrightText, s.error),
        (QPalette.ToolTipBase, s.panel), (QPalette.ToolTipText, s.text),
        (QPalette.Highlight, d["accent"]), (QPalette.HighlightedText, d["onAccent"]),
        (QPalette.Link, d["link"]), (QPalette.LinkVisited, s.muted),
        (QPalette.Light, d["borderStrong"]), (QPalette.Midlight, d["border"]),
        (QPalette.Mid, d["border"]), (QPalette.Dark, s.editor),
        (QPalette.Shadow, "#000000"),
    ):
        p.setColor(role, c(col))
    if hasattr(QPalette, "PlaceholderText"):
        p.setColor(QPalette.PlaceholderText, c(s.muted))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, c(d["disabled"]))
    return p


def apply(app):
    """Apply palette, font and stylesheet. Returns the active Scheme or None."""
    s, d = Appearance.colours()
    family = resolveFont(Appearance.font())
    size = Appearance.fontSize()

    if s is None:                       # System scheme: leave Manuskript alone
        return None

    app.setStyle("Fusion")              # palettes/stylesheets need Fusion
    app.setPalette(buildPalette(s, d))
    if family:
        f = QFont(app.font())
        f.setFamily(family)
        app.setFont(f)
    css = stylesheet.build(s, d, Appearance.density(), family, size)
    app.setStyleSheet(css)
    LOGGER.info("Appearance: scheme=%s density=%s font=%s", s.id,
                Appearance.density(), family or "system")
    return s


def extraStyleSheet():
    """The scheme stylesheet again (used by code that replaces the app-wide
    stylesheet, such as the tooltip customisation)."""
    s, d = Appearance.colours()
    if s is None:
        return ""
    family = resolveFont(Appearance.font())
    return stylesheet.build(s, d, Appearance.density(), family, Appearance.fontSize())
