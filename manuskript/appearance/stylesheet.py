# --!-- coding: utf8 --!--
"""Builds the app-wide Qt stylesheet from a scheme (no Qt dependency)."""

# pad = control padding (px), row = list/tree row padding, tab = tab padding
DENSITY = {
    "Compact": {"pad": 2, "padx": 6, "row": 1, "tab": 3, "radius": 4, "menu": 4},
    "Comfortable": {"pad": 4, "padx": 10, "row": 3, "tab": 6, "radius": 6, "menu": 6},
    "Spacious": {"pad": 7, "padx": 14, "row": 5, "tab": 9, "radius": 8, "menu": 9},
}


def build(s, d, density="Comfortable", font="", fontSize=0):
    """s: Scheme, d: schemes.derived() dict."""
    k = DENSITY.get(density, DENSITY["Comfortable"])
    v = dict(d)
    v.update(k, window=s.window, panel=s.panel, editor=s.editor, text=s.text,
             muted=s.muted, success=s.success, warning=s.warning, error=s.error)
    v["fontRule"] = ""
    if font:
        v["fontRule"] = 'font-family: "%s";' % font
    if fontSize:
        v["fontRule"] += " font-size: %dpt;" % fontSize
    return (_base(v) + _inputs(v) + _buttons(v) + _views(v) + _tabs(v)
            + _menus(v) + _scroll(v) + _misc(v))


def _base(v):
    return """
QWidget {{ {fontRule} }}
QMainWindow, QDialog {{ background: {window}; color: {text}; }}
QToolTip {{ background: {panel}; color: {text}; border: 1px solid {borderStrong};
    padding: 4px 6px; }}
QLabel {{ background: transparent; }}
QGroupBox {{ border: 1px solid {border}; border-radius: {radius}px;
    margin-top: 1.1em; padding: {pad}px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px;
    color: {muted}; }}
QSplitter::handle {{ background: {border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QSplitter::handle:hover {{ background: {accent}; }}
QStatusBar {{ background: {panel}; color: {muted}; }}
QProgressBar {{ border: 1px solid {border}; border-radius: {radius}px;
    background: {editor}; text-align: center; color: {text}; }}
QProgressBar::chunk {{ background: {accent}; border-radius: {radius}px; }}
""".format(**v)


def _inputs(v):
    return """
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QSpinBox,
QDoubleSpinBox, QComboBox, QAbstractSpinBox {{
    background: {editor}; color: {text};
    border: 1px solid {border}; border-radius: {radius}px;
    padding: {pad}px {padx}px; selection-background-color: {selection};
    selection-color: {selectionText}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus, QComboBox:on {{
    border: 1px solid {accent}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {disabled}; background: {window}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {panel}; color: {text};
    border: 1px solid {borderStrong}; selection-background-color: {accent};
    selection-color: {onAccent}; outline: none; }}
QCheckBox, QRadioButton {{ spacing: 6px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QCheckBox::indicator {{ border: 1px solid {borderStrong}; border-radius: 4px;
    background: {editor}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QRadioButton::indicator {{ border: 1px solid {borderStrong}; border-radius: 8px;
    background: {editor}; }}
QRadioButton::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {accent}; width: 14px; height: 14px;
    margin: -6px 0; border-radius: 7px; }}
""".format(**v)


def _buttons(v):
    return """
QPushButton {{ background: {panel}; color: {text}; border: 1px solid {border};
    border-radius: {radius}px; padding: {pad}px {padx}px; }}
QPushButton:hover {{ background: {hover}; border-color: {borderStrong}; }}
QPushButton:pressed {{ background: {pressed}; }}
QPushButton:default, QPushButton:checked {{ background: {accent};
    color: {onAccent}; border-color: {accent}; }}
QPushButton:disabled {{ color: {disabled}; background: {window}; }}
QPushButton:flat {{ border: none; background: transparent; }}
QPushButton:flat:hover {{ background: {hover}; }}
QToolButton {{ background: transparent; border: 1px solid transparent;
    border-radius: {radius}px; padding: {pad}px; color: {text}; }}
QToolButton:hover {{ background: {hover}; border-color: {border}; }}
QToolButton:checked, QToolButton:pressed {{ background: {pressed}; }}
QToolBar {{ background: {window}; border: none; spacing: 2px; }}
""".format(**v)


def _views(v):
    return """
QTreeView, QListView, QTableView, QListWidget, QTreeWidget, QTableWidget {{
    background: {editor}; color: {text}; alternate-background-color: {panel};
    border: 1px solid {border}; border-radius: {radius}px;
    selection-background-color: {selection}; selection-color: {selectionText};
    outline: none; show-decoration-selected: 1; }}
QTreeView::item, QListView::item, QTableView::item {{ padding: {row}px 2px; }}
QTreeView::item:hover, QListView::item:hover {{ background: {hover}; }}
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
    background: {selection}; color: {selectionText}; }}
QHeaderView::section {{ background: {panel}; color: {muted}; border: none;
    border-bottom: 1px solid {border}; padding: {pad}px {padx}px; }}
QTableCornerButton::section {{ background: {panel}; border: none; }}
""".format(**v)


def _tabs(v):
    return """
QTabWidget::pane {{ border: 1px solid {border}; border-radius: {radius}px;
    top: -1px; background: {window}; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; color: {muted};
    padding: {tab}px {padx}px; border: none; border-bottom: 2px solid transparent;
    margin-right: 2px; }}
QTabBar::tab:hover {{ color: {text}; background: {hover}; }}
QTabBar::tab:selected {{ color: {text}; border-bottom: 2px solid {accent}; }}
QTabBar::close-button {{ subcontrol-position: right; }}
QDockWidget {{ color: {text}; }}
QDockWidget::title {{ background: {panel}; padding: {pad}px {padx}px;
    border-bottom: 1px solid {border}; }}
""".format(**v)


def _menus(v):
    return """
QMenuBar {{ background: {window}; color: {text}; border: none; }}
QMenuBar::item {{ padding: {pad}px {padx}px; background: transparent;
    border-radius: {radius}px; }}
QMenuBar::item:selected {{ background: {hover}; }}
QMenu {{ background: {panel}; color: {text}; border: 1px solid {borderStrong};
    padding: 4px; }}
QMenu::item {{ padding: {menu}px 24px {menu}px 14px; border-radius: {radius}px; }}
QMenu::item:selected {{ background: {accent}; color: {onAccent}; }}
QMenu::item:disabled {{ color: {disabled}; background: transparent; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
""".format(**v)


def _scroll(v):
    return """
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {scroll}; border-radius: 4px;
    min-height: 28px; margin: 1px; }}
QScrollBar::handle:horizontal {{ background: {scroll}; border-radius: 4px;
    min-width: 28px; margin: 1px; }}
QScrollBar::handle:hover {{ background: {scrollHover}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
""".format(**v)


def _misc(v):
    return """
QDialogButtonBox QPushButton {{ min-width: 72px; }}
QMessageBox {{ background: {window}; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {border}; }}
QTextBrowser {{ selection-background-color: {selection}; }}
""".format(**v)
