# --!-- coding: utf8 --!--
"""App-wide appearance settings (QSettings group "Appearance").

Read very early at start-up, before the main window exists.
"""

from PyQt5.QtCore import QSettings

from moduskript.appearance import schemes

DENSITIES = ["Compact", "Comfortable", "Spacious"]
FONT_BUNDLED = "Inter"
FONTS = ["System default", FONT_BUNDLED, "Ubuntu Sans", "Noto Sans"]


def _qs():
    from PyQt5.QtWidgets import qApp
    return QSettings(qApp.organizationName(), qApp.applicationName())


def _get(name, default, typ=str):
    s = _qs()
    s.beginGroup("Appearance")
    try:
        return s.value(name, default, type=typ)
    finally:
        s.endGroup()


def _set(name, value):
    s = _qs()
    s.beginGroup("Appearance")
    s.setValue(name, value)
    s.endGroup()
    s.sync()


class Appearance:
    @staticmethod
    def scheme():
        v = _get("scheme", schemes.DEFAULT)
        return v if v == schemes.SYSTEM or v in schemes.SCHEMES else schemes.DEFAULT

    @staticmethod
    def setScheme(v):
        _set("scheme", v)

    @staticmethod
    def accent():
        """Custom accent colour as '#rrggbb', or '' to use the scheme's own."""
        return _get("accent", "")

    @staticmethod
    def setAccent(v):
        _set("accent", v or "")

    @staticmethod
    def font():
        v = _get("font", FONT_BUNDLED)
        return v if v in FONTS else FONT_BUNDLED

    @staticmethod
    def setFont(v):
        _set("font", v)

    @staticmethod
    def fontSize():
        """Point size, or 0 to keep whatever Manuskript/the system uses."""
        return _get("fontSize", 0, int)

    @staticmethod
    def setFontSize(v):
        _set("fontSize", int(v))

    @staticmethod
    def density():
        v = _get("density", "Comfortable")
        return v if v in DENSITIES else "Comfortable"

    @staticmethod
    def setDensity(v):
        _set("density", v)

    @staticmethod
    def viewsFollowTheme():
        return _get("viewsFollowTheme", True, bool)

    @staticmethod
    def setViewsFollowTheme(v):
        _set("viewsFollowTheme", bool(v))

    @staticmethod
    def recolourIcons():
        return _get("recolourIcons", True, bool)

    @staticmethod
    def setRecolourIcons(v):
        _set("recolourIcons", bool(v))

    @staticmethod
    def active():
        """The Scheme in use, or None for System."""
        return schemes.get(Appearance.scheme())

    @staticmethod
    def colours():
        """(Scheme, derived dict) for the active scheme, or (None, {})."""
        s = Appearance.active()
        if s is None:
            return None, {}
        return s, schemes.derived(s, Appearance.accent() or None)
