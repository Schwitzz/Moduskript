"""Press the real Tab key and measure how far the text moves."""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetricsF
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import qApp

from moduskript import settings
from moduskript.tests.test_formatBar import _openScene


def _x(e, pos):
    """Horizontal offset of character `pos` in the first line, from the layout."""
    doc = e.document()
    doc.setTextWidth(600)
    block = doc.firstBlock()
    doc.documentLayout().blockBoundingRect(block)      # forces the lazy layout
    lay = block.layout()
    assert lay.lineCount() > 0, "text layout not built"
    return lay.lineAt(0).cursorToX(pos)[0]


@pytest.mark.parametrize("n", [1, 2, 4, 8, 12])
def test_tab_character_is_n_spaces_wide(MWSampleProject, n):
    """A Tab character moves the next character by exactly n space widths."""
    e = _openScene(MWSampleProject)
    settings.textEditor["tabSpaces"] = n
    settings.textEditor["indent"] = False
    e.loadFontSettings()
    e.setPlainText("")
    e.show()
    QTest.keyClick(e, Qt.Key_Tab)            # the real key press
    QTest.keyClicks(e, "x")
    assert e.toPlainText() == "\tx"
    space = QFontMetricsF(e.font()).horizontalAdvance(" ")
    assert (_x(e, 1) - _x(e, 0)) / space == pytest.approx(n, abs=0.05)


@pytest.mark.parametrize("n", [2, 4, 8])
def test_first_line_indent_is_n_spaces(MWSampleProject, n):
    e = _openScene(MWSampleProject)
    settings.textEditor["tabSpaces"] = n
    settings.textEditor["indent"] = True
    e.loadFontSettings()
    e.setPlainText("word")
    e.show()
    e.highlighter and e.highlighter.rehighlight()
    space = QFontMetricsF(e.font()).horizontalAdvance(" ")
    assert e.document().firstBlock().blockFormat().textIndent() / space == pytest.approx(n, abs=0.05)
