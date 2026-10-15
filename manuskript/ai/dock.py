# --!-- coding: utf8 --!--
"""The AI assistant dock (chat panel)."""

import html
import time

from PyQt5.QtCore import Qt, QEvent, QTimer, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QLabel,
                             QPushButton, QTextBrowser, QTextEdit,
                             QVBoxLayout, QWidget)

from manuskript.ai import providers as P
from manuskript.ai.chats import ChatStore
from manuskript.ai.config import AISettings, ROLES
from manuskript.ai.context import assemble, gather, SOURCES
from manuskript.ai.workers import ChatWorker, ModelsWorker
from manuskript.functions import writablePath
from manuskript.ui.modernIcons import icon as modernIcon, pixmap as modernPixmap

RESERVE_TOKENS = 1024   # kept free for the reply (local server only)


class _SendEdit(QTextEdit):
    """Enter sends, Shift+Enter inserts a newline."""
    submit = pyqtSignal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                not (e.modifiers() & Qt.ShiftModifier):
            self.submit.emit()
            return
        QTextEdit.keyPressEvent(self, e)


def _wideCombo():
    """Combo whose popup is as wide as its longest item, whatever the
    dock width is."""
    c = QComboBox()
    c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(8)
    return c


def _fitPopup(combo):
    fm = combo.fontMetrics()
    w = max([fm.horizontalAdvance(combo.itemText(i)) for i in range(combo.count())] + [60])
    combo.view().setMinimumWidth(w + 40)


