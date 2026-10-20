#!/usr/bin/env python
# --!-- coding: utf8 --!--
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeView, QHeaderView

from moduskript import settings
from moduskript.enums import Outline
from moduskript.ui.views.dndView import dndView
from moduskript.ui.views.outlineBasics import outlineBasics
from moduskript.ui.views.outlineDelegates import outlineTitleDelegate, outlineCharacterDelegate, outlineCompileDelegate, \
    outlineStatusDelegate, outlineGoalPercentageDelegate, outlineLabelDelegate


class outlineView(QTreeView, dndView, outlineBasics):
    def __init__(self, parent=None, modelCharacters=None, modelLabels=None, modelStatus=None):
        QTreeView.__init__(self, parent)
        dndView.__init__(self)
        outlineBasics.__init__(self, parent)

        self.modelCharacters = modelCharacters
        self.modelLabels = modelLabels
        self.modelStatus = modelStatus

        self.header().setStretchLastSection(False)

    def setModelCharacters(self, model):
        # This is used by outlineCharacterDelegate to select character
        self.modelCharacters = model

    def setModelLabels(self, model):
        # This is used by outlineLabelDelegate to display labels
        self.modelLabels = model

    def setModelStatus(self, model):
        # This is used by outlineStatusDelegate to display statuses
        self.modelStatus = model

    def setModel(self, model):
        QTreeView.setModel(self, model)

        # Setting delegates
        self.outlineTitleDelegate = outlineTitleDelegate(self)
        # self.outlineTitleDelegate.setView(self)
        self.setItemDelegateForColumn(Outline.title, self.outlineTitleDelegate)
        self.outlineCharacterDelegate = outlineCharacterDelegate(self.modelCharacters)
        self.setItemDelegateForColumn(Outline.POV, self.outlineCharacterDelegate)
        self.outlineCompileDelegate = outlineCompileDelegate()
        self.setItemDelegateForColumn(Outline.compile, self.outlineCompileDelegate)
        self.outlineStatusDelegate = outlineStatusDelegate(self.modelStatus)
        self.setItemDelegateForColumn(Outline.status, self.outlineStatusDelegate)
        self.outlineGoalPercentageDelegate = outlineGoalPercentageDelegate()
        self.setItemDelegateForColumn(Outline.goalPercentage, self.outlineGoalPercentageDelegate)
        self.outlineLabelDelegate = outlineLabelDelegate(self.modelLabels)
        self.setItemDelegateForColumn(Outline.label, self.outlineLabelDelegate)

        # Hiding columns
        self.hideColumns()

        self.header().setSectionResizeMode(Outline.title, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.POV, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.status, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.label, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.compile, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.wordCount, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.goal, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.goalPercentage, QHeaderView.ResizeToContents)
        self.header().setSectionResizeMode(Outline.summarySentence, QHeaderView.Stretch)

    def setViewMode(self, mode):
        """Switch between 'tree' (minimal tree view) and 'table' (multi-column outline table)."""
        self._viewMode = mode
        if not self.model():
            return
        if mode == "tree":
            for c in range(self.model().columnCount()):
                self.hideColumn(c)
            self.showColumn(Outline.title)
            self.header().setVisible(False)
        else:
            self.header().setVisible(True)
            self.hideColumns()
            self.expandAll()

    def hideColumns(self):
        if not self.model():
            # outlineView is probably not initialized, because editorWidgets shows index cards or text.
            return

        if getattr(self, "_viewMode", "table") == "tree":
            for c in range(self.model().columnCount()):
                self.hideColumn(c)
            self.showColumn(Outline.title)
            return

        for c in range(self.model().columnCount()):
            self.hideColumn(c)
        for c in settings.outlineViewColumns:
            if c != Outline.notes:  # Notes column never shown inline in table (parity with Web)
                self.showColumn(c)

    def setRootIndex(self, index):
        QTreeView.setRootIndex(self, index)
        self.outlineGoalPercentageDelegate = outlineGoalPercentageDelegate(index)
        self.setItemDelegateForColumn(Outline.goalPercentage, self.outlineGoalPercentageDelegate)

    def dragMoveEvent(self, event):
        dndView.dragMoveEvent(self, event)
        QTreeView.dragMoveEvent(self, event)

    def mousePressEvent(self, event):
        # Prevent selecting item while right-clicking for popup menu!
        if event.button() != Qt.RightButton:
            QTreeView.mousePressEvent(self, event)
            outlineBasics.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        QTreeView.mouseReleaseEvent(self, event)
        outlineBasics.mouseReleaseEvent(self, event)
