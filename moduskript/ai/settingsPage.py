# --!-- coding: utf8 --!--
"""AI page for Manuskript's settings window. Every control saves at once."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
                             QGroupBox, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
                             QWidget)

from moduskript.ai import providers as P
from moduskript.ai.config import AISettings, ROLES
from moduskript.ai.context import SOURCES
from moduskript.ai.workers import ModelsWorker


class AISettingsPage(QScrollArea):

    def __init__(self, parent=None):
        QScrollArea.__init__(self, parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self._worker = None
        self._activeWorkers = set()
        self._autoFetched = False
        self._loading = True
        body = QWidget()
        self.setWidget(body)
        lay = QVBoxLayout(body)

        box = QGroupBox(self.tr("Provider"))
        form = QFormLayout(box)
        self.cmbProvider = QComboBox()
        self.cmbProvider.addItems(P.PROVIDERS)
        self.txtEndpoint = QLineEdit()
        self.txtEndpoint.setPlaceholderText("http://127.0.0.1:8080")
        self.txtKey = QLineEdit()
        self.txtKey.setEchoMode(QLineEdit.Password)
        self.cmbModel = QComboBox()
        self.btnRefresh = QPushButton(self.tr("Refresh models"))
        self.lblInfo = QLabel("")
        self.lblInfo.setWordWrap(True)
        form.addRow(self.tr("API provider"), self.cmbProvider)
        self.lblEndpoint = QLabel(self.tr("Server URL"))
        form.addRow(self.lblEndpoint, self.txtEndpoint)
        self.lblKey = QLabel(self.tr("API key"))
        form.addRow(self.lblKey, self.txtKey)
        form.addRow(self.tr("Model"), self.cmbModel)
        form.addRow("", self.btnRefresh)
        form.addRow("", self.lblInfo)
        lay.addWidget(box)

        self.boxLocal = QGroupBox(self.tr("Local model options (llama.cpp only)"))
        form = QFormLayout(self.boxLocal)
        self.spnCtx = QSpinBox()
        self.spnCtx.setRange(512, 1048576)
        self.spnCtx.setSingleStep(1024)
        self.spnTemp = QDoubleSpinBox()
        self.spnTemp.setRange(0.0, 2.0)
        self.spnTemp.setSingleStep(0.05)
        self.cmbThink = QComboBox()
        self.cmbThink.addItems(P.THINKING_LEVELS)
        form.addRow(self.tr("Context window (tokens)"), self.spnCtx)
        form.addRow(self.tr("Temperature"), self.spnTemp)
        form.addRow(self.tr("Thinking"), self.cmbThink)
        lay.addWidget(self.boxLocal)

        box = QGroupBox(self.tr("Context sent with each prompt"))
        v = QVBoxLayout(box)
        self.chkCtx = {}
        for key, label, _p in SOURCES:
            c = QCheckBox(label)
            self.chkCtx[key] = c
            v.addWidget(c)
        lay.addWidget(box)

        box = QGroupBox(self.tr("Role prompts"))
        form = QFormLayout(box)
        self.txtPrompt = {}
        for role in ROLES:
            t = QPlainTextEdit()
            t.setFixedHeight(90)
            self.txtPrompt[role] = t
            form.addRow(role, t)
        self.btnReset = QPushButton(self.tr("Reset role prompts to defaults"))
        form.addRow("", self.btnReset)
        lay.addWidget(box)
        lay.addStretch(1)

        self._load()
        self._connect()

    # ------------------------------------------------------------ load/save
    def _load(self):
        self._loading = True
        prov = AISettings.provider()
        self.cmbProvider.setCurrentText(prov)
        self.txtEndpoint.setText(AISettings.endpoint())
        self.spnCtx.setValue(AISettings.contextSize())
        self.spnTemp.setValue(AISettings.temperature())
        self.cmbThink.setCurrentText(AISettings.thinking())
        for k, c in self.chkCtx.items():
            c.setChecked(AISettings.ctxFlag(k))
        for role, t in self.txtPrompt.items():
            t.setPlainText(AISettings.prompt(role))
        self._loadProviderFields(prov)
        self._loading = False

    def _loadProviderFields(self, prov):
        """Key and model are remembered per provider."""
        self.cmbProvider.blockSignals(True)
        self.cmbProvider.setCurrentText(prov)
        self.cmbProvider.blockSignals(False)
        self.txtKey.setText(AISettings.apiKey(prov))
        self._fillModels(AISettings.cachedModels(prov), AISettings.model(prov))
        local = prov == P.LOCAL
        for w in (self.lblEndpoint, self.txtEndpoint, self.boxLocal):
            w.setVisible(local)
        self.txtKey.setPlaceholderText(
            self.tr("Optional (only if your server needs one)") if local else "")
        self.lblInfo.setText("" if local else self.tr(
            "Cloud providers use their official fixed endpoint. Context size, "
            "temperature and thinking are managed by the provider."))

    def _fillModels(self, names, current):
        """Fill the drop-down with the fetched models (current one kept first)."""
        items = list(names)
        if current and current not in items:
            items.insert(0, current)
        self.cmbModel.blockSignals(True)
        self.cmbModel.clear()
        self.cmbModel.addItems(items)
        self.cmbModel.setCurrentText(current or "")
        self.cmbModel.view().setMinimumWidth(
            max([self.cmbModel.fontMetrics().horizontalAdvance(i) for i in items] + [0]) + 40)
        self.cmbModel.blockSignals(False)

    def showEvent(self, e):
        QScrollArea.showEvent(self, e)
        # Query the server each time the page opens, so the list is current.
        if not self._loading and not self._autoFetched:
            self._autoFetched = True
            self._refresh()

    def hideEvent(self, e):
        QScrollArea.hideEvent(self, e)
        self._autoFetched = False

    def _connect(self):
        self.cmbProvider.activated.connect(self._providerChanged)
        self.txtEndpoint.editingFinished.connect(
            lambda: AISettings.setEndpoint(self.txtEndpoint.text()))
        self.txtKey.editingFinished.connect(self._keyChanged)
        self.cmbModel.activated.connect(self._modelChanged)
        self.btnRefresh.clicked.connect(self._refresh)
        self.spnCtx.valueChanged.connect(lambda v: AISettings.setContextSize(v))
        self.spnTemp.valueChanged.connect(lambda v: AISettings.setTemperature(v))
        self.cmbThink.activated.connect(
            lambda _i: AISettings.setThinking(self.cmbThink.currentText()))
        for k, c in self.chkCtx.items():
            c.toggled.connect(lambda v, k=k: AISettings.setCtxFlag(k, v))
        for role, t in self.txtPrompt.items():
            t.textChanged.connect(lambda r=role, t=t: AISettings.setPrompt(r, t.toPlainText()))
        self.btnReset.clicked.connect(self._resetPrompts)

    def _providerChanged(self, _i=None):
        # Save what is on screen for the old provider first.
        old = AISettings.provider()
        AISettings.setApiKey(old, self.txtKey.text())
        AISettings.setModel(old, self.cmbModel.currentText())
        prov = self.cmbProvider.currentText()
        AISettings.setProvider(prov)
        self._loadProviderFields(prov)
        self._refresh()

    def _keyChanged(self):
        AISettings.setApiKey(self.cmbProvider.currentText(), self.txtKey.text())

    def _modelChanged(self, _i=None):
        AISettings.setModel(self.cmbProvider.currentText(), self.cmbModel.currentText())

    def _resetPrompts(self):
        from moduskript.ai.config import DEFAULT_PROMPTS
        for role, t in self.txtPrompt.items():
            t.setPlainText(DEFAULT_PROMPTS[role])

    def _isWorkerRunning(self, w):
        if w is None:
            return False
        try:
            return bool(w.isRunning())
        except RuntimeError:
            return False

    def _retireWorker(self, w):
        if self._worker is w:
            self._worker = None
        try:
            self.btnRefresh.setEnabled(True)
        except RuntimeError:
            pass
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(200, lambda worker=w: self._cleanupWorker(worker))

    def _cleanupWorker(self, w):
        if self._isWorkerRunning(w):
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(200, lambda worker=w: self._cleanupWorker(worker))
            return
        self._activeWorkers.discard(w)
        try:
            w.deleteLater()
        except RuntimeError:
            pass

    def _refresh(self):
        prov = self.cmbProvider.currentText()
        self._keyChanged()
        AISettings.setEndpoint(self.txtEndpoint.text())
        if self._isWorkerRunning(self._worker):
            try:
                self._worker.done.disconnect()
                self._worker.failed.disconnect()
            except Exception:
                pass
        if prov != P.LOCAL and not AISettings.apiKey(prov):
            self.lblInfo.setText(self.tr("Enter your API key, then click Refresh models."))
            return
        self.btnRefresh.setEnabled(False)
        self.lblInfo.setText(self.tr("Fetching models..."))
        w = ModelsWorker(prov, AISettings.endpoint(), AISettings.apiKey(prov), None)
        self._activeWorkers.add(w)
        self._worker = w
        w.done.connect(self._refreshDone)
        w.failed.connect(self._refreshFailed)
        w.finished.connect(lambda worker=w: self._retireWorker(worker))
        w.start()

    def _refreshDone(self, prov, names):
        if prov != self.cmbProvider.currentText():
            return
        AISettings.setCachedModels(prov, names)
        self._fillModels(names, self.cmbModel.currentText())
        self.lblInfo.setText(self.tr("%d models found.") % len(names))

    def _refreshFailed(self, prov, msg):
        self.lblInfo.setText(self.tr("Could not fetch models: ") + msg)
