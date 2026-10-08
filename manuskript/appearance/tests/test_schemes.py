import importlib.util
import os
import sys
import types

import pytest

# Load the pure-python modules directly: no Qt and no Manuskript app needed.
_base = os.path.join(os.path.dirname(__file__), "..")
pkg = types.ModuleType("manuskript.appearance")
pkg.__path__ = [_base]
sys.modules.setdefault("manuskript", types.ModuleType("manuskript"))
sys.modules["manuskript.appearance"] = pkg


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "manuskript.appearance." + name, os.path.join(_base, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


C = _load("colors")
S = _load("schemes")
ALL = list(S.SCHEMES.values())


def test_counts_and_unique_ids():
    assert len(ALL) >= 25
    assert len({s.id for s in ALL}) == len(ALL)
    assert sum(1 for s in ALL if s.dark) > sum(1 for s in ALL if not s.dark)
    assert S.DEFAULT in S.SCHEMES


@pytest.mark.parametrize("s", ALL, ids=lambda s: s.id)
def test_valid_hex(s):
    for v in s[3:]:
        assert len(C.toRgb(v)) == 3


@pytest.mark.parametrize("s", ALL, ids=lambda s: s.id)
def test_dark_flag_matches_luminance(s):
    assert (C.luminance(s.window) < 0.2) == s.dark


@pytest.mark.parametrize("s", ALL, ids=lambda s: s.id)
def test_text_contrast_wcag_aa(s):
    for bg in (s.window, s.panel, s.editor):
        assert C.contrast(s.text, bg) >= 7.0, (s.id, bg)       # AAA for body text
        assert C.contrast(s.muted, bg) >= 4.5, (s.id, bg)      # AA for muted text


@pytest.mark.parametrize("s", ALL, ids=lambda s: s.id)
def test_accent_and_status_colours_readable(s):
    for col in (s.accent, s.success, s.warning, s.error):
        assert C.contrast(col, s.editor) >= 3.0, (s.id, col)   # AA for UI elements
        assert C.contrast(col, s.panel) >= 3.0, (s.id, col)


@pytest.mark.parametrize("s", ALL, ids=lambda s: s.id)
def test_derived_colours(s):
    d = S.derived(s)
    assert C.contrast(d["selectionText"], d["selection"]) >= 4.5
    assert C.contrast(d["link"], s.editor) >= 4.5
    assert C.contrast(d["onAccent"], d["accent"]) >= 4.5


def test_custom_accent_is_applied():
    d = S.derived(S.get("midnight"), accent="#ff0000")
    assert d["accent"] == "#ff0000"
    assert C.contrast(d["link"], S.get("midnight").editor) >= 4.5


def test_system_has_no_scheme():
    assert S.get(S.SYSTEM) is None
    assert S.names()[0][0] == S.SYSTEM
