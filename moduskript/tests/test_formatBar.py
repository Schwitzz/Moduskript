#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Tests for the formatting bar, the tab-width setting and the model drop-down."""

import pytest
from PyQt5.QtGui import QFontMetricsF, QTextCursor

from moduskript import settings
from moduskript.ui.editors import formatBar as FB
from moduskript.ui.views.MDEditView import MDEditView


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
    from moduskript.enums import Outline
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
    from moduskript.ai import providers as P
    from moduskript.ai.config import AISettings
    from moduskript.ai.settingsPage import AISettingsPage
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


def test_readable_vs_md_code_toggle_and_highlighter(MWSampleProject):
    MW = MWSampleProject
    bar = MW.mainEditor.formatBar
    e = _openScene(MWSampleProject)
    e.setPlainText("# Heading One\nParagraph with **bold** and *italic* text.")
    bar._view = e
    e.show()

    # Keep cursor right inside line 2 (active block, no selection)
    c = e.textCursor()
    c.movePosition(QTextCursor.End)
    e.setTextCursor(c)

    # Toggle to Readable Mode first
    bar.btnReadable.setChecked(True)
    assert settings.textEditor["readableMode"] is True
    # Icon-only button: no "Readable" or "MD Code" text labels
    assert bar.btnReadable.text() == ""
    assert "Readable mode" in bar.btnReadable.toolTip()

    # Verify underlying Markdown text is untouched
    assert e.toPlainText() == "# Heading One\nParagraph with **bold** and *italic* text."
    # Verify opening markup '#' on block 0 AND '**' / '*' on active block 1 have collapsed point size (0.1)
    b0 = e.document().firstBlock()
    b1 = b0.next()
    formats0 = b0.layout().formats()
    formats1 = b1.layout().formats()
    assert any(r.start == 0 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05) for r in formats0)
    # '*italic*' opening '*' is at index 28 in "Paragraph with **bold** and *italic* text."
    assert any(r.start == 28 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05) for r in formats1)

    # Also verify tab-indented novel paragraphs (`\t*italic*`) tokenize as prose (not code block) and collapse '*'
    e.setPlainText("\t*No shit,* Arch thought, wondering who *exactly* might use it.")
    e.highlighter.rehighlight()
    b_tab = e.document().firstBlock()
    tab_formats = b_tab.layout().formats()
    assert any(r.start == 1 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05) for r in tab_formats)
    assert any(r.start == 2 and r.format.fontItalic() is True for r in tab_formats)

    # Toggle back to MD Code Visible mode
    bar.btnReadable.setChecked(False)
    assert settings.textEditor["readableMode"] is False
    assert bar.btnReadable.text() == ""
    assert "Markdown code visible" in bar.btnReadable.toolTip()
    formats_after = b0.layout().formats()
    assert not any(r.start == 0 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05) for r in formats_after)


def test_markdown_formatting_buttons_toggle_off_instead_of_stacking(MWSampleProject):
    MW = MWSampleProject
    bar = MW.mainEditor.formatBar
    e = _openScene(MWSampleProject)
    e.setPlainText("hello world")
    bar._view = e
    e.show()

    # 1. Select "hello" and click Bold -> "**hello** world"
    c = e.textCursor()
    c.setPosition(0)
    c.setPosition(5, QTextCursor.KeepAnchor)
    e.setTextCursor(c)
    bar.btnBold.click()
    assert e.toPlainText() == "**hello** world"

    # Click Bold a second time to untoggle -> "hello world" (NOT "****hello**** world")
    bar.btnBold.click()
    assert e.toPlainText() == "hello world"

    # 2. Click Italic on "hello" -> "*hello* world", click again -> "hello world"
    bar.btnItalic.click()
    assert e.toPlainText() == "*hello* world"
    bar.btnItalic.click()
    assert e.toPlainText() == "hello world"

    # 3. Empty selection: clicking Bold does NOT pollute document with empty "****"
    e.setPlainText("")
    bar.btnBold.click()
    assert e.toPlainText() == ""
    assert "**" in e._pendingFormats
    bar.btnBold.click()
    assert "**" not in e._pendingFormats
    assert e.toPlainText() == ""

    # 4. Heading toggle: click H1 -> "# hello", click H1 again -> "hello"
    e.setPlainText("hello")
    bar.btnH1.click()
    assert e.toPlainText() == "# hello"
    bar.btnH1.click()
    assert e.toPlainText() == "hello"


