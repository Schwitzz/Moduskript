import types

import pytest

from moduskript.appearance import colors as C
from moduskript.appearance import schemes as S
from moduskript.appearance import views as V


class _A:
    """Stand-in for Appearance, injected per test (nothing global changes)."""
    follow = True
    scheme = "nord"

    @classmethod
    def viewsFollowTheme(cls):
        return cls.follow

    @classmethod
    def colours(cls):
        s = S.get(cls.scheme)
        return (s, S.derived(s)) if s else (None, {})


@pytest.fixture(autouse=True)
def fakeAppearance(monkeypatch):
    _A.follow, _A.scheme = True, "nord"
    monkeypatch.setattr(V, "Appearance", _A)


def _settings():
    m = types.SimpleNamespace()
    m.textEditor = {"background": "#000000", "fontColor": "#c8cdc9",
                    "misspelled": "#F00", "backgroundTransparent": True}
    m.corkBackground = {"color": "#000000", "image": "spacedreams.jpg"}
    return m


def test_project_colours_replaced_when_following():
    m = _settings()
    assert V.applyToSettings(m) is True
    nord = S.get("nord")
    assert m.textEditor["background"] == nord.editor
    assert m.textEditor["fontColor"] == nord.text
    assert m.textEditor["backgroundTransparent"] is False
    assert m.corkBackground["image"] == ""
    assert C.contrast(m.textEditor["fontColor"], m.textEditor["background"]) >= 7


def test_untouched_when_off_or_system():
    _A.follow = False
    m = _settings()
    assert V.applyToSettings(m) is False and m.textEditor["background"] == "#000000"
    _A.follow, _A.scheme = True, "system"
    assert V.applyToSettings(m) is False and m.corkBackground["image"] == "spacedreams.jpg"
