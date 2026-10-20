#!/usr/bin/env python
# --!-- coding: utf8 --!--

import re

from PyQt5.QtCore import QRegExp, Qt, QTimer, QRect, QPoint, QSize
from PyQt5.QtGui import QColor, QFont, QPainter, QTextCursor
from PyQt5.QtWidgets import qApp, QToolTip, QWidget

from moduskript.ui.views.textEditView import textEditView
from moduskript.ui.highlighters import MarkdownHighlighter
from moduskript import settings
from moduskript.ui.highlighters.markdownEnums import MarkdownState as MS
from moduskript.ui.highlighters.markdownTokenizer import MarkdownTokenizer as MT
from moduskript import functions as F

import logging
LOGGER = logging.getLogger(__name__)


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        QWidget.__init__(self, editor)
        self._editor = editor
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def sizeHint(self):
        return QSize(self._editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self._editor.paintLineNumbers(event)


class MDEditView(textEditView):

    blockquoteRegex = QRegExp("^ {0,3}(>\\s*)+")
    listRegex = QRegExp(r"^(\s*)([+*-]|([0-9a-z])+([.\)]))(\s+)")
    inlineLinkRegex = QRegExp("\\[([^\n]+)\\]\\(([^\n]+)\\)")
    imageRegex = QRegExp("!\\[([^\n]*)\\]\\(([^\n]+)\\)")
    automaticLinkRegex = QRegExp("(<([a-zA-Z]+\\:[^\n]+)>)|(<([^\n]+@[^\n]+)>)")

    def __init__(self, parent=None, index=None, html=None, spellcheck=None,
                 highlighting=False, dict="", autoResize=False):
        textEditView.__init__(self, parent, index, html, spellcheck,
                              highlighting=True, dict=dict,
                              autoResize=autoResize)

        # Highlighter
        self._textFormat = "md"
        self._highlighterClass = MarkdownHighlighter
        self._noFocusMode = False
        self._lastCursorPosition = None
        self._pendingFormats = set()

        if index:
            # We have to setup things anew, for the highlighter notably
            self.setCurrentModelIndex(index)
        elif self._highlighting:
            self.highlighter = MarkdownHighlighter(self)
            self.highlighter.setDefaultBlockFormat(self._defaultBlockFormat)
            self.highlighter.updateColorScheme()

        self.cursorPositionChanged.connect(self.cursorPositionHasChanged)
        self.verticalScrollBar().rangeChanged.connect(
            self.scrollBarRangeChanged)

        # Clickable things
        self.clickRects = []
        self.textChanged.connect(self.getClickRects)
        self.document().documentLayoutChanged.connect(self.getClickRects)
        self.setMouseTracking(True)

        # Line number gutter
        self._lineNumberArea = _LineNumberArea(self)
        self.document().blockCountChanged.connect(lambda _c: self.updateLineNumberAreaGeometry())
        self.textChanged.connect(self._onLineNumbersUpdate)
        self.cursorPositionChanged.connect(self._onLineNumbersUpdate)
        self.verticalScrollBar().valueChanged.connect(lambda _v: self._onLineNumbersUpdate())
        self.updateLineNumberAreaGeometry()

    def loadFontSettings(self):
        textEditView.loadFontSettings(self)
        if hasattr(self, "_lineNumberArea"):
            self.updateLineNumberAreaGeometry()

    def visualLineCount(self):
        doc = self.document()
        total = 0
        block = doc.firstBlock()
        while block.isValid():
            if block.isVisible():
                bl = block.layout()
                total += max(1, bl.lineCount() if bl is not None else 1)
            block = block.next()
        return max(1, total)

    def getVisualNumberedLines(self, startPos=None, endPos=None):
        """Return list of (1-based visual line number, line text) across all wrapped visual lines."""
        doc = self.document()
        if doc.textWidth() <= 0 and self.viewport().width() > 40:
            doc.setTextWidth(self.viewport().width())
        out = []
        v_line = 1
        block = doc.firstBlock()
        while block.isValid():
            if block.isVisible():
                bl = block.layout()
                b_text = block.text()
                b_pos = block.position()
                lc = bl.lineCount() if bl is not None else 0
                if lc > 0:
                    for i in range(lc):
                        tl = bl.lineAt(i)
                        l_start = b_pos + tl.textStart()
                        l_end = l_start + tl.textLength()
                        seg = b_text[tl.textStart() : tl.textStart() + tl.textLength()]
                        if (startPos is None or l_end > startPos or (l_start == startPos == endPos)) and (
                            endPos is None or l_start < endPos or (l_start == endPos)
                        ):
                            out.append((v_line, seg))
                        v_line += 1
                else:
                    b_end = b_pos + len(b_text)
                    if (startPos is None or b_end >= startPos) and (endPos is None or b_pos <= endPos):
                        out.append((v_line, b_text))
                    v_line += 1
            block = block.next()
        return out

    def lineNumberAreaWidth(self):
        if getattr(self, "_autoResize", False) or not settings.textEditor.get("lineNumbers", True):
            return 0
        lines = self.visualLineCount()
        digits = max(2, len(str(lines)))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

    def updateLineNumberAreaGeometry(self):
        if not hasattr(self, "_lineNumberArea"):
            return
        w = self.lineNumberAreaWidth()
        if w <= 0:
            self.setViewportMargins(0, 0, 0, 0)
            self._lineNumberArea.hide()
            return
        self.setViewportMargins(w, 0, 0, 0)
        vp = self.viewport().geometry()
        self._lineNumberArea.setGeometry(max(0, vp.left() - w), vp.top(), w, vp.height())
        self._lineNumberArea.show()
        self._lineNumberArea.update()

    def _onLineNumbersUpdate(self):
        if hasattr(self, "_lineNumberArea") and not self._lineNumberArea.isHidden():
            if self._lineNumberArea.width() != self.lineNumberAreaWidth():
                self.updateLineNumberAreaGeometry()
            else:
                self._lineNumberArea.update()

    def paintLineNumbers(self, event):
        if not settings.textEditor.get("lineNumbers", True):
            return
        painter = QPainter(self._lineNumberArea)
        fg = QColor(settings.textEditor.get("fontColor") or "#888888")
        muted = QColor(fg)
        muted.setAlpha(110)
        active = QColor(fg)
        active.setAlpha(220)

        f = QFont(self.font())
        pt = f.pointSize()
        if pt > 2:
            f.setPointSize(max(8, pt - 1))
        f_bold = QFont(f)
        f_bold.setBold(True)

        doc = self.document()
        layout = doc.documentLayout()
        scroll_y = self.verticalScrollBar().value()
        vp_h = self.viewport().height()
        cur = self.textCursor()
        cur_block_num = cur.blockNumber()
        cur_pos_in_block = cur.position() - cur.block().position()
        gutter_w = self._lineNumberArea.width()
        fm_h = painter.fontMetrics().height()

        v_line = 1
        block = doc.firstBlock()
        while block.isValid():
            if block.isVisible():
                b_rect = layout.blockBoundingRect(block)
                bl = block.layout()
                lc = max(1, bl.lineCount() if bl is not None else 1)
                if b_rect.bottom() < scroll_y:
                    v_line += lc
                    block = block.next()
                    continue
                if b_rect.top() > scroll_y + vp_h:
                    break

                c0 = QTextCursor(block)
                r0 = self.cursorRect(c0)
                base_line_y = bl.lineAt(0).y() if (bl is not None and bl.lineCount() > 0) else 0.0
                active_subline = -1
                if block.blockNumber() == cur_block_num and bl is not None and bl.lineCount() > 0:
                    tl_cur = bl.lineForTextPosition(cur_pos_in_block)
                    if tl_cur.isValid():
                        active_subline = tl_cur.lineNumber()
                elif block.blockNumber() == cur_block_num:
                    active_subline = 0

                for i in range(lc):
                    if bl is not None and i < bl.lineCount():
                        tl = bl.lineAt(i)
                        y_pos = r0.top() + int(tl.y() - base_line_y)
                        l_height = max(int(tl.height()), fm_h)
                    else:
                        y_pos = r0.top()
                        l_height = max(r0.height(), fm_h)

                    if y_pos + l_height >= 0 and y_pos <= vp_h:
                        if i == active_subline:
                            painter.setFont(f_bold)
                            painter.setPen(active)
                        else:
                            painter.setFont(f)
                            painter.setPen(muted)
                        painter.drawText(
                            0,
                            y_pos,
                            gutter_w - 8,
                            l_height,
                            Qt.AlignRight | Qt.AlignVCenter,
                            str(v_line),
                        )
                    v_line += 1
            block = block.next()

    ###########################################################################
    # KEYPRESS
    ###########################################################################

    def keyPressEvent(self, event):
        k = event.key()
        m = event.modifiers()
        cursor = self.textCursor()

        # RETURN
        if k == Qt.Key_Return:
            if not cursor.hasSelection():
                if m & Qt.ShiftModifier:
                    # Insert Markdown-style line break
                    cursor.insertText("  ")

                if m & Qt.ControlModifier:
                    cursor.insertText("\n")
                else:
                    self.handleCarriageReturn()
            else:
                textEditView.keyPressEvent(self, event)

        # TAB
        elif k == Qt.Key_Tab:
            #self.indentText()
            # FIXME
            textEditView.keyPressEvent(self, event)
        elif k == Qt.Key_Backtab:
            #self.unindentText()
            # FIXME
            textEditView.keyPressEvent(self, event)

        elif k == Qt.Key_Right and not (m & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier)):
            if cursor.hasSelection():
                end_pos = cursor.selectionEnd()
                doc = self.document()
                doc_len = doc.characterCount()
                stepped = False
                for mlen in (2, 1):
                    if end_pos + mlen <= doc_len:
                        c_chk = QTextCursor(doc)
                        c_chk.setPosition(end_pos)
                        c_chk.setPosition(end_pos + mlen, QTextCursor.KeepAnchor)
                        if c_chk.selectedText() in ("**", "*", "~~", "`"):
                            c_new = QTextCursor(doc)
                            c_new.setPosition(end_pos + mlen)
                            self.setTextCursor(c_new)
                            stepped = True
                            break
                if stepped:
                    event.accept()
                    return
            textEditView.keyPressEvent(self, event)

        else:
            t = event.text()
            if (
                t
                and t.isprintable()
                and not (m & (Qt.ControlModifier | Qt.AltModifier))
                and getattr(self, "_pendingFormats", None)
            ):
                cursor.beginEditBlock()
                open_m = "".join(sorted(self._pendingFormats, key=len, reverse=True))
                close_m = "".join(sorted(self._pendingFormats, key=len))
                cursor.insertText(open_m + t + close_m)
                cursor.setPosition(cursor.position() - len(close_m))
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                self._pendingFormats.clear()
                event.accept()
                return

            textEditView.keyPressEvent(self, event)

    # Thanks to GhostWriter, mainly
    def handleCarriageReturn(self):
        autoInsertText = "";
        cursor = self.textCursor()
        endList = False
        moveBack = False
        text = cursor.block().text()

        if cursor.positionInBlock() < cursor.block().length() - 1:
            autoInsertText = self.getPriorIndentation()
            if cursor.positionInBlock() < len(autoInsertText):
                autoInsertText = autoInsertText[:cursor.positionInBlock()]

        else:
            s = cursor.block().userState()

            if s in [MS.MarkdownStateNumberedList,
                     MS.MarkdownStateBulletPointList]:
                self.listRegex.indexIn(text)
                g = self.listRegex.capturedTexts()
                    # 0 = "   a. " or "  * "
                    # 1 = "   "       "  "
                    # 2 =    "a."       "*"
                    # 3 =    "a"          ""
                    # 4 =     "."         ""
                    # 5 =      " "        " "

                # If the line of text is an empty list item, end the list.
                if len(g[0].strip()) == len(text.strip()):
                    endList = True

                # Else increment the list number
                elif g[3]:  # Numbered list
                    try: # digit
                        i = int(g[3])+1

                    except: # letter
                        i = chr(ord(g[3])+1)

                    autoInsertText = "{}{}{}{}".format(
                            g[1], i, g[4], g[5])

                else:  # Bullet list
                    autoInsertText = g[0]

                if text[-2:] == "  ":
                    autoInsertText = " " * len(autoInsertText)

            elif s == MS.MarkdownStateBlockquote:
                self.blockquoteRegex.indexIn(text)
                g = self.blockquoteRegex.capturedTexts()
                autoInsertText = g[0]

            elif s in [MS.MarkdownStateInGithubCodeFence,
                       MS.MarkdownStateInPandocCodeFence] and \
                 cursor.block().previous().userState() != s:
                autoInsertText = "\n" + text
                moveBack = True

            else:
                autoInsertText = self.getPriorIndentation()

        # Clear the list
        if endList:
            autoInsertText = self.getPriorIndentation()
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.insertText(autoInsertText)
            autoInsertText = ""

        # Finally, we insert
        cursor.insertText("\n" + autoInsertText)
        if moveBack:
            cursor.movePosition(QTextCursor.PreviousBlock)
            self.setTextCursor(cursor)

        self.ensureCursorVisible()

    def getPriorIndentation(self):
        text = self.textCursor().block().text()
        l = len(text) - len(text.lstrip())
        return text[:l]

    def getPriorMarkdownBlockItemStart(self, itemRegex):
        text = self.textCursor().block().text()
        if itemRegex.indexIn(text) >= 0:
            return text[itemRegex.matchedLength():]

        return ""

    ###########################################################################
    # TypeWriterScrolling
    ###########################################################################

    def setCurrentModelIndex(self, index):
        textEditView.setCurrentModelIndex(self, index)
        self.centerCursor()

    def cursorPositionHasChanged(self):
        self.centerCursor()
        # Focus mode or Readable mode: rehighlight previous and current blocks on cursor move
        if self.highlighter and (
            settings.textEditor["focusMode"]
            or settings.textEditor.get("readableMode", True)
        ):
            if self._lastCursorPosition is not None:
                block = self.document().findBlock(self._lastCursorPosition)
                self.highlighter.rehighlightBlock(block)
            self._lastCursorPosition = self.textCursor().position()
            block = self.document().findBlock(self._lastCursorPosition)
            self.highlighter.rehighlightBlock(block)

    def centerCursor(self, force=False):
        cursor = self.cursorRect()
        scrollbar = self.verticalScrollBar()
        viewport = self.viewport().rect()
        if (force or settings.textEditor["alwaysCenter"]
                or cursor.bottom() >= viewport.bottom()
                or cursor.top() <= viewport.top()):
            offset = viewport.center() - cursor.center()
            scrollbar.setValue(scrollbar.value() - offset.y())

    def scrollBarRangeChanged(self, min, max):
        """
        Adds viewport height to scrollbar max so that we can center cursor
        on screen.
        """
        if settings.textEditor["alwaysCenter"]:
            self.verticalScrollBar().blockSignals(True)
            self.verticalScrollBar().setMaximum(max + self.viewport().height())
            self.verticalScrollBar().blockSignals(False)

    ###########################################################################
    # FORMATTING
    ###########################################################################

    def bold(self): self.insertFormattingMarkup("**")
    def italic(self): self.insertFormattingMarkup("*")
    def strike(self): self.insertFormattingMarkup("~~")
    def verbatim(self): self.insertFormattingMarkup("`")
    def superscript(self): self.insertFormattingMarkup("^")
    def subscript(self): self.insertFormattingMarkup("~")
    def blockquote(self): self.lineFormattingMarkup("> ")
    def orderedList(self): self.lineFormattingMarkup(" 1. ")
    def unorderedList(self): self.lineFormattingMarkup("  - ")

    def selectWord(self, cursor):
        if cursor.selectedText():
            return
        end = cursor.selectionEnd()
        cursor.movePosition(QTextCursor.StartOfWord)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)

    def selectBlock(self, cursor):
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)

    def comment(self):
        cursor = self.textCursor()

        # Select beginning and end of words
        self.selectWord(cursor)

        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText("<!-- " + text + " -->")
        else:
            cursor.insertText("<!--  -->")
            cursor.movePosition(QTextCursor.PreviousCharacter,
                                QTextCursor.MoveAnchor, 4)
            self.setTextCursor(cursor)

    def commentLine(self):
        cursor = self.textCursor()

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        block = self.document().findBlock(start)
        block2 = self.document().findBlock(end)

        if True:
            # Method 1
            cursor.beginEditBlock()
            while block.isValid():
                self.commentBlock(block)
                if block == block2: break
                block = block.next()
            cursor.endEditBlock()

        else:
            # Method 2
            cursor.beginEditBlock()
            cursor.setPosition(block.position())
            cursor.insertText("<!--\n")
            cursor.setPosition(block2.position() + block2.length() - 1)
            cursor.insertText("\n-->")
            cursor.endEditBlock()

    def commentBlock(self, block):
        cursor = QTextCursor(block)
        text = block.text()
        if text[:5] == "<!-- " and \
           text[-4:] == " -->":
            text2 = text[5:-4]
        else:
            text2 = "<!-- " + text + " -->"
        self.selectBlock(cursor)
        cursor.insertText(text2)

    def lineFormattingMarkup(self, markup):
        """
        Toggles `markup` at the beginning of block (removes if already present, otherwise adds).
        """
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()
        stripped = markup.strip()
        cursor.beginEditBlock()
        if text.startswith(markup):
            c = QTextCursor(block)
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(markup))
            c.removeSelectedText()
        elif stripped and text.lstrip().startswith(stripped + " "):
            idx = text.find(stripped + " ")
            c = QTextCursor(block)
            c.movePosition(QTextCursor.StartOfBlock)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, idx + len(stripped) + 1)
            c.removeSelectedText()
        else:
            cursor.movePosition(cursor.StartOfBlock)
            cursor.insertText(markup)
        cursor.endEditBlock()

    def insertFormattingMarkup(self, markup):
        cursor = self.textCursor()
        doc = self.document()
        mlen = len(markup)

        def _docSlice(pos, length):
            if pos < 0 or length <= 0 or pos + length > doc.characterCount():
                return ""
            c = QTextCursor(doc)
            c.setPosition(pos)
            c.setPosition(pos + length, QTextCursor.KeepAnchor)
            return c.selectedText()

        def _isOuterMatch(start_pos, end_pos):
            before = _docSlice(start_pos - mlen, mlen)
            after = _docSlice(end_pos, mlen)
            if before != markup or after != markup:
                return False
            # For single '*' italic, ensure we aren't matching the inner '*' of '**' unless '***'
            if markup == "*":
                before2 = _docSlice(start_pos - 2, 2)
                after2 = _docSlice(end_pos, 2)
                before3 = _docSlice(start_pos - 3, 3)
                after3 = _docSlice(end_pos, 3)
                if (before2 == "**" and before3 != "***") or (after2 == "**" and after3 != "***"):
                    return False
            return True

        # Check if cursor is right before or inside an existing closing markup (stepping out)
        if not cursor.hasSelection():
            pos = cursor.position()
            # If immediately following text is markup, step past it (turning formatting OFF)
            if _docSlice(pos, mlen) == markup:
                if not (markup == "*" and _docSlice(pos, 2) == "**" and _docSlice(pos, 3) != "***"):
                    cursor.setPosition(pos + mlen)
                    self.setTextCursor(cursor)
                    if hasattr(self, "_pendingFormats"):
                        self._pendingFormats.discard(markup)
                    return
            # If immediately preceding is whitespace and following is markup (*word |*)
            if pos > 0 and _docSlice(pos - 1, 1).isspace() and _docSlice(pos, mlen) == markup:
                cursor.beginEditBlock()
                c_swap = QTextCursor(doc)
                c_swap.setPosition(pos - 1)
                c_swap.setPosition(pos + mlen, QTextCursor.KeepAnchor)
                c_swap.insertText(markup + " ")
                cursor.setPosition(c_swap.position())
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                if hasattr(self, "_pendingFormats"):
                    self._pendingFormats.discard(markup)
                return

        # 1. Check before selectWord in case cursor is right between empty pair e.g. **|**
        orig_start = cursor.selectionStart()
        orig_end = cursor.selectionEnd()
        if not cursor.hasSelection() and _isOuterMatch(orig_start, orig_end):
            cursor.beginEditBlock()
            cursor.setPosition(orig_start - mlen)
            cursor.setPosition(orig_end + mlen, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            return

        # Select word if cursor is within a word
        if not cursor.hasSelection():
            pos = cursor.position()
            prev_ch = _docSlice(pos - 1, 1)
            next_ch = _docSlice(pos, 1)
            if (prev_ch and not prev_ch.isspace() and prev_ch not in "*_~`#") or \
               (next_ch and not next_ch.isspace() and next_ch not in "*_~`#"):
                self.selectWord(cursor)

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        selected = cursor.selectedText()

        # If we have a selection:
        if cursor.hasSelection() and selected.strip():
            # Trim leading/trailing whitespace outside formatting markers
            l_strip = len(selected) - len(selected.lstrip())
            r_strip = len(selected) - len(selected.rstrip())
            inner_selected = selected.strip()
            actual_start = start + l_strip
            actual_end = end - r_strip

            # 2. If the selection itself includes the surrounding markup (e.g. "**word**")
            if (
                len(inner_selected) >= 2 * mlen
                and inner_selected.startswith(markup)
                and inner_selected.endswith(markup)
                and not (markup == "*" and inner_selected.startswith("**") and not inner_selected.startswith("***"))
            ):
                inner = inner_selected[mlen : len(inner_selected) - mlen]
                cursor.beginEditBlock()
                cursor.setPosition(actual_start)
                cursor.setPosition(actual_end, QTextCursor.KeepAnchor)
                cursor.insertText(inner)
                cursor.setPosition(actual_start)
                cursor.setPosition(actual_start + len(inner), QTextCursor.KeepAnchor)
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                return

            # 3. If the characters immediately outside [actual_start, actual_end] are `markup`
            if _isOuterMatch(actual_start, actual_end):
                cursor.beginEditBlock()
                cursor.setPosition(actual_end)
                cursor.setPosition(actual_end + mlen, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.setPosition(actual_start - mlen)
                cursor.setPosition(actual_start, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                cursor.setPosition(actual_start - mlen)
                cursor.setPosition(actual_end - mlen, QTextCursor.KeepAnchor)
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                return

            # Wrap selection with markup
            end_after = actual_end + mlen
            cursor.beginEditBlock()
            cursor.setPosition(actual_start)
            cursor.insertText(markup)
            cursor.setPosition(end_after)
            cursor.insertText(markup)
            cursor.endEditBlock()
            cursor.setPosition(actual_start + mlen)
            cursor.setPosition(end_after, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
            return

        # If no selection and not on a word: toggle pending format without inserting empty characters
        if not hasattr(self, "_pendingFormats"):
            self._pendingFormats = set()
        if markup in self._pendingFormats:
            self._pendingFormats.discard(markup)
        else:
            self._pendingFormats.add(markup)

    def convertToCleanMD(self):
        """Normalize document text: remove empty markup artefacts and fix malformed markdown spans."""
        cursor = self.textCursor()
        cursor.beginEditBlock()
        text = self.toPlainText()
        import re
        # 1. Remove empty quadruple markup like ****, ~~~~, ````
        cleaned = re.sub(r"\*{4,}|~{4,}|`{4,}", "", text)
        # 2. Fix whitespace inside bold/italics/strike: e.g. **text \t** -> **text** \t
        cleaned = re.sub(r"(\*{1,2})([^*\n]+?)([ \t]+)(\1)", r"\1\2\1\3", cleaned)
        cleaned = re.sub(r"(~~)([^~\n]+?)([ \t]+)(~~)", r"\1\2\1\3", cleaned)
        # 3. Remove stray empty ** or ~~ standalone tokens
        cleaned = re.sub(r"(?<!\S)\*{2}(?!\S)", "", cleaned)
        cleaned = re.sub(r"(?<!\S)~~(?!\S)", "", cleaned)
        if cleaned != text:
            cursor.select(QTextCursor.Document)
            cursor.insertText(cleaned)
        cursor.endEditBlock()
        if getattr(self, "highlighter", None) is not None:
            self.highlighter.rehighlight()

    def clearFormat(self):
        cursor = self.textCursor()
        text = cursor.selectedText()
        if not text:
            self.selectBlock(cursor)
            text = cursor.selectedText()
        text = self.clearedFormat(text)
        cursor.insertText(text)

    def clearedFormat(self, text):
        # FIXME: clear also block formats
        for reg, rep, flags in [
            (r"\*\*(.*?)\*\*", "\\1", None), # bold
            ("__(.*?)__", "\\1", None), # bold
            (r"\*(.*?)\*", "\\1", None), # emphasis
            ("_(.*?)_", "\\1", None), # emphasis
            ("`(.*?)`", "\\1", None), # verbatim
            ("~~(.*?)~~", "\\1", None), # strike
            (r"\^(.*?)\^", "\\1", None), # superscript
            ("~(.*?)~", "\\1", None), # subscript
            (r"<!--\s*(.*?)\s*-->", "\\1", re.S), # comments

            # LINES OR BLOCKS
            (r"^#*\s*(.+?)\s*", "\\1", re.M), # ATX
            (r"^[=-]*$", "", re.M), # Setext
            (r"^`*$", "", re.M), # Code block fenced
            (r"^\s*[-+*]\s*(.*?)\s*$", "\\1", re.M), # Bullet List
            (r"^\s*[0-9a-z](\.|\))\s*(.*?)\s*$", "\\2", re.M), # Bullet List
            (r"\s*[>\s]*(.*?)\s*$", "\\1", re.M), # Code block and blockquote

            ]:
            text = re.sub(reg, rep, text, flags if flags else 0)
        return text

    def clearedFormatForStats(self, text):
        # Remove stuff that musn't be counted
        # FIXME: clear also block formats
        for reg, rep, flags in [
            ("<!--.*-->", "", re.S), # comments
            ]:
            text = re.sub(reg, rep, text, flags if flags else 0)
        return text

    def titleSetext(self, level):
        cursor = self.textCursor()

        cursor.beginEditBlock()
        # Is it already a Setext header?
        if cursor.block().userState() in [
                MS.MarkdownStateSetextHeading1Line2,
                MS.MarkdownStateSetextHeading2Line2]:
            cursor.movePosition(QTextCursor.PreviousBlock)

        text = cursor.block().text()

        if cursor.block().userState() in [
                MS.MarkdownStateSetextHeading1Line1,
                MS.MarkdownStateSetextHeading2Line1]:
            # Need to remove line below
            c = QTextCursor(cursor.block().next())
            self.selectBlock(c)
            c.insertText("")

        char = "=" if level == 1 else "-"
        text = re.sub(r"^#*\s*(.*)\s*#*", "\\1", text)  # Removes #
        sub = char * len(text)
        text = text + "\n" + sub

        self.selectBlock(cursor)
        cursor.insertText(text)
        cursor.endEditBlock()

    def titleATX(self, level):
        cursor = self.textCursor()
        text = cursor.block().text()

        # Are we in a Setext Header?
        if cursor.block().userState() in [
                MS.MarkdownStateSetextHeading1Line1,
                MS.MarkdownStateSetextHeading2Line1]:
            # Need to remove line below
            cursor.beginEditBlock()
            c = QTextCursor(cursor.block().next())
            self.selectBlock(c)
            c.insertText("")

            self.selectBlock(cursor)
            cursor.insertText(text)
            cursor.endEditBlock()
            return

        elif cursor.block().userState() in [
                MS.MarkdownStateSetextHeading1Line2,
                MS.MarkdownStateSetextHeading2Line2]:
            cursor.movePosition(QTextCursor.PreviousBlock)
            self.setTextCursor(cursor)
            self.titleATX(level)
            return

        m = re.match(r"^(#+)(\s*)(.+)", text)
        if m:
            pre = m.group(1)
            space = m.group(2)
            txt = m.group(3)

            if len(pre) == level:
                # Remove title
                text = txt
            else:
                text = "#" * level + space + txt

        else:
            text = "#" * level + " " + text

        self.selectBlock(cursor)
        cursor.insertText(text)

    ###########################################################################
    # CLICKABLE THINKS
    ###########################################################################

    def resizeEvent(self, event):
        textEditView.resizeEvent(self, event)
        self.updateLineNumberAreaGeometry()
        self.getClickRects()

    def showEvent(self, event):
        textEditView.showEvent(self, event)
        self.updateLineNumberAreaGeometry()

    def scrollContentsBy(self, dx, dy):
        textEditView.scrollContentsBy(self, dx, dy)
        self._onLineNumbersUpdate()
        self.getClickRects()

    def getClickRects(self):
        """
        Parses the whole texte to catch clickable things: links and images.
        Stores the result so that it can be used elsewhere.
        """
        cursor = self.textCursor()
        refs = []
        text = self.toPlainText()
        for rx in [
                self.imageRegex,
                self.automaticLinkRegex,
                self.inlineLinkRegex,
            ]:
            pos = 0
            while rx.indexIn(text, pos) != -1:
                cursor.setPosition(rx.pos())
                r1 = self.cursorRect(cursor)
                pos = rx.pos() + rx.matchedLength()
                cursor.setPosition(pos)
                r2 = self.cursorRect(cursor)
                if r1.top() == r2.top():
                    ct = ClickThing(
                            QRect(r1.topLeft(), r2.bottomRight()),
                            rx,
                            rx.capturedTexts())
                    refs.append(ct)
                else:
                    r1.setRight(self.viewport().geometry().right())
                    refs.append(ClickThing(r1, rx, rx.capturedTexts()))
                    r2.setLeft(self.viewport().geometry().left())
                    refs.append(ClickThing(r2, rx, rx.capturedTexts()))
                    # We check for middle lines
                    cursor.setPosition(rx.pos())
                    cursor.movePosition(cursor.Down)
                    while self.cursorRect(cursor).top() != r2.top():
                        r3 = self.cursorRect(cursor)
                        r3.setLeft(self.viewport().geometry().left())
                        r3.setRight(self.viewport().geometry().right())
                        refs.append(ClickThing(r3, rx, rx.capturedTexts()))
                        if not cursor.movePosition(cursor.Down):
                            # Super-rare failure. Leaving log message for future investigation.
                            LOGGER.debug("Failed to move cursor down while calculating clickables. Aborting.")
                            break

        self.clickRects = refs

    def mouseMoveEvent(self, event):
        """
        When mouse moves, we show tooltip when appropriate.
        """
        self.beginTooltipMoveEvent()
        textEditView.mouseMoveEvent(self, event)
        self.endTooltipMoveEvent()

        onRect = [r for r in self.clickRects if r.rect.contains(event.pos())]

        if not onRect:
            qApp.restoreOverrideCursor()
            self.hideTooltip()
            return

        ct = onRect[0]
        if not qApp.overrideCursor():
            qApp.setOverrideCursor(Qt.PointingHandCursor)

        if ct.regex == self.automaticLinkRegex:
            tooltip = ct.texts[2] or ct.texts[4]

        elif ct.regex == self.imageRegex:
            tt = ("<p><b>" + ct.texts[1] + "</b></p>"
                  +"<p><img src='data:image/png;base64,{}'></p>")
            tooltip = None
            pos = event.pos() + QPoint(0, ct.rect.height())
            ImageTooltip.fromUrl(ct.texts[2], pos, self)

        elif ct.regex == self.inlineLinkRegex:
            tooltip = ct.texts[1] or ct.texts[2]

        if tooltip:
            tooltip = self.tr("{} (CTRL+Click to open)").format(tooltip)
            self.showTooltip(self.mapToGlobal(event.pos()), tooltip)

    def mouseReleaseEvent(self, event):
        textEditView.mouseReleaseEvent(self, event)
        onRect = [r for r in self.clickRects if r.rect.contains(event.pos())]
        if onRect and event.modifiers() & Qt.ControlModifier:
            ct = onRect[0]

            if ct.regex == self.automaticLinkRegex:
                url = ct.texts[2] or ct.texts[4]
            elif ct.regex == self.imageRegex:
                url = ct.texts[2]
            elif ct.regex == self.inlineLinkRegex:
                url = ct.texts[2]

            F.openURL(url)
            qApp.restoreOverrideCursor()

    # def paintEvent(self, event):
    #     """
    #     Only useful for debugging: shows which rects are detected for
    #     clickable things.
    #     """
    #     textEditView.paintEvent(self, event)
    #
    #     # Debug: paint rects
    #     from PyQt5.QtGui import QPainter
    #     painter = QPainter(self.viewport())
    #     painter.setPen(Qt.gray)
    #     for r in self.clickRects:
    #         painter.drawRect(r.rect)

    def doTooltip(self, pos, message):
        QToolTip.showText(self.mapToGlobal(pos), message)

class ClickThing:
    """
    A simple class to remember QRect associated with clickable stuff.
    """
    def __init__(self, rect, regex, texts):
        self.rect = rect
        self.regex = regex
        self.texts = texts

from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtCore import QIODevice, QUrl, QBuffer
from PyQt5.QtGui import QPixmap

class ImageTooltip:
    """
    This class handles the retrieving and caching of images in order to display these in tooltips.
    """

    cache = {}
    manager = QNetworkAccessManager()
    processing = {}

    supportedSchemes = ("", "file", "http", "https")

    def fromUrl(url, pos, editor):
        """
        Shows the image tooltip for the given url if available, or requests it for future use.
        """
        ImageTooltip.editor = editor

        if ImageTooltip.showTooltip(url, pos):
            return # the url already exists in the cache

        try:
            ImageTooltip.manager.finished.connect(ImageTooltip.finished, F.AUC)
        except:
            pass # already connected

        qurl = QUrl.fromUserInput(url)
        if (qurl == QUrl()):
            ImageTooltip.cache[url] = (False, ImageTooltip.manager.tr("The image path or URL is incomplete or malformed."))
            ImageTooltip.showTooltip(url, pos)
            return # empty QUrl means it failed completely
        elif (qurl.scheme() not in ImageTooltip.supportedSchemes):
            # QUrl.fromUserInput() can occasionally deduce an incorrect scheme,
            # which produces an error message regarding an unknown scheme. (Yay!)
            # But it also breaks all possible methods to try and associate the
            # reply with the original request in finished(), since reply.request()
            # is completely and utterly butchered for all tracking needs. :'(
            # (The QNetworkRequest, .url() and .originatingObject() can all change.)

            # Test case (Linux): ![image](C:\test_root.jpg)
            ImageTooltip.cache[url] = (False, ImageTooltip.manager.tr("The protocol \"{}\" is not supported.").format(qurl.scheme()))
            ImageTooltip.showTooltip(url, pos)
            return # no more request/reply chaos, please!
        elif (qurl in ImageTooltip.processing):
            return # one download is more than enough

        # Request the image for later processing.
        request = QNetworkRequest(qurl)
        ImageTooltip.processing[qurl] = (pos, url)
        reply = ImageTooltip.manager.get(request)

        # On Linux the finished() signal is not triggered when the url resembles
        # 'file://X:/...'. But because it completes instantly, we can manually
        # trigger the code to keep our processing dictionary neat & clean.
        if reply.error() == 302:  # QNetworkReply.ProtocolInvalidOperationError
            ImageTooltip.finished(reply)

    def finished(reply):
        """
        After retrieving an image, we add it to the cache.
        """
        cache = ImageTooltip.cache
        url_key = reply.request().url()
        pos, url = None, None

        if url_key in ImageTooltip.processing:
            # Obtain the information associated with this request.
            pos, url = ImageTooltip.processing[url_key]
            del ImageTooltip.processing[url_key]
        elif len(ImageTooltip.processing) == 0:
            # We are not processing anything. Maybe it is a spurious signal,
            # or maybe the 'reply.error() == 302' workaround in fromUrl() has
            # been fixed in Qt. Whatever the reason, we can assume this request
            # has already been handled, and needs no more work from us.
            return
        else:
            # Somehow we lost track. Log what we can to hopefully figure it out.
            LOGGER.warning("Unable to match fetched data for tooltip to original request.")
            LOGGER.warning("- Completed request: %s", url_key)
            LOGGER.warning("- Status upon finishing: %s, %s", reply.error(), reply.errorString())
            LOGGER.warning("- Currently processing: %s", ImageTooltip.processing)
            return

        # Update cache with retrieved data.
        if reply.error() != QNetworkReply.NoError:
            cache[url] = (False, reply.errorString())
        else:
            px = QPixmap()
            px.loadFromData(reply.readAll())
            px = px.scaled(800, 600, Qt.KeepAspectRatio)
            cache[url] = (True, px)

        ImageTooltip.showTooltip(url, pos)

    def showTooltip(url, pos):
        """
        Show a tooltip for the given url based on cached information.
        """
        cache = ImageTooltip.cache

        if url in cache:
            if not cache[url][0]:  # error, image was not found
                ImageTooltip.tooltipError(cache[url][1], pos)
            else:
                ImageTooltip.tooltip(cache[url][1], pos)
            return True
        return False

    def tooltipError(message, pos):
        """
        Display a tooltip with an error message at the given position.
        """
        ImageTooltip.editor.doTooltip(pos, message)

    def tooltip(image, pos):
        """
        Display a tooltip with an image at the given position.
        """
        px = image
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        px.save(buffer, "PNG", quality=100)
        image = bytes(buffer.data().toBase64()).decode()
        tt = "<p><img src='data:image/png;base64,{}'></p>".format(image)
        ImageTooltip.editor.doTooltip(pos, tt)
