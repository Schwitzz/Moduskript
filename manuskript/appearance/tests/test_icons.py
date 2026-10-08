from manuskript.appearance import colors as C
from manuskript.appearance import icons as I

BG = "#14161b"


def test_dark_fill_is_lifted_and_bright_fill_kept():
    svg = '<path style="fill:#222222"/><path style="fill:#ffffff"/><path fill="#303030"/>'
    out, changed = I.recolourSvg(svg, BG)
    assert changed and "#ffffff" in out and "#222222" not in out and "#303030" not in out


def test_nothing_changes_when_all_visible():
    out, changed = I.recolourSvg('<path style="fill:#fff"/>', BG)
    assert not changed and out == '<path style="fill:#fff"/>'


def test_build_writes_only_changed_and_caches(tmp_path):
    src = tmp_path / "src" / "22x22" / "actions"; src.mkdir(parents=True)
    (src / "dark.svg").write_text('<svg><path style="fill:#111111"/></svg>')
    (src / "ok.svg").write_text('<svg><path style="fill:#ffffff"/></svg>')
    cache = tmp_path / "cache"
    n = I.build(str(tmp_path / "src"), str(cache), BG, "v1")
    assert n == 1
    t = cache / I.THEME
    assert (t / "22x22" / "actions" / "dark.svg").exists()
    assert not (t / "22x22" / "actions" / "ok.svg").exists()
    assert "Inherits=NumixMsk" in (t / "index.theme").read_text()
    assert I.build(str(tmp_path / "src"), str(cache), BG, "v1") == -1   # cached
    assert I.build(str(tmp_path / "src"), str(cache), BG, "v2") == 1    # rebuilt