class AIDock(QDockWidget):

    def __init__(self, parent):
        QDockWidget.__init__(self, parent)
        self.setObjectName("dckAI")
        self.setWindowTitle(self.tr("AI Assistant"))
        self.mw = parent
        self.store = ChatStore(writablePath("ai_chats"))
        self.chat = self._blankChat()
        self.worker = None
        self.modelsWorker = None
        self._streamText = ""
        self._streamAgent = ""
        self._pending = None          # (prompt) while a reply is streaming
        self._t0 = self._tFirst = 0.0
        self._inTok = self._outTok = 0
        self._loading = False
        self._buildUi()
        self._loadSettings()
        self.refreshChatList()

    # ------------------------------------------------------------ UI
    def _buildUi(self):
        # Hide the native QDockWidget titlebar so there is no redundant 'X' close button
        # or tiny native float target; we provide a clean icon-driven header inside.
        self.setTitleBarWidget(QWidget(self))

        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)

        # Row 1: Chat selector + Icon buttons (New, Delete, Dock/Undock)
        row = QHBoxLayout()
        row.setSpacing(4)
        lbl_chat_icon = QLabel()
        lbl_chat_icon.setPixmap(modernPixmap("sparkles", 16, accent=True))
        lbl_chat_icon.setToolTip(self.tr("Recent Chats"))
        row.addWidget(lbl_chat_icon)

        self.cmbChats = _wideCombo()
        self.cmbChats.setToolTip(self.tr("Select chat conversation"))

        self.btnNew = QPushButton()
        self.btnNew.setIcon(modernIcon("plus", 16))
        self.btnNew.setFixedSize(30, 30)
        self.btnNew.setToolTip(self.tr("New chat"))

        self.btnDel = QPushButton()
        self.btnDel.setIcon(modernIcon("trash", 16))
        self.btnDel.setFixedSize(30, 30)
        self.btnDel.setToolTip(self.tr("Delete current chat"))

        self.btnDock = QPushButton()
        self.btnDock.setFixedSize(30, 30)
        self.btnDock.setToolTip(self.tr("Dock or undock the AI Assistant panel"))

        row.addWidget(self.cmbChats, 1)
        row.addWidget(self.btnNew)
        row.addWidget(self.btnDel)
        row.addWidget(self.btnDock)
        v.addLayout(row)

        # Row 2: Provider & Role with icons instead of text labels
        row = QHBoxLayout()
        row.setSpacing(4)
        lbl_prov = QLabel()
        lbl_prov.setPixmap(modernPixmap("server", 15))
        lbl_prov.setToolTip(self.tr("AI Provider"))
        self.cmbProvider = _wideCombo()
        self.cmbProvider.addItems(P.PROVIDERS)
        self.cmbProvider.setToolTip(self.tr("AI Provider"))

        lbl_role = QLabel()
        lbl_role.setPixmap(modernPixmap("user-check", 15))
        lbl_role.setToolTip(self.tr("AI Role Persona"))
        self.cmbRole = _wideCombo()
        self.cmbRole.addItems(ROLES)
        self.cmbRole.setToolTip(self.tr("AI Role Persona"))

        row.addWidget(lbl_prov)
        row.addWidget(self.cmbProvider, 1)
        row.addWidget(lbl_role)
        row.addWidget(self.cmbRole, 1)
        v.addLayout(row)

        # Row 3: Model selector + Refresh icon button
        row = QHBoxLayout()
        row.setSpacing(4)
        lbl_model = QLabel()
        lbl_model.setPixmap(modernPixmap("cpu", 15))
        lbl_model.setToolTip(self.tr("Model"))
        self.cmbModel = _wideCombo()
        self.cmbModel.setEditable(True)
        self.cmbModel.setToolTip(self.tr("Active LLM Model"))
        self.btnRefresh = QPushButton()
        self.btnRefresh.setIcon(modernIcon("refresh", 15))
        self.btnRefresh.setFixedSize(30, 30)
        self.btnRefresh.setToolTip(self.tr("Refresh model list"))
        row.addWidget(lbl_model)
        row.addWidget(self.cmbModel, 1)
        row.addWidget(self.btnRefresh)
        v.addLayout(row)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        v.addWidget(self.view, 1)

        # Status line sits directly under the chat view.
        row = QHBoxLayout()
        self.lblStatus = QLabel("")
        self.lblStatus.setWordWrap(True)
        self.btnCancel = QPushButton()
        self.btnCancel.setIcon(modernIcon("stop", 14))
        self.btnCancel.setText(self.tr("Stop"))
        self.btnCancel.setToolTip(self.tr("Cancel generation"))
        self.btnCancel.setVisible(False)
        row.addWidget(self.lblStatus, 1)
        row.addWidget(self.btnCancel)
        v.addLayout(row)

        # Input row with Send icon button
        inp_row = QHBoxLayout()
        inp_row.setSpacing(4)
        self.txtInput = _SendEdit()
        self.txtInput.setFixedHeight(74)
        self.txtInput.setPlaceholderText(
            self.tr("Ask the AI... (Enter to send, Shift+Enter for a new line)"))
        self.btnSend = QPushButton()
        self.btnSend.setIcon(modernIcon("send", 16, accent=True))
        self.btnSend.setFixedSize(34, 74)
        self.btnSend.setToolTip(self.tr("Send message (Enter)"))
        inp_row.addWidget(self.txtInput, 1)
        inp_row.addWidget(self.btnSend)
        v.addLayout(inp_row)
        self.setWidget(w)

        self.btnNew.clicked.connect(self.newChat)
        self.btnDel.clicked.connect(self.deleteChat)
        self.btnDock.clicked.connect(self.toggleFloating)
        self.topLevelChanged.connect(self._updateDockButton)
        self.btnCancel.clicked.connect(self.cancel)
        self.btnRefresh.clicked.connect(self.refreshModels)
        self.btnSend.clicked.connect(self.send)
        self.txtInput.submit.connect(self.send)
        self.cmbChats.activated.connect(self._chatPicked)
        self.cmbProvider.activated.connect(self._providerPicked)
        self.cmbRole.activated.connect(self._rolePicked)
        self.cmbModel.activated.connect(self._modelPicked)
        self.cmbModel.lineEdit().editingFinished.connect(self._modelPicked)
        self._updateDockButton(self.isFloating())

    def toggleFloating(self):
        """Toggle between docked and floating state, re-attaching to the right dock area when docked."""
        want_floating = not self.isFloating()
        self.setFloating(want_floating)
        if not want_floating and self.mw is not None:
            self.mw.addDockWidget(Qt.RightDockWidgetArea, self)
            self.show()
        self._updateDockButton(self.isFloating())

    def _updateDockButton(self, is_floating=False):
        if is_floating:
            self.btnDock.setIcon(modernIcon("dock", 16, accent=True))
            self.btnDock.setProperty("dockState", "dock")
            self.btnDock.setToolTip(self.tr("Re-dock AI Assistant into main window"))
        else:
            self.btnDock.setIcon(modernIcon("undock", 16))
            self.btnDock.setProperty("dockState", "undock")
            self.btnDock.setToolTip(self.tr("Detach AI Assistant into a floating window"))

    # ------------------------------------------------------ settings sync
    @staticmethod
    def _blankChat():
        return {"id": None, "title": "", "project": "", "messages": []}

    def _project(self):
        return getattr(self.mw, "currentProject", None) or ""

    def _loadSettings(self):
        """Make the widgets show what Preferences/QSettings currently hold."""
        prov = AISettings.provider()
        self.cmbProvider.setCurrentText(prov)
        self.cmbRole.setCurrentText(AISettings.role())
        self._fillModels(AISettings.cachedModels(prov), AISettings.model(prov))

    def syncFromSettings(self):
        if self.worker is None:
            self._loadSettings()

    def showEvent(self, e):
        QDockWidget.showEvent(self, e)
        self.syncFromSettings()

    def _fillModels(self, names, current):
        self.cmbModel.blockSignals(True)
        self.cmbModel.clear()
        items = list(names)
        if current and current not in items:
            items.insert(0, current)
        self.cmbModel.addItems(items)
        self.cmbModel.setCurrentText(current or "")
        _fitPopup(self.cmbModel)
        self.cmbModel.blockSignals(False)

    def _providerPicked(self, _i=None):
        prov = self.cmbProvider.currentText()
        AISettings.setProvider(prov)
        self._fillModels(AISettings.cachedModels(prov), AISettings.model(prov))
        self.refreshModels()

    def _rolePicked(self, _i=None):
        AISettings.setRole(self.cmbRole.currentText())

    def _modelPicked(self, _i=None):
        AISettings.setModel(self.cmbProvider.currentText(),
                            self.cmbModel.currentText())

    def refreshModels(self):
        prov = self.cmbProvider.currentText()
        if self.modelsWorker is not None and self.modelsWorker.isRunning():
            return
        self.lblStatus.setText(self.tr("Fetching models..."))
        self.modelsWorker = ModelsWorker(
            prov, AISettings.endpoint(), AISettings.apiKey(prov), self)
        self.modelsWorker.done.connect(self._modelsDone)
        self.modelsWorker.failed.connect(self._modelsFailed)
        self.modelsWorker.start()

    def _modelsDone(self, prov, names):
        if prov != self.cmbProvider.currentText():
            return   # user switched provider meanwhile
        AISettings.setCachedModels(prov, names)
        self._fillModels(names, self.cmbModel.currentText())
        self.lblStatus.setText(self.tr("%d models found") % len(names))

    def _modelsFailed(self, prov, msg):
        if prov == self.cmbProvider.currentText():
            self.lblStatus.setText(self.tr("Model list failed: ") + msg)

    # ------------------------------------------------------------ chats
    def refreshChatList(self):
        chats = self.store.list(self._project())
        self.cmbChats.clear()
        if self.chat["id"] is None:
            self.cmbChats.addItem(self.tr("-- new chat --"), None)
        for c in chats:
            self.cmbChats.addItem(c.get("title", c["id"]), c["id"])
        for i in range(self.cmbChats.count()):
            if self.cmbChats.itemData(i) == self.chat["id"]:
                self.cmbChats.setCurrentIndex(i)
        _fitPopup(self.cmbChats)

    def newChat(self):
        if self.worker is not None:
            self.cancel()
            self.worker.wait(3000)
        self.chat = self._blankChat()
        self.view.clear()
        self.lblStatus.setText("")
        self.refreshChatList()

    def _chatPicked(self, i):
        cid = self.cmbChats.itemData(i)
        if cid is None or cid == self.chat["id"] or self.worker is not None:
            return
        chat = self.store.load(cid)
        if chat:
            self.chat = chat
            self.renderAll()

    def deleteChat(self):
        if self.chat["id"]:
            self.store.delete(self.chat["id"])
        self.newChat()

    def renderAll(self):
        self.view.clear()
        for m in self.chat["messages"]:
            self._appendHeader(m.get("agent", "AI") if m["role"] == "assistant" else None)
            self.view.insertPlainText(m["content"])
        self.view.moveCursor(QTextCursor.End)

    @staticmethod
    def _labelColour(isUser):
        """Accent for the user, success colour for the AI (scheme-aware)."""
        try:
            from manuskript.appearance.config import Appearance
            s, d = Appearance.colours()
            if s is not None:
                return d["accent"] if isUser else s.success
        except Exception:
            pass
        return "#4a90d9" if isUser else "#2e9e5b"

    def _appendHeader(self, agent):
        """Start a new message block. agent=None means the user."""
        self.view.moveCursor(QTextCursor.End)
        label = self.tr("You") if agent is None else self.tr("%s says") % agent
        color = self._labelColour(agent is None)
        if not self.view.document().isEmpty():
            self.view.insertHtml("<br><br>")
        self.view.insertHtml('<b style="color:%s">%s:</b>&nbsp;' % (color, html.escape(label)))

    # ------------------------------------------------------------ sending
    def _systemPrompt(self, prov, role):
        base = AISettings.prompt(role)
        flags = {k: AISettings.ctxFlag(k) for k, _l, _p in SOURCES}
        if prov == P.LOCAL:
            budget = AISettings.contextSize() - RESERVE_TOKENS - P.estimateTokens(base)
            budget -= sum(P.estimateTokens(m["content"]) for m in self.chat["messages"])
            budget = max(budget, 256)
        else:
            budget = 100000   # cloud models: generous fixed cap, provider limits apply
        try:
            ctx = assemble(gather(self.mw, flags), budget)
        except Exception as e:   # never block chatting on a context problem
            ctx = ""
            self.lblStatus.setText(self.tr("Context unavailable: ") + str(e))
        if ctx:
            return base + "\n\nThe author is working on this project. Use the " \
                "following material as context:\n\n" + ctx
        return base

    def send(self):
        prompt = self.txtInput.toPlainText().strip()
        if not prompt or self.worker is not None:
            return
        prov = self.cmbProvider.currentText()
        model = self.cmbModel.currentText().strip()
        role = self.cmbRole.currentText()
        key = AISettings.apiKey(prov)
        if not model:
            self.lblStatus.setText(self.tr("Choose a model first (use the refresh button)."))
            return
        if prov != P.LOCAL and not key:
            self.lblStatus.setText(self.tr("No API key set for %s (Settings > AI).") % prov)
            return
        self._modelPicked()
        AISettings.setRole(role)

        history = [{"role": m["role"], "content": m["content"]}
                   for m in self.chat["messages"]]
        history.append({"role": "user", "content": prompt})
        req = {
            "provider": prov, "endpoint": AISettings.endpoint(), "apiKey": key,
            "model": model, "system": self._systemPrompt(prov, role),
            "history": history,
            "temperature": AISettings.temperature() if prov == P.LOCAL else None,
            "thinking": AISettings.thinking() if prov == P.LOCAL else "Off",
        }
        self._pending = prompt
        self._streamAgent = role
        self._streamText = ""
        self._inTok = self._outTok = 0
        self._t0 = time.time()
        self._tFirst = 0.0
        self.txtInput.clear()
        self._appendHeader(None)
        self.view.insertPlainText(prompt)
        self._appendHeader(role)

        self.worker = ChatWorker(req, self)
        self.worker.chunk.connect(self._onChunk)
        self.worker.thinking.connect(self._onThinking)
        self.worker.usage.connect(self._onUsage)
        self.worker.failed.connect(self._onFailed)
        self.worker.completed.connect(self._onCompleted)
        self.worker.finished.connect(self._onFinished)
        self.btnCancel.setVisible(True)
        self.cmbProvider.setEnabled(False)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._updateStatus)
        self._tick.start(500)
        self._updateStatus()
        self.worker.start()

    def _updateStatus(self):
        if self.worker is None:
            return
        el = time.time() - self._t0
        if not self._streamText:
            self.lblStatus.setText(self.tr("Thinking... %ds") % int(el))
            return
        out = self._outTok or P.estimateTokens(self._streamText)
        span = max(time.time() - self._tFirst, 0.001)
        self.lblStatus.setText(self.tr("Generating...  In: %d | Out: %d | %.1f t/s")
                               % (self._inTok, out, out / span))

    def _onChunk(self, text):
        if not self._tFirst:
            self._tFirst = time.time()
        self._streamText += text
        self.view.moveCursor(QTextCursor.End)
        self.view.insertPlainText(text)
        self.view.moveCursor(QTextCursor.End)

    def _onThinking(self):
        pass   # status line already shows "Thinking... Ns"

    def _onUsage(self, inTok, outTok):
        self._inTok, self._outTok = inTok, outTok

    def _onFailed(self, msg):
        # Roll back: the failed prompt must not poison later requests.
        self._failed = msg
        self.view.moveCursor(QTextCursor.End)
        self.view.insertHtml('<br><span style="color:#d9534f">%s</span>'
                             % html.escape(self.tr("Error: ") + msg))
        if self._pending:
            self.txtInput.setPlainText(self._pending)
            self._pending = None
        self._streamText = ""

    def _onCompleted(self, cancelled):
        if cancelled:
            self.view.insertHtml('<br><i>%s</i>' % html.escape(self.tr("[Generation cancelled]")))
        if self._pending is not None and (self._streamText or not cancelled):
            self.chat["messages"].append({"role": "user", "content": self._pending})
            self.chat["messages"].append({"role": "assistant", "agent": self._streamAgent,
                                          "content": self._streamText})
            if not self.chat["id"]:
                self.chat["id"] = self.store.newId()
                self.chat["title"] = self.store.makeTitle(self._streamAgent, self._pending)
                self.chat["project"] = self._project()
            self.store.save(self.chat)
        elif self._pending and cancelled:
            self.txtInput.setPlainText(self._pending)
        self._pending = None

    def _onFinished(self):
        self._tick.stop()
        self.worker.deleteLater()
        self.worker = None
        self.btnCancel.setVisible(False)
        self.cmbProvider.setEnabled(True)
        if self._streamText:
            out = self._outTok or P.estimateTokens(self._streamText)
            span = max(time.time() - (self._tFirst or self._t0), 0.001)
            self.lblStatus.setText(self.tr("Done.  In: %d | Out: %d | %.1f t/s")
                                   % (self._inTok, out, out / span))
        self.refreshChatList()

    def cancel(self):
        if self.worker is not None:
            self.worker.cancel()

    def shutdown(self):
        """Called from MainWindow.closeEvent."""
        for w in (self.worker, self.modelsWorker):
            if w is not None and w.isRunning():
                if hasattr(w, "cancel"):
                    w.cancel()
                w.wait(3000)
