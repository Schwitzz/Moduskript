# --!-- coding: utf8 --!--
"""Appearance page for Manuskript's settings window."""

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFormLayout,
                             QGroupBox, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
                             QWidget)

from manuskript.appearance import schemes
from manuskript.appearance.config import (Appearance, DENSITIES, FONTS)

PREVIEW = QSize(150, 92)


def schemePreview(s, accent=None):
    """A tiny mock window drawn in the scheme's colours."""
    d = schemes.derived(s, accent)
    pm = QPixmap(PREVIEW)
    pm.fill(QColor(s.window))
    p = QPainter(pm)
    w, h = PREVIEW.width(), PREVIEW.height()
    p.fillRect(0, 0, 34, h, QColor(s.panel))                 # sidebar
    for i in range(4):
        p.fillRect(7, 12 + i * 15, 20, 6, QColor(s.muted if i else d["accent"]))
    p.fillRect(40, 8, w - 48, h - 16, QColor(s.editor))      # editor
    for i, wd in enumerate((70, 84, 60, 76)):
        p.fillRect(48, 18 + i * 10, wd, 4, QColor(s.text))
    p.fillRect(48, h - 24, 40, 6, QColor(d["accent"]))
    for i, col in enumerate((s.success, s.warning, s.error)):
        p.fillRect(w - 44 + i * 10, h - 24, 7, 6, QColor(col))
    p.end()
    return pm


