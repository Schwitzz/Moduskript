# --!-- coding: utf8 --!--
"""Icon-led formatting bar shown above the main text editor (Web Editor parity).

Primary Row:
  Undo, Redo | Style dropdown, H1, H2, H3 | Bold, Italic, Strikethrough |
  Quote, Bullet List, Numbered List | Align Left, Center, Right, Justify |
  Typography & Spacing popover button (Font, Size, Line spacing, Paragraph spacing, Indent, Tab spaces) |
  Readable / MD Code toggle button.

All settings controls (`cmbFont`, `spnSize`, `cmbAlign`, `cmbSpacing`, `spnPara`, `chkIndent`, `spnTab`)
remain synced with Settings -> Views & Editor -> Text editor.
"""

import re

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFontComboBox, QFormLayout,
                             QFrame, QHBoxLayout, QLabel, QMenu, QSpinBox,
                             QToolButton, QVBoxLayout, QWidget, QWidgetAction,
                             qApp)

from moduskript import settings
from moduskript.functions import mainWindow
from moduskript.ui.modernIcons import icon as modernIcon
from moduskript.ui.views.MDEditView import MDEditView

STYLES = ["Body text", "Heading 1", "Heading 2", "Heading 3", "Heading 4",
          "Quote", "Bullet list", "Numbered list"]
_PREFIX = {"Body text": "", "Heading 1": "# ", "Heading 2": "## ",
           "Heading 3": "### ", "Heading 4": "#### ", "Quote": "> ",
           "Bullet list": "- ", "Numbered list": "1. "}
_STRIP = re.compile(r"^\s*(#{1,6}\s+|>\s*|[-*+]\s+|\d+[.)]\s+)")
ALIGNMENTS = ["Left", "Center", "Right", "Justify"]
SPACINGS = [("Single", 100), ("1.15", 115), ("1.5", 150), ("Double", 200)]


def styleOf(text):
    """Paragraph style name of one line of Markdown text."""
    m = _STRIP.match(text)
    if not m:
        return "Body text"
    p = m.group(1).strip()
    if p.startswith("#"):
        return "Heading %d" % min(len(p), 4)
    if p.startswith(">"):
        return "Quote"
    if p[0] in "-*+":
        return "Bullet list"
    return "Numbered list"


def restyle(text, style):
    """Return `text` with its block prefix replaced by the one for `style`."""
    return _PREFIX[style] + _STRIP.sub("", text, count=1)


