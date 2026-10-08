# --!-- coding: utf8 --!--
"""Recolour icons that are hard to see on a dark scheme.

The bundled NumixMsk files are never modified. Recoloured copies go into a
cache icon theme ("NumixMskThemed") that inherits from NumixMsk, so only the
faint icons are overridden.
"""

import os
import re
import shutil

from manuskript.appearance import colors as C

THEME = "NumixMskThemed"
MIN_CONTRAST = 3.0
TARGET_CONTRAST = 4.0
_HEX = re.compile(r"(fill|stroke)(\s*[:=]\s*\"?)(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b")


def recolourSvg(text, background):
    """Return (new_text, changed). Any fill/stroke colour with too little
    contrast against `background` is lifted, keeping its hue where possible."""
    changed = [False]

    def fix(m):
        col = m.group(3)
        if C.contrast(col, background) >= MIN_CONTRAST:
            return m.group(0)
        changed[0] = True
        return m.group(1) + m.group(2) + C.ensureContrast(col, background, TARGET_CONTRAST)

    return _HEX.sub(fix, text), changed[0]


def _indexTheme(dirs):
    out = ["[Icon Theme]", "Name=%s" % THEME, "Comment=Recoloured icons",
           "Inherits=NumixMsk", "Directories=" + ",".join(sorted(dirs)), ""]
    for d in sorted(dirs):
        size = d.split("/")[0]
        out.append("[%s]" % d)
        if size == "scalable":
            out += ["Size=48", "MinSize=8", "MaxSize=512", "Type=Scalable"]
        else:
            out += ["Size=%s" % size.split("x")[0], "Type=Fixed"]
        out.append("")
    return "\n".join(out)


def build(sourceTheme, cacheRoot, background, stamp):
    """Create `cacheRoot/NumixMskThemed`. Returns the number of icons written.
    `stamp` identifies scheme+version; the cache is reused if it matches."""
    target = os.path.join(cacheRoot, THEME)
    stampFile = os.path.join(target, ".stamp")
    if os.path.isfile(stampFile) and open(stampFile).read() == stamp:
        return -1
    shutil.rmtree(target, ignore_errors=True)
    dirs, count = set(), 0
    for dirpath, _dn, files in os.walk(sourceTheme):
        for fn in files:
            if not fn.endswith(".svg"):
                continue
            src = os.path.join(dirpath, fn)
            try:
                txt = open(src, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            new, changed = recolourSvg(txt, background)
            if not changed:
                continue
            rel = os.path.relpath(dirpath, sourceTheme)
            os.makedirs(os.path.join(target, rel), exist_ok=True)
            with open(os.path.join(target, rel, fn), "w", encoding="utf-8") as f:
                f.write(new)
            dirs.add(rel.replace(os.sep, "/"))
            count += 1
    os.makedirs(target, exist_ok=True)
    with open(os.path.join(target, "index.theme"), "w") as f:
        f.write(_indexTheme(dirs))
    with open(stampFile, "w") as f:
        f.write(stamp)
    return count
