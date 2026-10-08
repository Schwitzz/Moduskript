# --!-- coding: utf8 --!--
"""Colour scheme definitions (no Qt dependency).

Each row: id, display name, dark?, window, panel, editor, text, muted,
          accent, success, warning, error
"""

from collections import OrderedDict, namedtuple

from manuskript.appearance import colors as C

SYSTEM = "system"
DEFAULT = "midnight"

Scheme = namedtuple("Scheme", [
    "id", "name", "dark", "window", "panel", "editor", "text", "muted",
    "accent", "success", "warning", "error"])

_ROWS = [
    # ---------------------------------------------------------------- dark
    ("midnight", "Midnight", True, "#14161b", "#1b1e25", "#0f1115", "#e4e6eb", "#9aa0ac", "#6ea8fe", "#5fd38d", "#f0b429", "#f2677a"),
    ("obsidian", "Obsidian (OLED)", True, "#000000", "#0b0b0d", "#000000", "#e6e6e6", "#8e8e93", "#8ab4ff", "#4ade80", "#fbbf24", "#f87171"),
    ("nord", "Nord", True, "#2e3440", "#3b4252", "#272c36", "#eceff4", "#a3adbf", "#88c0d0", "#a3be8c", "#ebcb8b", "#bf616a"),
    ("dracula", "Dracula", True, "#282a36", "#21222c", "#1e1f29", "#f8f8f2", "#a3abd0", "#bd93f9", "#50fa7b", "#f1fa8c", "#ff5555"),
    ("gruvbox-dark", "Gruvbox Dark", True, "#282828", "#3c3836", "#1d2021", "#ebdbb2", "#a89984", "#fabd2f", "#b8bb26", "#fe8019", "#fb4934"),
    ("tokyo-night", "Tokyo Night", True, "#1a1b26", "#1f2335", "#16161e", "#c0caf5", "#8089b3", "#7aa2f7", "#9ece6a", "#e0af68", "#f7768e"),
    ("tokyo-night-storm", "Tokyo Night Storm", True, "#24283b", "#1f2335", "#1a1e2e", "#c0caf5", "#8d96c0", "#7aa2f7", "#9ece6a", "#e0af68", "#f7768e"),
    ("catppuccin-mocha", "Catppuccin Mocha", True, "#1e1e2e", "#181825", "#11111b", "#cdd6f4", "#a6adc8", "#cba6f7", "#a6e3a1", "#f9e2af", "#f38ba8"),
    ("catppuccin-macchiato", "Catppuccin Macchiato", True, "#24273a", "#1e2030", "#181926", "#cad3f5", "#a5adcb", "#c6a0f6", "#a6da95", "#eed49f", "#ed8796"),
    ("catppuccin-frappe", "Catppuccin Frapp\u00e9", True, "#303446", "#292c3c", "#232634", "#c6d0f5", "#a5adce", "#ca9ee6", "#a6d189", "#e5c890", "#e78284"),
    ("one-dark", "One Dark", True, "#282c34", "#21252b", "#1b1f27", "#abb2bf", "#848c9a", "#61afef", "#98c379", "#e5c07b", "#e06c75"),
    ("solarized-dark", "Solarized Dark", True, "#002b36", "#073642", "#00212b", "#93a1a1", "#839496", "#268bd2", "#859900", "#b58900", "#dc322f"),
    ("rose-pine", "Ros\u00e9 Pine", True, "#191724", "#1f1d2e", "#14121f", "#e0def4", "#908caa", "#c4a7e7", "#9ccfd8", "#f6c177", "#eb6f92"),
    ("rose-pine-moon", "Ros\u00e9 Pine Moon", True, "#232136", "#2a273f", "#1d1b2e", "#e0def4", "#908caa", "#c4a7e7", "#9ccfd8", "#f6c177", "#eb6f92"),
    ("everforest-dark", "Everforest Dark", True, "#2d353b", "#343f44", "#272e33", "#d3c6aa", "#9da9a0", "#a7c080", "#a7c080", "#dbbc7f", "#e67e80"),
    ("monokai-pro", "Monokai Pro", True, "#2d2a2e", "#221f22", "#19181a", "#fcfcfa", "#a59fa0", "#ffd866", "#a9dc76", "#fc9867", "#ff6188"),
    ("ayu-mirage", "Ayu Mirage", True, "#1f2430", "#242936", "#191e2a", "#cccac2", "#8a919e", "#ffcc66", "#87d96c", "#ffad66", "#f28779"),
    ("ayu-dark", "Ayu Dark", True, "#0b0e14", "#10141c", "#0a0c11", "#bfbdb6", "#8a8e99", "#e6b450", "#7fd962", "#ffb454", "#f07178"),
    ("kanagawa", "Kanagawa", True, "#1f1f28", "#2a2a37", "#16161d", "#dcd7ba", "#9a9aa8", "#7e9cd8", "#98bb6c", "#e6c384", "#e82424"),
    ("github-dark", "GitHub Dark", True, "#0d1117", "#161b22", "#010409", "#e6edf3", "#8d96a0", "#58a6ff", "#3fb950", "#d29922", "#f85149"),
    ("material-ocean", "Material Ocean", True, "#0f111a", "#181a29", "#090b10", "#c3cee3", "#8a93ad", "#82aaff", "#c3e88d", "#ffcb6b", "#f07178"),
    ("night-owl", "Night Owl", True, "#011627", "#0b2942", "#010e1a", "#d6deeb", "#8ea1b5", "#82aaff", "#addb67", "#ecc48d", "#ef5350"),
    ("oceanic-next", "Oceanic Next", True, "#1b2b34", "#243642", "#16232a", "#d8dee9", "#9aa5b5", "#6699cc", "#99c794", "#fac863", "#ec5f67"),
    ("sepia-night", "Sepia Night", True, "#1c1814", "#241f1a", "#15120f", "#e3d5c0", "#a39683", "#d9a15b", "#a8b878", "#e0b040", "#d8695f"),
    ("high-contrast", "High Contrast Dark", True, "#000000", "#0a0a0a", "#000000", "#ffffff", "#d0d0d0", "#ffd400", "#00ff7f", "#ffa500", "#ff5f5f"),
    # --------------------------------------------------------------- light
    ("paper", "Paper", False, "#f4f5f7", "#ffffff", "#ffffff", "#1f2328", "#5b6470", "#2563eb", "#15803d", "#b45309", "#c62828"),
    ("sepia", "Sepia", False, "#efe6d2", "#f5edd9", "#f8f1e0", "#3b2f20", "#6e5f4a", "#a8561a", "#4d7c2f", "#9a6a00", "#b3382c"),
    ("solarized-light", "Solarized Light", False, "#eee8d5", "#fdf6e3", "#fdf6e3", "#4b5f66", "#5f7378", "#268bd2", "#6b7a00", "#946c00", "#dc322f"),
    ("catppuccin-latte", "Catppuccin Latte", False, "#eff1f5", "#e6e9ef", "#ffffff", "#4c4f69", "#5c5f77", "#8839ef", "#287a1f", "#8a6200", "#d20f39"),
    ("rose-pine-dawn", "Ros\u00e9 Pine Dawn", False, "#faf4ed", "#fffaf3", "#fffaf3", "#575279", "#6e6a86", "#7a5da8", "#2f7f87", "#9a6000", "#b4375a"),
    ("gruvbox-light", "Gruvbox Light", False, "#fbf1c7", "#ebdbb2", "#f9f5d7", "#3c3836", "#5f5750", "#9d5c00", "#6d7000", "#af3a03", "#cc241d"),
]


