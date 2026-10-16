#!/usr/bin/env python
# --!-- coding: utf8 --!--

"""Tests for settingsWindow"""

from manuskript import functions as F

def test_general(MWSampleProject):
    MW = MWSampleProject

    # Loading from mainWindow
    MW.actSettings.triggered.emit()
    assert MW.sw.isVisible()
    MW.sw.close()
    MW.actLabels.triggered.emit()
    assert MW.sw.isVisible()
    MW.sw.close()
    MW.actStatus.triggered.emit()
    assert MW.sw.isVisible()
    MW.sw.hide()
    MW.sw.setTab("General")

    SW = MW.sw

    # Imports
    from PyQt5.QtWidgets import qApp, QStyleFactory
    from PyQt5.QtCore import QSettings, Qt
    qS = QSettings(qApp.organizationName(), qApp.applicationName())
    from manuskript import settings as S

    # Style
    assert SW.cmbStyle.count() == len(list(QStyleFactory.keys()))
    if qS.value("applicationStyle"):
        assert SW.cmbStyle.currentText() == qS.value("applicationStyle")
    ## Seg fault when trying to set the style in tests:
    # for s in styles:
    #     SW.cmbStyle.setCurrentText(s)
        # assert S.value("applicationStyle") == s

    # Translations
    if qS.value("applicationTranslation"):
        assert (SW.cmbTranslation.currentData()
                == qS.value("applicationTranslation"))
    for name in SW.translations:
        SW.cmbTranslation.setCurrentText(name)
        if qS.value("applicationTranslation"):
            assert qS.value("applicationTranslation") == SW.translations[name]

    def switchCheckBoxAndAssert(chk, settings):
        """
        Asserts that the check state is that of settings, change checkstate
        and asserts settings has been changed.
        Settings is a function that returns the value.
        """
        state = settings()
        assert chk.isChecked() == state
        chk.setChecked(not state)
        assert chk.isChecked() != state

    # Loading and Saving
    SW.txtAutoSave.setText("0")
    SW.txtAutoSaveNoChanges.setText("0")
    switchCheckBoxAndAssert(SW.chkAutoLoad,
                            lambda: qS.value("autoLoad", type=bool))
    switchCheckBoxAndAssert(SW.chkAutoSave,
                            lambda: S.autoSave)
    switchCheckBoxAndAssert(SW.chkAutoSaveNoChanges,
                            lambda: S.autoSaveNoChanges)
    switchCheckBoxAndAssert(SW.chkSaveOnQuit,
                            lambda: S.saveOnQuit)
    switchCheckBoxAndAssert(SW.chkSaveToZip,
                            lambda: S.saveToZip)

    # Revisions
    switchCheckBoxAndAssert(SW.chkRevisionsKeep,
                            lambda: S.revisions["keep"])
    switchCheckBoxAndAssert(SW.chkRevisionRemove,
                            lambda: S.revisions["smartremove"])

    # Views
    # Simple way here, we just call the functions.
    SW.cmbTreeIcon.currentIndexChanged.emit(0)
    SW.cmbOutlineIcon.currentIndexChanged.emit(0)
    SW.cmbCorkIcon.currentIndexChanged.emit(0)
    SW.chkOutlineTitle.setChecked(Qt.Checked)  #outlineColumnsChanged
    SW.chkOutlineTitle.setChecked(Qt.Unchecked)
    SW.chkOutlineTitle.setChecked(Qt.Checked)
    # Can't test because of the dialog
    # assert SW.setCorkColor() == None
    SW.sldTreeIconSize.setValue(SW.sldTreeIconSize.value() + 1)
    SW.rdoCorkNewStyle.toggled.emit(True)
    SW.cmbCorkImage.currentIndexChanged.emit(0)
    SW.cmbCorkImage.currentIndexChanged.emit(1)
    # Test editor: same problem as above
    # choseEditorFontColor
    # choseEditorMisspelledColor
    # choseEditorBackgroundColor
    # Test editor
    switchCheckBoxAndAssert(SW.chkEditorBackgroundTransparent,
                            lambda: S.textEditor["backgroundTransparent"])
    assert SW.restoreEditorColors() == None
    switchCheckBoxAndAssert(SW.chkEditorNoBlinking,
                            lambda: S.textEditor["cursorNotBlinking"])
    # Twice on purpose: set and restore
    switchCheckBoxAndAssert(SW.chkEditorNoBlinking,
                            lambda: S.textEditor["cursorNotBlinking"])
    # Manually call updateAllWidgets, because other wise timer of 250ms
    SW.updateAllWidgets()

    # Labels
    assert SW.updateLabelColor(MW.mdlLabels.item(1).index()) == None
    rc = MW.mdlLabels.rowCount()
    SW.addLabel()
    SW.lstLabels.setCurrentIndex(
        MW.mdlLabels.item(MW.mdlLabels.rowCount() - 1).index())
    SW.removeLabel()
    assert MW.mdlLabels.rowCount() == rc
    # setLabelColor # Same problem as above

    # Status
    rc = MW.mdlStatus.rowCount()
    SW.addStatus()
    SW.lstStatus.setCurrentIndex(
        MW.mdlStatus.item(MW.mdlStatus.rowCount() - 1).index())
    SW.removeStatus()
    assert MW.mdlStatus.rowCount() == rc

    # Fullscreen
    # self.lstThemes.currentItemChanged.connect(self.themeSelected)
    item = SW.lstThemes.item(0)
    SW.lstThemes.currentItemChanged.emit(item, None)
    assert S.fullScreenTheme in item.data(Qt.UserRole)
    SW.lstThemes.currentItemChanged.emit(None, None)
    count = SW.lstThemes.count()
    SW.newTheme()
    assert SW.lstThemes.count() == count + 1
    SW.newTheme() # theme with same name
    item = SW.lstThemes.item(SW.lstThemes.count() - 1)
    SW.lstThemes.setCurrentItem(item)
    SW.removeTheme()
    item = SW.lstThemes.item(count)
    SW.lstThemes.setCurrentItem(item)
    SW.editTheme()
    switchCheckBoxAndAssert(SW.chkThemeIndent,
                            lambda: SW._themeData["Spacings/IndentFirstLine"])
    SW.updateThemeFont(None)
    SW.updateThemeBackground(0)
    SW.updateThemeBackground(1)
    SW.spnThemeLineSpacing.setValue(123)
    for i in range(4):
        SW.updateLineSpacing(i)
        SW.updateUIFromTheme() # No time to wait on timer
    assert SW._editingTheme != None
    SW.resize(SW.geometry().size()) # resizeEvent
    #TODO: other edit test (see SW.loadTheme
    SW.saveTheme()
    item = SW.lstThemes.item(count)
    SW.lstThemes.setCurrentItem(item)
    SW.editTheme()
    SW.cancelEdit()
    item = SW.lstThemes.item(count)
    SW.lstThemes.setCurrentItem(item)
    SW.removeTheme()
    assert SW.lstThemes.count() == count


