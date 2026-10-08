# --!-- coding: utf8 --!--
"""Tiny colour maths with no Qt dependency (so it can be unit tested)."""


def toRgb(hexColor):
    h = hexColor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def toHex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def mix(c1, c2, f=0.5):
    """Blend: f=0 gives c1, f=1 gives c2."""
    a, b = toRgb(c1), toRgb(c2)
    return toHex(tuple(a[i] + (b[i] - a[i]) * f for i in range(3)))


def lighten(c, f):
    return mix(c, "#ffffff", f)


def darken(c, f):
    return mix(c, "#000000", f)


def luminance(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in toRgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(c1, c2):
    """WCAG contrast ratio, 1.0 to 21.0."""
    l1, l2 = luminance(c1), luminance(c2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def readableOn(bg, light="#ffffff", dark="#000000"):
    """Pick white or black text, whichever reads better on `bg`."""
    return light if contrast(bg, light) >= contrast(bg, dark) else dark


def ensureContrast(fg, bg, minRatio):
    """Nudge `fg` towards white/black until it reaches `minRatio` on `bg`."""
    target = "#ffffff" if luminance(bg) < 0.5 else "#000000"
    out = fg
    for i in range(1, 21):
        if contrast(out, bg) >= minRatio:
            break
        out = mix(fg, target, i * 0.05)
    return out