class FormatBar(QFrame):

    def __init__(self, parent=None):
        QFrame.__init__(self, parent)
        self.setObjectName("formatBar")
        self._updating = False
        self._view = None
        self._watched = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(2)
        row1 = QHBoxLayout()
        row1.setSpacing(3)
        outer.addLayout(row1)

        # ---- Undo / Redo
        self.btnUndo = self._iconBtn("undo", self.tr("Undo (Ctrl+Z)"))
        self.btnRedo = self._iconBtn("redo", self.tr("Redo (Ctrl+Y)"))
        row1.addWidget(self.btnUndo)
        row1.addWidget(self.btnRedo)
        row1.addWidget(self._sep())

        # ---- Paragraph style & H1 / H2 / H3 quick icon buttons
        self.cmbStyle = QComboBox()
        self.cmbStyle.addItems([self.tr(s) for s in STYLES])
        self.cmbStyle.setToolTip(self.tr("Paragraph style (applies to selected paragraphs)"))
        self.cmbStyle.setMaximumWidth(125)
        self.btnH1 = self._iconBtn("heading-1", self.tr("Heading 1"))
        self.btnH2 = self._iconBtn("heading-2", self.tr("Heading 2"))
        self.btnH3 = self._iconBtn("heading-3", self.tr("Heading 3"))
        row1.addWidget(self.cmbStyle)
        row1.addWidget(self.btnH1)
        row1.addWidget(self.btnH2)
        row1.addWidget(self.btnH3)
        row1.addWidget(self._sep())

        # ---- Inline formatting: Bold / Italic / Strikethrough
        self.btnBold = self._iconBtn("bold", self.tr("Bold (Ctrl+B)"))
        self.btnItalic = self._iconBtn("italic", self.tr("Italic (Ctrl+I)"))
        self.btnStrike = self._iconBtn("strikethrough", self.tr("Strikethrough"))
        for b in (self.btnBold, self.btnItalic, self.btnStrike):
            b.setCheckable(True)
            row1.addWidget(b)
        row1.addWidget(self._sep())

        # ---- Block formatting: Quote / Bullet List / Numbered List
        self.btnQuote = self._iconBtn("quote", self.tr("Blockquote"))
        self.btnBulletList = self._iconBtn("list", self.tr("Bullet list"))
        self.btnNumberedList = self._iconBtn("list-ordered", self.tr("Numbered list"))
        for b in (self.btnQuote, self.btnBulletList, self.btnNumberedList):
            row1.addWidget(b)
        row1.addWidget(self._sep())

        # ---- Alignment icon buttons (synced with self.cmbAlign)
        self.btnAlignLeft = self._iconBtn("align-left", self.tr("Align Left"))
        self.btnAlignCenter = self._iconBtn("align-center", self.tr("Align Center"))
        self.btnAlignRight = self._iconBtn("align-right", self.tr("Align Right"))
        self.btnAlignJustify = self._iconBtn("align-justify", self.tr("Justify"))
        for idx, b in enumerate((self.btnAlignLeft, self.btnAlignCenter,
                                 self.btnAlignRight, self.btnAlignJustify)):
            b.setCheckable(True)
            b.clicked.connect(lambda _c=False, i=idx: self._setAlignmentIndex(i))
            row1.addWidget(b)
        row1.addWidget(self._sep())

        # ---- Typography & Spacing Popover (holds cmbFont, spnSize, cmbAlign, cmbSpacing, spnPara, chkIndent, spnTab)
        self.cmbFont = QFontComboBox()
        self.cmbFont.setToolTip(self.tr("Editor font"))
        self.cmbFont.setMaximumWidth(170)
        self.spnSize = QSpinBox()
        self.spnSize.setRange(6, 72)
        self.spnSize.setSuffix(" pt")
        self.spnSize.setToolTip(self.tr("Editor font size"))

        self.cmbAlign = QComboBox()
        self.cmbAlign.addItems([self.tr(a) for a in ALIGNMENTS])
        self.cmbAlign.setToolTip(self.tr("Text alignment"))
        self.cmbSpacing = QComboBox()
        for name, val in SPACINGS:
            self.cmbSpacing.addItem(self.tr(name), val)
        self.cmbSpacing.setToolTip(self.tr("Line spacing"))
        self.spnPara = QSpinBox()
        self.spnPara.setRange(0, 60)
        self.spnPara.setSuffix(" px")
        self.spnPara.setToolTip(self.tr("Space below each paragraph"))
        self.chkIndent = QCheckBox(self.tr("First-line indent"))
        self.chkIndent.setToolTip(self.tr("Indent the first line of each paragraph"))
        self.spnTab = QSpinBox()
        self.spnTab.setRange(1, 24)
        self.spnTab.setSuffix(self.tr(" spaces"))
        self.spnTab.setToolTip(self.tr("Width of the Tab key and of the indent"))

        self.btnTypography = QToolButton()
        self.btnTypography.setIcon(modernIcon("sliders", 17))
        self.btnTypography.setIconSize(QSize(17, 17))
        self.btnTypography.setMinimumSize(30, 28)
        self.btnTypography.setPopupMode(QToolButton.InstantPopup)
        self.btnTypography.setToolTip(
            self.tr("Typography, Font, Line Spacing, Paragraph Spacing & Tab Width")
        )
        typo_menu = QMenu(self.btnTypography)
        typo_panel = QWidget(typo_menu)
        typo_form = QFormLayout(typo_panel)
        typo_form.setContentsMargins(10, 10, 10, 10)
        typo_form.setSpacing(6)
        typo_form.addRow(self.tr("Font:"), self.cmbFont)
        typo_form.addRow(self.tr("Size:"), self.spnSize)
        typo_form.addRow(self.tr("Align:"), self.cmbAlign)
        typo_form.addRow(self.tr("Line spacing:"), self.cmbSpacing)
        typo_form.addRow(self.tr("Space below:"), self.spnPara)
        typo_form.addRow(self.tr("Tab width:"), self.spnTab)
        typo_form.addRow("", self.chkIndent)
        typo_act = QWidgetAction(typo_menu)
        typo_act.setDefaultWidget(typo_panel)
        typo_menu.addAction(typo_act)
        self.btnTypography.setMenu(typo_menu)
        row1.addWidget(self.btnTypography)

        # ---- Line numbers toggle button
        self.btnLineNumbers = QToolButton()
        self.btnLineNumbers.setCheckable(True)
        self.btnLineNumbers.setFocusPolicy(Qt.NoFocus)
        self.btnLineNumbers.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btnLineNumbers.setIconSize(QSize(17, 17))
        self.btnLineNumbers.setMinimumSize(30, 28)
        self._updateLineNumbersButton(settings.textEditor.get("lineNumbers", True))
        self.btnLineNumbers.toggled.connect(self._toggleLineNumbers)
        row1.addWidget(self.btnLineNumbers)

        # ---- Readable / MD Code mode toggle button (icon-only, tooltip provides context)
        self.btnReadable = QToolButton()
        self.btnReadable.setCheckable(True)
        self.btnReadable.setFocusPolicy(Qt.NoFocus)
        self.btnReadable.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btnReadable.setIconSize(QSize(17, 17))
        self.btnReadable.setMinimumSize(30, 28)
        self._updateReadableButton(settings.textEditor.get("readableMode", False))
        self.btnReadable.toggled.connect(self._toggleReadableMode)
        row1.addWidget(self.btnReadable)
        row1.addStretch(1)

        # Connections
        self.btnUndo.clicked.connect(lambda: self._call("undo"))
        self.btnRedo.clicked.connect(lambda: self._call("redo"))
        self.cmbStyle.activated.connect(self._applyStyle)
        self.btnH1.clicked.connect(lambda: self._applyNamedStyle("Heading 1"))
        self.btnH2.clicked.connect(lambda: self._applyNamedStyle("Heading 2"))
        self.btnH3.clicked.connect(lambda: self._applyNamedStyle("Heading 3"))
        self.btnBold.clicked.connect(lambda: self._call("bold"))
        self.btnItalic.clicked.connect(lambda: self._call("italic"))
        self.btnStrike.clicked.connect(lambda: self._call("strike"))
        self.btnQuote.clicked.connect(lambda: self._applyNamedStyle("Quote"))
        self.btnBulletList.clicked.connect(lambda: self._applyNamedStyle("Bullet list"))
        self.btnNumberedList.clicked.connect(lambda: self._applyNamedStyle("Numbered list"))

        self.cmbFont.activated.connect(self._settingsChanged)
        self.spnSize.valueChanged.connect(self._settingsChanged)
        self.cmbAlign.activated.connect(self._settingsChanged)
        self.cmbSpacing.activated.connect(self._settingsChanged)
        self.spnPara.valueChanged.connect(self._settingsChanged)
        self.chkIndent.toggled.connect(self._settingsChanged)
        self.spnTab.valueChanged.connect(self._settingsChanged)

        qApp.focusChanged.connect(self._focusChanged)
        self.refresh()

    def _sep(self):
        s = QFrame()
        s.setFrameShape(QFrame.VLine)
        s.setFrameShadow(QFrame.Sunken)
        return s

    def _iconBtn(self, icon_name, tip):
        b = QToolButton()
        b.setIcon(modernIcon(icon_name, 17))
        b.setIconSize(QSize(17, 17))
        b.setToolTip(tip)
        b.setFocusPolicy(Qt.NoFocus)
        b.setMinimumSize(30, 28)
        return b

    def _setAlignmentIndex(self, index):
        align_flags = [Qt.AlignLeft, Qt.AlignHCenter, Qt.AlignRight, Qt.AlignJustify]
        target_align = align_flags[index]
        v = self.target()
        if v is not None:
            from PyQt5.QtGui import QTextBlockFormat
            cur = v.textCursor()
            doc = v.document()
            first = doc.findBlock(cur.selectionStart())
            last = doc.findBlock(cur.selectionEnd())
            if cur.hasSelection() and last != first and cur.selectionEnd() == last.position():
                last = last.previous()
            cur.beginEditBlock()
            b = first
            while b.isValid():
                c = QTextCursor(b)
                bf = c.blockFormat()
                bf.setAlignment(target_align)
                bf.setProperty(QTextBlockFormat.UserProperty, int(target_align))
                c.setBlockFormat(bf)
                if b == last:
                    break
                b = b.next()
            cur.endEditBlock()
            self._syncAlignmentButtons(index)
            v.setFocus()
            return
        self.cmbAlign.setCurrentIndex(index)
        self._syncAlignmentButtons(index)
        self._settingsChanged()

    def _syncAlignmentButtons(self, active_idx):
        for idx, b in enumerate((self.btnAlignLeft, self.btnAlignCenter,
                                 self.btnAlignRight, self.btnAlignJustify)):
            b.blockSignals(True)
            b.setChecked(idx == active_idx)
            b.blockSignals(False)

    def _applyNamedStyle(self, style_name):
        if style_name in STYLES:
            v = self.target()
            if v is not None:
                cur_style = styleOf(v.textCursor().block().text())
                if cur_style == style_name:
                    style_name = "Body text"
            self.cmbStyle.setCurrentIndex(STYLES.index(style_name))
            self._applyStyle()

    # ------------------------------------------------------- target view
    def _focusChanged(self, old, new):
        if isinstance(new, MDEditView) and new.isVisible():
            self._view = new
            if new not in self._watched:
                self._watched.add(new)
                new.cursorPositionChanged.connect(self._cursorMoved)
                new.destroyed.connect(lambda *_a, v=new: self._watched.discard(v))
            self._cursorMoved()

    def target(self):
        """The Markdown editor the bar acts on, or None."""
        v = self._view
        try:
            if v is not None and v.isVisible():
                return v
        except RuntimeError:              # underlying widget was deleted
            self._view = None
        try:
            ed = mainWindow().mainEditor.currentEditor()
            v = ed.getCurrentItemView() if ed else None
        except Exception:
            v = None
        return v if isinstance(v, MDEditView) else None

    def _cursorMoved(self):
        v = self.target()
        if v is None or self._updating:
            return
        self._updating = True
        cur = v.textCursor()
        cur_block = cur.block()
        self.cmbStyle.setCurrentIndex(
            STYLES.index(styleOf(cur_block.text())))

        # Sync alignment buttons to current block alignment
        block_align = cur_block.blockFormat().alignment()
        if block_align & Qt.AlignHCenter:
            align_idx = 1
        elif block_align & Qt.AlignRight:
            align_idx = 2
        elif block_align & Qt.AlignJustify:
            align_idx = 3
        else:
            align_idx = 0
        self._syncAlignmentButtons(align_idx)

        # Sync inline formatting buttons
        fmt = cur.charFormat()
        is_bold = fmt.fontWeight() > QFont.Normal or "**" in getattr(v, "_pendingFormats", ())
        is_italic = fmt.fontItalic() or "*" in getattr(v, "_pendingFormats", ())
        is_strike = fmt.fontStrikeOut() or "~~" in getattr(v, "_pendingFormats", ())
        for b, state in ((self.btnBold, is_bold), (self.btnItalic, is_italic), (self.btnStrike, is_strike)):
            b.blockSignals(True)
            b.setChecked(bool(state))
            b.blockSignals(False)

        self._updating = False

    # ----------------------------------------------------------- actions
    def _call(self, name):
        v = self.target()
        if v is not None:
            getattr(v, name)()
            v.setFocus()

    def _applyStyle(self, _i=None):
        v = self.target()
        if v is None or self._updating:
            return
        style = STYLES[self.cmbStyle.currentIndex()]
        cur = v.textCursor()
        doc = v.document()
        first = doc.findBlock(cur.selectionStart())
        last = doc.findBlock(cur.selectionEnd())
        if cur.hasSelection() and last != first and cur.selectionEnd() == last.position():
            last = last.previous()
        single_block = (first == last)
        cur.beginEditBlock()
        b = first
        num_idx = 1
        while b.isValid():
            c = QTextCursor(b)
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if b.text().strip() or single_block:
                if style == "Numbered list":
                    body = _STRIP.sub("", b.text(), count=1)
                    c.insertText(f"{num_idx}. {body}")
                    num_idx += 1
                else:
                    c.insertText(restyle(b.text(), style))
            if b == last:
                break
            b = b.next()
        cur.endEditBlock()
        if single_block and not cur.hasSelection():
            c_end = QTextCursor(first)
            c_end.movePosition(QTextCursor.EndOfBlock)
            v.setTextCursor(c_end)
        v.setFocus()

    def _settingsChanged(self, *_a):
        if self._updating:
            return
        o = settings.textEditor
        f = QFont()
        f.fromString(o["font"])
        f.setFamily(self.cmbFont.currentFont().family())
        f.setPointSize(self.spnSize.value())
        o["font"] = f.toString()
        o["textAlignment"] = self.cmbAlign.currentIndex()
        self._syncAlignmentButtons(o["textAlignment"])
        o["lineSpacing"] = self.cmbSpacing.currentData() or o["lineSpacing"]
        o["spacingBelow"] = self.spnPara.value()
        o["indent"] = self.chkIndent.isChecked()
        o["tabSpaces"] = self.spnTab.value()
        self._pushToSettingsWindow()
        mw = mainWindow()
        if mw is not None:
            sw = getattr(mw, "sw", None)
            if sw is not None:
                sw.updateAllWidgets()         # reloads every editor's format
            else:
                from moduskript.ui.views.textEditView import textEditView
                from PyQt5.QtCore import QRegExp
                for w in mw.findChildren(textEditView, QRegExp(".*")):
                    w.loadFontSettings()
        v = self.target()
        if v is not None:
            v.setFocus()

    def _pushToSettingsWindow(self):
        """Mirror the values into the Settings window without re-triggering it."""
        sw = getattr(mainWindow(), "sw", None)
        if sw is None:
            return
        o = settings.textEditor
        f = QFont()
        f.fromString(o["font"])
        ls = o["lineSpacing"]

        def put(w, fn):
            w.blockSignals(True)
            fn(w)
            w.blockSignals(False)

        put(sw.cmbEditorFontFamily, lambda w: w.setCurrentFont(f))
        put(sw.spnEditorFontSize, lambda w: w.setValue(f.pointSize()))
        put(sw.cmbEditorAlignment, lambda w: w.setCurrentIndex(o["textAlignment"]))
        put(sw.cmbEditorLineSpacing, lambda w: w.setCurrentIndex(
            0 if ls == 100 else 1 if ls == 150 else 2 if ls == 200 else 3))
        put(sw.spnEditorLineSpacing, lambda w: w.setValue(ls))
        sw.spnEditorLineSpacing.setEnabled(ls not in (100, 150, 200))
        put(sw.spnEditorParaBelow, lambda w: w.setValue(o["spacingBelow"]))
        put(sw.chkEditorIndent, lambda w: w.setChecked(o["indent"]))
        put(sw.spnEditorTabWidth, lambda w: w.setValue(o.get("tabSpaces", 4)))
        if hasattr(sw, "chkEditorReadableMode"):
            put(sw.chkEditorReadableMode, lambda w: w.setChecked(o.get("readableMode", False)))

    def refresh(self):
        """Show the current editor settings (also called when Settings changes)."""
        o = settings.textEditor
        f = QFont()
        f.fromString(o["font"])
        widgets = (self.cmbFont, self.spnSize, self.cmbAlign, self.cmbSpacing,
                   self.spnPara, self.chkIndent, self.spnTab)
        self._updating = True
        for w in widgets:
            w.blockSignals(True)
        self.cmbFont.setCurrentFont(f)
        self.spnSize.setValue(f.pointSize() if f.pointSize() > 0 else 12)
        self.cmbAlign.setCurrentIndex(o["textAlignment"])
        self._syncAlignmentButtons(o["textAlignment"])
        # A custom line spacing gets its own entry so nothing is hidden.
        while self.cmbSpacing.count() > len(SPACINGS):
            self.cmbSpacing.removeItem(self.cmbSpacing.count() - 1)
        i = self.cmbSpacing.findData(o["lineSpacing"])
        if i < 0:
            self.cmbSpacing.addItem("%d%%" % o["lineSpacing"], o["lineSpacing"])
            i = self.cmbSpacing.count() - 1
        self.cmbSpacing.setCurrentIndex(i)
        self.spnPara.setValue(o["spacingBelow"])
        self.chkIndent.setChecked(o["indent"])
        self.spnTab.setValue(o.get("tabSpaces", 4))
        self.btnReadable.blockSignals(True)
        self._updateReadableButton(o.get("readableMode", False))
        self.btnReadable.blockSignals(False)
        self.btnLineNumbers.blockSignals(True)
        self._updateLineNumbersButton(o.get("lineNumbers", True))
        self.btnLineNumbers.blockSignals(False)
        for w in widgets:
            w.blockSignals(False)
        self._updating = False

    def _updateReadableButton(self, readable_on):
        self.btnReadable.blockSignals(True)
        self.btnReadable.setChecked(bool(readable_on))
        self.btnReadable.blockSignals(False)
        self.btnReadable.setText("")
        if readable_on:
            self.btnReadable.setIcon(modernIcon("book-open", 17, accent=True))
            self.btnReadable.setToolTip(
                self.tr("Word Processor / Readable mode active (Markdown syntax hidden — click 'Convert to MD' to show Markdown code)")
            )
        else:
            self.btnReadable.setIcon(modernIcon("code", 17))
            self.btnReadable.setToolTip(
                self.tr("Markdown code visible (click to switch to Word Processor view)")
            )

    def _toggleReadableMode(self, checked):
        if self._updating:
            return
        settings.textEditor["readableMode"] = bool(checked)
        try:
            from PyQt5.QtCore import QSettings
            QSettings().setValue("textEditor/readableMode", bool(checked))
        except Exception:
            pass
        self._updateReadableButton(checked)
        self._pushToSettingsWindow()
        v = self.target()
        if v is not None:
            if not checked and hasattr(v, "convertToCleanMD"):
                v.convertToCleanMD()
            if getattr(v, "highlighter", None) is not None:
                v.highlighter.rehighlight()
        from moduskript.functions import findWidgetsOfClass
        for ed in findWidgetsOfClass(MDEditView):
            if ed is not v and getattr(ed, "highlighter", None) is not None:
                if not checked and hasattr(ed, "convertToCleanMD"):
                    ed.convertToCleanMD()
                ed.highlighter.rehighlight()
        if v is not None:
            v.setFocus()

    def _updateLineNumbersButton(self, line_numbers_on):
        self.btnLineNumbers.blockSignals(True)
        self.btnLineNumbers.setChecked(bool(line_numbers_on))
        self.btnLineNumbers.blockSignals(False)
        self.btnLineNumbers.setIcon(modernIcon("hash", 17, accent=bool(line_numbers_on)))
        if line_numbers_on:
            self.btnLineNumbers.setToolTip(
                self.tr("Line numbers visible (click to hide line numbers)")
            )
        else:
            self.btnLineNumbers.setToolTip(
                self.tr("Line numbers hidden (click to show line numbers)")
            )

    def _toggleLineNumbers(self, checked):
        if self._updating:
            return
        settings.textEditor["lineNumbers"] = bool(checked)
        try:
            from PyQt5.QtCore import QSettings
            QSettings().setValue("textEditor/lineNumbers", bool(checked))
        except Exception:
            pass
        self._updateLineNumbersButton(checked)
        v = self.target()
        if v is not None and hasattr(v, "updateLineNumberAreaGeometry"):
            v.updateLineNumberAreaGeometry()
        from moduskript.functions import findWidgetsOfClass
        for ed in findWidgetsOfClass(MDEditView):
            if ed is not v and hasattr(ed, "updateLineNumberAreaGeometry"):
                ed.updateLineNumberAreaGeometry()
        if v is not None:
            v.setFocus()
