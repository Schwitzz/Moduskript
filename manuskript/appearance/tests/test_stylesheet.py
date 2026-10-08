import importlib.util
import os
import re
import sys
import types

import pytest

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
SS = _load("stylesheet")


def _balanced(css):
    return css.count("{") == css.count("}")


@pytest.mark.parametrize("sid", list(S.SCHEMES))
@pytest.mark.parametrize("density", list(SS.DENSITY))
def test_builds_for_every_scheme_and_density(sid, density):
    s = S.get(sid)
    css = SS.build(s, S.derived(s), density, "Inter", 11)
    assert _balanced(css)
    assert "{{" not in css and "}}" not in css          # no unformatted templates
    assert "{" + "accent" not in css
    assert s.window in css and s.editor in css
    assert not re.search(r"#[0-9a-f]{0,5}[^0-9a-f;\s,)}]", css)  # no malformed colours


def test_font_rule_optional():
    s = S.get("nord")
    css = SS.build(s, S.derived(s), "Comfortable", "", 0)
    assert "font-family" not in css and "font-size" not in css
    css = SS.build(s, S.derived(s), "Comfortable", "Noto Sans", 12)
    assert 'font-family: "Noto Sans"' in css and "font-size: 12pt" in css


def test_custom_accent_flows_into_css():
    s = S.get("midnight")
    css = SS.build(s, S.derived(s, "#ff00aa"), "Comfortable")
    assert "#ff00aa" in css


def test_density_changes_padding():
    s = S.get("midnight")
    d = S.derived(s)
    assert SS.build(s, d, "Compact") != SS.build(s, d, "Spacious")
