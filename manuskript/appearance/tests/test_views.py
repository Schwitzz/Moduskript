import importlib.util, os, sys, types

_base = os.path.join(os.path.dirname(__file__), "..")
pkg = types.ModuleType("manuskript.appearance"); pkg.__path__ = [_base]
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
# views.py imports Appearance (needs PyQt5); stub config for a Qt-free test.
cfg = types.ModuleType("manuskript.appearance.config")


class _A:
    follow = True
    scheme = "nord"

    @staticmethod
    def viewsFollowTheme():
        return _A.follow

    @staticmethod
    def colours():
        s = S.get(_A.scheme)
        return (s, S.derived(s)) if s else (None, {})


cfg.Appearance = _A
sys.modules["manuskript.appearance.config"] = cfg
V = _load("views")


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
    _A.scheme = "nord"