class AppearanceSettingsPage(QScrollArea):

    def __init__(self, mainWindow=None, parent=None):
        QScrollArea.__init__(self, parent)
        self.mw = mainWindow
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        self.setWidget(body)
        lay = QVBoxLayout(body)

        box = QGroupBox(self.tr("Colour scheme"))
        v = QVBoxLayout(box)
        self.lst = QListWidget()
        self.lst.setViewMode(QListWidget.IconMode)
        self.lst.setIconSize(PREVIEW)
        self.lst.setResizeMode(QListWidget.Adjust)
        self.lst.setMovement(QListWidget.Static)
        self.lst.setWordWrap(True)
        self.lst.setSpacing(8)
        self.lst.setMinimumHeight(300)
        self.lst.setGridSize(QSize(PREVIEW.width() + 22, PREVIEW.height() + 44))
        v.addWidget(self.lst)
        self.lblNote = QLabel(self.tr("Select any colour scheme above to apply it live."))
        self.lblNote.setWordWrap(True)
        v.addWidget(self.lblNote)
        self.btnRestart = QPushButton(self.tr("Restart application (optional)"))
        self.btnRestart.setEnabled(False)
        v.addWidget(self.btnRestart)
        lay.addWidget(box)

        box = QGroupBox(self.tr("Look and feel"))
        f = QFormLayout(box)
        self.btnAccent = QPushButton()
        self.btnAccentReset = QPushButton(self.tr("Use scheme accent"))
        self.cmbFont = QComboBox()
        self.cmbFont.addItems(FONTS)
        self.spnSize = QSpinBox()
        self.spnSize.setRange(0, 24)
        self.spnSize.setSpecialValueText(self.tr("Default"))
        self.spnSize.setSuffix(" pt")
        self.cmbDensity = QComboBox()
        self.cmbDensity.addItems(DENSITIES)
        f.addRow(self.tr("Accent colour"), self.btnAccent)
        f.addRow("", self.btnAccentReset)
        f.addRow(self.tr("Interface font"), self.cmbFont)
        f.addRow(self.tr("Font size"), self.spnSize)
        f.addRow(self.tr("Density"), self.cmbDensity)
        lay.addWidget(box)

        box = QGroupBox(self.tr("Views"))
        v = QVBoxLayout(box)
        self.chkViews = QCheckBox(self.tr(
            "Editor, corkboard and cards follow the colour scheme"))
        self.chkIcons = QCheckBox(self.tr("Recolour faint grey icons on dark schemes"))
        v.addWidget(self.chkViews)
        v.addWidget(self.chkIcons)
        lay.addWidget(box)
        lay.addStretch(1)

        self._startScheme = Appearance.scheme()
        self._fill()
        self._connect()

    # ------------------------------------------------------------ fill
    def _fill(self):
        self._loading = True
        cur = Appearance.scheme()
        acc = Appearance.accent() or None
        sysItem = QListWidgetItem(self.tr("System (unchanged)"))
        sysItem.setData(Qt.UserRole, schemes.SYSTEM)
        sysItem.setIcon(QIcon(self._systemPreview()))
        self.lst.addItem(sysItem)
        for s in schemes.SCHEMES.values():
            it = QListWidgetItem(s.name)
            it.setData(Qt.UserRole, s.id)
            it.setIcon(QIcon(schemePreview(s, acc)))
            self.lst.addItem(it)
        for i in range(self.lst.count()):
            if self.lst.item(i).data(Qt.UserRole) == cur:
                self.lst.setCurrentRow(i)
        self._showAccent()
        self.cmbFont.setCurrentText(Appearance.font())
        self.spnSize.setValue(Appearance.fontSize())
        self.cmbDensity.setCurrentText(Appearance.density())
        self.chkViews.setChecked(Appearance.viewsFollowTheme())
        self.chkIcons.setChecked(Appearance.recolourIcons())
        self._loading = False

    def _systemPreview(self):
        pm = QPixmap(PREVIEW)
        pm.fill(self.palette().color(self.backgroundRole()))
        p = QPainter(pm)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(pm.rect(), Qt.AlignCenter, self.tr("Your system\nlook"))
        p.end()
        return pm

    def _showAccent(self):
        s = Appearance.active()
        col = Appearance.accent() or (s.accent if s else "#888888")
        self.btnAccent.setText(col)
        self.btnAccent.setStyleSheet("background:%s; color:%s;" % (
            col, "#000000" if QColor(col).lightness() > 128 else "#ffffff"))
        self.btnAccentReset.setEnabled(bool(Appearance.accent()))

    # ------------------------------------------------------------ signals
    def _connect(self):
        self.lst.currentItemChanged.connect(self._schemeChanged)
        self.btnAccent.clicked.connect(self._pickAccent)
        self.btnAccentReset.clicked.connect(self._resetAccent)
        self.cmbFont.activated.connect(
            lambda _i: self._save(Appearance.setFont, self.cmbFont.currentText()))
        self.spnSize.valueChanged.connect(
            lambda v: self._save(Appearance.setFontSize, v))
        self.cmbDensity.activated.connect(
            lambda _i: self._save(Appearance.setDensity, self.cmbDensity.currentText()))
        self.chkViews.toggled.connect(
            lambda v: self._save(Appearance.setViewsFollowTheme, v))
        self.chkIcons.toggled.connect(
            lambda v: self._save(Appearance.setRecolourIcons, v))
        self.btnRestart.clicked.connect(self._restart)

    def _applyLive(self):
        """Apply the active colour scheme, font, density, and view colours live."""
        from PyQt5.QtWidgets import qApp
        from manuskript import settings
        from manuskript.appearance import apply as app_apply
        from manuskript.appearance.views import applyToSettings
        app_apply.apply(qApp)
        applyToSettings(settings)
        if self.mw is not None:
            if hasattr(self.mw, "mainEditor") and self.mw.mainEditor is not None:
                self.mw.mainEditor.updateCorkBackground()
                if hasattr(self.mw.mainEditor, "tabSplitter"):
                    self.mw.mainEditor.tabSplitter.updateStyleSheet()
            if hasattr(self.mw, "whiteboardView") and self.mw.whiteboardView is not None:
                self.mw.whiteboardView.canvas.viewport().update()
            sw = getattr(self.mw, "sw", None)
            if sw is not None:
                sw.updateAllWidgets()
        self.btnRestart.setEnabled(True)
        self.lblNote.setText(self.tr("Theme applied live. You can also restart if any icon needs refreshing."))

    def _needRestart(self):
        self._applyLive()

    def _save(self, setter, value):
        if self._loading:
            return
        setter(value)
        self._applyLive()

    def _schemeChanged(self, item, _prev=None):
        if self._loading or item is None:
            return
        Appearance.setScheme(item.data(Qt.UserRole))
        self._showAccent()
        self._applyLive()

    def _pickAccent(self):
        s = Appearance.active()
        start = QColor(Appearance.accent() or (s.accent if s else "#6ea8fe"))
        c = QColorDialog.getColor(start, self, self.tr("Accent colour"))
        if c.isValid():
            Appearance.setAccent(c.name())
            self._showAccent()
            self._needRestart()

    def _resetAccent(self):
        Appearance.setAccent("")
        self._showAccent()
        self._needRestart()

    def _restart(self):
        from manuskript.appearance.restart import restartApp
        mw = self.mw
        if mw is not None:
            restartApp(mw)