def test_modern_settings_search_presets_and_live_theme(MWSampleProject):
    from manuskript import settings as S
    from manuskript.appearance.config import Appearance

    MW = MWSampleProject
    MW.actSettings.triggered.emit()
    SW = MW.sw
    SW.hide()

    # 1. Verify wider sidebar & search filter bar
    assert SW.lstMenu.minimumWidth() >= 200
    SW.txtSearchSettings.setText("ai")
    assert not SW.lstMenu.item(7).isHidden()  # AI Assistant page visible
    assert SW.lstMenu.item(3).isHidden()      # Labels hidden
    SW.txtSearchSettings.setText("")
    assert not SW.lstMenu.item(3).isHidden()

    # 2. Verify setTab named navigation works for all tabs
    SW.setTab("Revisions")
    assert SW.lstMenu.currentRow() == 1
    SW.setTab("Views")
    assert SW.lstMenu.currentRow() == 2
    SW.setTab("Editor")
    assert SW.lstMenu.currentRow() == 2 and SW.tabViews.currentIndex() == SW.tabViews.count() - 1
    assert all("Index cards" not in SW.tabViews.tabText(i) for i in range(SW.tabViews.count()))
    SW.setTab("AI")
    assert SW.lstMenu.currentRow() == 7
    SW.setTab("Appearance")
    assert SW.lstMenu.currentRow() == 8

    # 3. Verify Revision Quick Presets
    SW._applyRevisionPreset(2)  # Frequent
    assert SW.spnRevisionsDay.value() == 10
    SW._applyRevisionPreset(1)  # Standard
    assert SW.spnRevisionsDay.value() == 1

    # 4. Verify Readable mode checkbox in Settings syncs with FormatBar
    SW.chkEditorReadableMode.setChecked(True)
    SW.updateAllWidgets()
    assert S.textEditor["readableMode"] is True
    assert MW.mainEditor.formatBar.btnReadable.isChecked() is True
    SW.chkEditorReadableMode.setChecked(False)
    SW.updateAllWidgets()
    assert S.textEditor["readableMode"] is False

    # 5. Verify live theme application in AppearanceSettingsPage
    ap = SW.appearancePage
    target_scheme = "dracula" if Appearance.scheme() == "nord" else "nord"
    for i in range(ap.lst.count()):
        if ap.lst.item(i).data(0x0100) == target_scheme:  # Qt.UserRole
            ap.lst.setCurrentRow(i)
            break
    assert Appearance.scheme() == target_scheme
    assert "applied live" in ap.lblNote.text()

