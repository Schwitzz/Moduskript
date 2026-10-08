#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Tests for the formatting bar, the tab-width setting and the model drop-down."""

import pytest
from PyQt5.QtGui import QFontMetricsF, QTextCursor

from manuskript import settings
from manuskript.ui.editors import formatBar as FB
from manuskript.ui.views.MDEditView import MDEditView


@pytest.mark.parametrize("text,style", [
    ("Plain words", "Body text"), ("# Title", "Heading 1"),
    ("### Deep", "Heading 3"), ("###### Six", "Heading 4"),
    ("> quoted", "Quote"), ("- item", "Bullet list"),
    ("* item", "Bullet list"), ("12. item", "Numbered list"),
    ("#hashtag no space", "Body text"),
])
def test_styleOf(text, style):
    assert FB.styleOf(text) == style


def test_restyle_replaces_old_prefix():
    assert FB.restyle("# Title", "Heading 2") == "## Title"
    assert FB.restyle("> quote", "Body text") == "quote"
    assert FB.restyle("- a", "Numbered list") == "1. a"
    assert FB.restyle("plain", "Quote") == "> plain"


def _openScene(MW):
    """Open the first text scene of the sample project; return its editor."""
    from manuskript.enums import Outline
    root = MW.mdlOutline.rootItem
    todo = list(root.children())
    while todo:
        it = todo.pop(0)
        if it.isText():
            MW.mainEditor.setCurrentModelIndex(it.index(), newTab=True)
            return MW.mainEditor.currentEditor().txtRedacText
        todo = list(it.children()) + todo
    raise AssertionError("no text scene in sample project")


@pytest.mark.parametrize("n", [1, 2, 4, 8, 12])
def test_tab_is_exactly_n_spaces(MWSampleProject, n):
    e = _openScene(MWSampleProject)
    settings.textEditor["tabSpaces"] = n
    settings.textEditor["indent"] = True
    e.loadFontSettings()
    space = QFontMetricsF(e.font()).horizontalAdvance(" ")
    assert space > 0
    assert e.tabStopDistance() == pytest.approx(n * space, abs=0.01)
    assert e.document().indentWidth() == pytest.approx(n * space, abs=0.01)
    assert e._defaultBlockFormat.textIndent() == pytest.approx(n * space, abs=0.01)


def test_indent_off_means_no_first_line_indent(MWSampleProject):
    e = _openScene(MWSampleProject)
    settings.textEditor["indent"] = False
    e.loadFontSettings()
    assert e._defaultBlockFormat.textIndent() == 0


def test_old_pixel_setting_is_ignored(MWSampleProject):
    """tabWidth (px, the old 20 -> ~29 spaces bug) must no longer matter."""
    e = _openScene(MWSampleProject)
    settings.textEditor["tabSpaces"] = 4
    settings.textEditor["tabWidth"] = 199
    e.loadFontSettings()
    space = QFontMetricsF(e.font()).horizontalAdvance(" ")
    assert e.tabStopDistance() == pytest.approx(4 * space, abs=0.01)


def test_settings_have_tabSpaces_default():
    assert settings.textEditor["tabSpaces"] >= 1


def test_bar_follows_and_writes_settings(MWSampleProject):
    MW = MWSampleProject
    MW.actSettings.triggered.emit()      # the Settings window is created lazily
    MW.sw.hide()
    bar = MW.mainEditor.formatBar
    settings.textEditor.update({"tabSpaces": 6, "indent": True, "spacingBelow": 9,
                                "textAlignment": 3, "lineSpacing": 150})
    bar.refresh()
    assert bar.spnTab.value() == 6 and bar.chkIndent.isChecked()
    assert bar.spnPara.value() == 9 and bar.cmbAlign.currentIndex() == 3
    assert bar.cmbSpacing.currentData() == 150
    # changing the bar changes the settings and the Settings window
    bar.spnTab.setValue(3)
    assert settings.textEditor["tabSpaces"] == 3
    assert MW.sw.spnEditorTabWidth.value() == 3
    bar.cmbAlign.setCurrentIndex(1)
    bar.cmbAlign.activated.emit(1)
    assert settings.textEditor["textAlignment"] == 1
    assert MW.sw.cmbEditorAlignment.currentIndex() == 1


def test_settings_window_updates_bar(MWSampleProject):
    MW = MWSampleProject
    MW.actSettings.triggered.emit()
    MW.sw.hide()
    MW.sw.spnEditorTabWidth.setValue(5)
    MW.sw.updateAllWidgets()
    assert MW.mainEditor.formatBar.spnTab.value() == 5


def test_paragraph_style_applies_to_selection(MWSampleProject):
    MW = MWSampleProject
    bar = MW.mainEditor.formatBar
    e = MDEditView()
    e.setPlainText("one\n\n# two\n- three")
    bar._view = e
    e.show()
    c = e.textCursor()
    c.setPosition(0)
    c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    e.setTextCursor(c)
    bar.cmbStyle.setCurrentIndex(FB.STYLES.index("Quote"))
    bar._applyStyle()
    assert e.toPlainText() == "> one\n\n> two\n> three"   # empty line untouched
    bar.cmbStyle.setCurrentIndex(FB.STYLES.index("Body text"))
    bar._applyStyle()
    assert e.toPlainText() == "one\n\ntwo\nthree"


def test_model_dropdown_in_settings(MWSampleProject):
    from manuskript.ai import providers as P
    from manuskript.ai.config import AISettings
    from manuskript.ai.settingsPage import AISettingsPage
    page = AISettingsPage()
    assert not page.cmbModel.isEditable()          # a real drop-down, not a text box
    AISettings.setProvider(P.LOCAL)
    AISettings.setCachedModels(P.LOCAL, ["m-a", "m-b"])
    page._loadProviderFields(P.LOCAL)
    names = [page.cmbModel.itemText(i) for i in range(page.cmbModel.count())]
    assert "m-a" in names and "m-b" in names
    # a fetch result fills the list and is cached for the chat dock too
    page._refreshDone(P.LOCAL, ["x1", "x2", "x3"])
    assert [page.cmbModel.itemText(i) for i in range(page.cmbModel.count())][-3:] == ["x1", "x2", "x3"] \
        or page.cmbModel.findText("x3") >= 0
    assert AISettings.cachedModels(P.LOCAL) == ["x1", "x2", "x3"]