def test_ai_dock_undock_and_redock_button(MWSampleProject):
    MW = MWSampleProject
    dock = MW.dckAI
    dock.show()
    # Native dock titlebar is replaced with a dummy widget so 'X' close / tiny float target are removed
    assert dock.titleBarWidget() is not None
    assert not dock.isFloating()
    assert dock.btnDock.property("dockState") == "undock"
    assert not dock.btnDock.icon().isNull()

    # Click to undock (float)
    dock.toggleFloating()
    assert dock.isFloating()
    assert dock.btnDock.property("dockState") == "dock"

    # Click to re-dock back into the main window
    dock.toggleFloating()
    assert not dock.isFloating()
    assert dock.btnDock.property("dockState") == "undock"
    dock.hide()


def test_formatting_trims_trailing_whitespace():
    e = MDEditView()
    e.setPlainText("Watson: \tAnd then")
    c = e.textCursor()
    c.setPosition(0)
    c.setPosition(9, QTextCursor.KeepAnchor)  # "Watson: \t"
    e.setTextCursor(c)
    e.bold()
    # Trailing whitespace kept outside markup
    assert e.toPlainText() == "**Watson:** \tAnd then"


def test_formatting_step_out_without_inserting_markup():
    e = MDEditView()
    e.setPlainText("*word*")
    c = e.textCursor()
    c.setPosition(5)  # right before closing '*'
    e.setTextCursor(c)
    e.italic()  # hitting italic to exit formatting
    # Must step cursor past '*' to position 6 without inserting '**'
    assert e.textCursor().position() == 6
    assert e.toPlainText() == "*word*"


def test_convert_to_clean_md():
    e = MDEditView()
    e.setPlainText("**Watson: \t**said nothing. **** empty ** stray.")
    e.convertToCleanMD()
    assert e.toPlainText() == "**Watson:** \tsaid nothing.  empty  stray."


def test_alignment_buttons_apply_to_block_format():
    from PyQt5.QtCore import Qt
    bar = FB.FormatBar()
    e = MDEditView()
    e.setPlainText("Chapter 1\n\nOnce upon a time.")
    bar._view = e
    e.show()
    c = e.textCursor()
    c.setPosition(0)
    c.setPosition(9, QTextCursor.KeepAnchor)  # select "Chapter 1"
    e.setTextCursor(c)
    bar._setAlignmentIndex(1)  # Center
    b1 = e.document().firstBlock()
    b2 = b1.next()
    assert bool(b1.blockFormat().alignment() & Qt.AlignHCenter)
    # Second block MUST remain Left-aligned (not centered across the whole document)
    assert bool(b2.blockFormat().alignment() & Qt.AlignLeft)
    assert not bool(b2.blockFormat().alignment() & Qt.AlignHCenter)
    # Move cursor to second block and justify it
    c.setPosition(15)
    e.setTextCursor(c)
    bar._setAlignmentIndex(3)  # Justify
    b2 = e.document().findBlock(15)
    assert bool(b2.blockFormat().alignment() & Qt.AlignJustify)
    # First block still centered
    assert bool(e.document().firstBlock().blockFormat().alignment() & Qt.AlignHCenter)


def test_lists_visible_in_readable_mode_and_sequential_numbering(MWSampleProject):
    MW = MWSampleProject
    bar = MW.mainEditor.formatBar
    e = _openScene(MWSampleProject)
    settings.textEditor["readableMode"] = True
    e.setPlainText("# Shopping\nApples\nBananas\nCherries")
    bar._view = e
    e.show()

    # Select the 3 items below the heading and click Numbered List
    c = e.textCursor()
    c.setPosition(11)
    c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    e.setTextCursor(c)
    bar.btnNumberedList.click()
    assert e.toPlainText() == "# Shopping\n1. Apples\n2. Bananas\n3. Cherries"

    # In Readable Mode, '1. ' must NOT be collapsed to 0.1pt (must remain visible)
    e.highlighter.rehighlight()
    b_item1 = e.document().firstBlock().next()
    item1_formats = b_item1.layout().formats()
    assert not any(
        r.start == 0 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05)
        for r in item1_formats
    )

    # Switch to Bullet List on those 3 items
    bar.btnBulletList.click()
    assert e.toPlainText() == "# Shopping\n- Apples\n- Bananas\n- Cherries"
    e.highlighter.rehighlight()
    b_bullet1 = e.document().firstBlock().next()
    bullet1_formats = b_bullet1.layout().formats()
    assert not any(
        r.start == 0 and r.format.font().pointSizeF() == pytest.approx(0.1, abs=0.05)
        for r in bullet1_formats
    )


