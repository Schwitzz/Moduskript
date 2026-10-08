# --!-- coding: utf8 --!--
"""Formatting bar shown above the main text editor.

Row 1: paragraph style, font, size, bold / italic / strike.
Row 2: alignment, line spacing, paragraph spacing, first-line indent, tab width.

Paragraph style and bold/italic act on the text in the editor (Markdown).
Everything in row 2 and the font are the same app-wide editor settings as
Settings -> Views -> Text editor, so both places always show the same values.
"""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QFontComboBox, QFrame,
                             QHBoxLayout, QLabel, QSpinBox, QToolButton,
                             QVBoxLayout, qApp)

from manuskript import settings
from manuskript.functions import mainWindow
from manuskript.ui.views.MDEditView import MDEditView

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
        outer.setSpacing(4)
        row1, row2 = QHBoxLayout(), QHBoxLayout()
        for r in (row1, row2):
            r.setSpacing(6)
        outer.addLayout(row1)
        outer.addLayout(row2)

        # ---- row 1
        self.cmbStyle = QComboBox()
        self.cmbStyle.addItems([self.tr(s) for s in STYLES])
        self.cmbStyle.setToolTip(self.tr("Paragraph style (applies to the selected paragraphs)"))
        self.cmbFont = QFontComboBox()
        self.cmbFont.setToolTip(self.tr("Editor font"))
        self.cmbFont.setMaximumWidth(190)
        self.spnSize = QSpinBox()
        self.spnSize.setRange(6, 72)
        self.spnSize.setSuffix(" pt")
        self.spnSize.setToolTip(self.tr("Editor font size"))
        row1.addWidget(self.cmbStyle)
        row1.addWidget(self.cmbFont)
        row1.addWidget(self.spnSize)
        row1.addWidget(self._sep())
        self.btnBold = self._button("B", self.tr("Bold (Ctrl+B)"), bold=True)
        self.btnItalic = self._button("I", self.tr("Italic (Ctrl+I)"), italic=True)
        self.btnStrike = self._button("S", self.tr("Strikethrough"), strike=True)
        for b in (self.btnBold, self.btnItalic, self.btnStrike):
            row1.addWidget(b)
        row1.addStretch(1)

        # ---- row 2
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
        self.chkIndent = QCheckBox(self.tr("Indent"))
        self.chkIndent.setToolTip(self.tr("Indent the first line of each paragraph"))
        self.spnTab = QSpinBox()
        self.spnTab.setRange(1, 24)
        self.spnTab.setSuffix(self.tr(" spaces"))
        self.spnTab.setToolTip(self.tr("Width of the Tab key and of the indent"))
        for w in (QLabel(self.tr("Align")), self.cmbAlign,
                  QLabel(self.tr("Lines")), self.cmbSpacing,
                  QLabel(self.tr("Below")), self.spnPara,
                  self.chkIndent, QLabel(self.tr("Tab")), self.spnTab):
            row2.addWidget(w)
        row2.addStretch(1)

        self.cmbStyle.activated.connect(self._applyStyle)
        self.btnBold.clicked.connect(lambda: self._call("bold"))
        self.btnItalic.clicked.connect(lambda: self._call("italic"))
        self.btnStrike.clicked.connect(lambda: self._call("strike"))
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

    def _button(self, text, tip, bold=False, italic=False, strike=False):
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setFocusPolicy(Qt.NoFocus)      # keep the cursor in the editor
        f = QFont(b.font())
        f.setBold(bold)
        f.setItalic(italic)
        f.setStrikeOut(strike)
        b.setFont(f)
        b.setMinimumWidth(30)
        return b

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
        self.cmbStyle.setCurrentIndex(
            STYLES.index(styleOf(v.textCursor().block().text())))
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
        cur.beginEditBlock()
        b = first
        while b.isValid():
            c = QTextCursor(b)
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            if b.text().strip():          # leave empty lines alone
                c.insertText(restyle(b.text(), style))
            if b == last:
                break
            b = b.next()
        cur.endEditBlock()
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
        o["lineSpacing"] = self.cmbSpacing.currentData() or o["lineSpacing"]
        o["spacingBelow"] = self.spnPara.value()
        o["indent"] = self.chkIndent.isChecked()
        o["tabSpaces"] = self.spnTab.value()
        self._pushToSettingsWindow()
        sw = getattr(mainWindow(), "sw", None)
        if sw is not None:
            sw.updateAllWidgets()         # reloads every editor's format
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
        for w in widgets:
            w.blockSignals(False)
        self._updating = False
