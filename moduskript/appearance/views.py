# --!-- coding: utf8 --!--
"""Make the project's own view colours follow the colour scheme.

A project stores editor and corkboard colours in its settings.txt. When
"Views follow theme" is on, those values are replaced in memory right after
the project's settings are loaded. (They are written back to the project only
when you save, like any other setting.)
"""

from moduskript.appearance.config import Appearance


def themedValues(s, d):
    """The editor/cork values for scheme `s` (pure function)."""
    return {
        "editorBackground": s.editor,
        "editorText": s.text,
        "misspelled": s.error,
        "corkColor": d["corkBackground"],
    }


def applyToSettings(settings):
    """Call right after a project's settings were loaded. `settings` is the
    manuskript.settings module. Returns True if anything was changed."""
    if not Appearance.viewsFollowTheme():
        return False
    s, d = Appearance.colours()
    if s is None:
        return False
    v = themedValues(s, d)
    settings.textEditor["background"] = v["editorBackground"]
    settings.textEditor["fontColor"] = v["editorText"]
    settings.textEditor["misspelled"] = v["misspelled"]
    settings.textEditor["backgroundTransparent"] = False
    settings.corkBackground["color"] = v["corkColor"]
    settings.corkBackground["image"] = ""
    return True