def test_line_numbers_toggle_and_ai_context_injection(MWSampleProject):
    from moduskript.ai.context import numberLines
    MW = MWSampleProject
    bar = MW.mainEditor.formatBar
    e = _openScene(MWSampleProject)
    e.setPlainText("First line\nSecond line\nThird line")
    bar._view = e
    e.show()

    # Toggle line numbers ON
    bar._toggleLineNumbers(True)
    assert settings.textEditor["lineNumbers"] is True
    assert e.lineNumberAreaWidth() > 0
    assert not e._lineNumberArea.isHidden()

    # Toggle line numbers OFF
    bar.btnLineNumbers.setChecked(False)
    assert settings.textEditor["lineNumbers"] is False
    assert e.lineNumberAreaWidth() == 0
    assert e._lineNumberArea.isHidden()

    # Restore ON
    bar.btnLineNumbers.setChecked(True)
    assert not e._lineNumberArea.isHidden()

    # Verify AI context line numbering helper (including soft-wrapped visual lines)
    numbered = numberLines("Alpha\nBeta\nGamma", startLine=10)
    assert numbered == "10: Alpha\n11: Beta\n12: Gamma"
    long_para = " ".join(["word"] * 40)
    wrapped_numbered = numberLines(long_para, startLine=1, width=60)
    assert "1: " in wrapped_numbered
    assert "2: " in wrapped_numbered
    assert "3: " in wrapped_numbered

    # Verify MDEditView counts wrapped visual lines within a single paragraph
    e.resize(400, 300)
    e.setPlainText(long_para)
    e.document().setTextWidth(300)
    assert e.visualLineCount() >= 2
    v_lines = e.getVisualNumberedLines()
    assert len(v_lines) >= 2
    assert v_lines[0][0] == 1 and v_lines[1][0] == 2


def test_ai_dock_stop_button_cancels_cleanly(MWSampleProject):
    from moduskript.ai.workers import ChatWorker
    MW = MWSampleProject
    dock = MW.dckAI
    req = {
        "provider": "Local / Llama.cpp",
        "endpoint": "http://127.0.0.1:9",
        "apiKey": "",
        "model": "test-model",
        "system": "sys",
        "history": [{"role": "user", "content": "hi"}],
    }
    w = ChatWorker(req, None)
    dock._activeWorkers.add(w)
    dock.worker = w
    dock._pending = "Hello AI"
    dock._streamAgent = "Co-author"
    dock._streamText = "Partial answer"
    dock.btnCancel.setVisible(True)
    dock.cancel()
    assert dock.worker is None
    assert not dock.btnCancel.isVisible()
    assert "Generation cancelled" in dock.view.toPlainText()


def test_ai_dock_renders_markdown_formatting(MWSampleProject):
    from moduskript.ai.dock import markdownToHtml
    MW = MWSampleProject
    dock = MW.dckAI
    html_out = markdownToHtml("### Scene Notes\nUse **strong verbs** and *vivid* imagery.\n- Item one\n- Item two")
    assert "<h3>" in html_out or "<h3" in html_out
    assert "<strong>strong verbs</strong>" in html_out
    assert "<em>vivid</em>" in html_out

    dock.chat["messages"] = [
        {"role": "user", "content": "Check **Line 1** please"},
        {"role": "assistant", "agent": "Editor", "content": "### Feedback\nReplace **walked** with *strode*."},
    ]
    dock._pending = None
    dock._extraNotice = ""
    dock.renderAll()
    plain = dock.view.toPlainText()
    assert "Feedback" in plain
    assert "Replace walked with strode." in plain
    assert "**walked**" not in plain
    assert "###" not in plain