def _fit(color, backgrounds, ratio):
    """Nudge `color` just enough to reach `ratio` on every background."""
    for bg in backgrounds:
        color = C.ensureContrast(color, bg, ratio)
    return color


def _normalise(row):
    """Keep each palette's character but guarantee readability: body text
    7:1, muted text 4.5:1, accent and status colours 3:1 on every surface."""
    r = list(row)
    bgs = (r[3], r[4], r[5])
    r[6] = _fit(r[6], bgs, 7.0)
    r[7] = _fit(r[7], bgs, 4.5)
    for i in (8, 9, 10, 11):
        r[i] = _fit(r[i], bgs[1:], 3.0)
    return tuple(r)


SCHEMES = OrderedDict((r[0], Scheme(*_normalise(r))) for r in _ROWS)


def get(schemeId):
    """Return a Scheme, or None for the system scheme / unknown ids."""
    return SCHEMES.get(schemeId)


def names():
    """[(id, display name)] with System first."""
    return [(SYSTEM, "System (unchanged)")] + [(s.id, s.name) for s in SCHEMES.values()]


def derived(s, accent=None):
    """Extra colours computed from a scheme. `accent` overrides s.accent."""
    acc = accent or s.accent
    border = C.mix(s.window, s.text, 0.18)
    return {
        "border": border,
        "borderStrong": C.mix(s.window, s.text, 0.32),
        "hover": C.mix(s.panel, acc, 0.22),
        "pressed": C.mix(s.panel, acc, 0.34),
        "selection": C.mix(s.editor, acc, 0.38),
        "selectionText": C.ensureContrast(s.text, C.mix(s.editor, acc, 0.38), 4.5),
        "accent": acc,
        "onAccent": C.readableOn(acc),
        "disabled": C.mix(s.window, s.muted, 0.55),
        "scroll": C.mix(s.window, s.text, 0.22),
        "scrollHover": C.mix(s.window, s.text, 0.38),
        "link": C.ensureContrast(acc, s.editor, 4.5),
        "card": C.mix(s.panel, s.text, 0.05),
        "cardBorder": C.mix(s.panel, s.text, 0.20),
        "corkBackground": C.mix(s.window, s.editor, 0.5),
    }
