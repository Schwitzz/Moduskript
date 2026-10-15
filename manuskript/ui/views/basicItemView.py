#!/usr/bin/env python
# --!-- coding: utf8 --!--
from PyQt5.QtWidgets import QWidget, QAbstractItemView
from PyQt5.QtCore import QModelIndex

from manuskript.enums import Outline
from manuskript.ui.views.basicItemView_ui import Ui_basicItemView
from manuskript.ui.views.associatedNotesWidget import AssociatedNotesWidget


class basicItemView(QWidget, Ui_basicItemView):
    def __init__(self, parent=None):
        QWidget.__init__(self)
        self.setupUi(self)
        self.txtSummarySentence.setColumn(Outline.summarySentence)
        self.txtSummaryFull.setColumn(Outline.summaryFull)
        self.txtGoal.setColumn(Outline.setGoal)
        self.associatedNotes = AssociatedNotesWidget(self)
        self.verticalLayout.addWidget(self.associatedNotes)

    def setModels(self, mdlOutline, mdlCharacter, mdlLabels, mdlStatus):
        self.cmbPOV.setModels(mdlCharacter, mdlOutline)
        self.txtSummarySentence.setModel(mdlOutline)
        self.txtSummaryFull.setModel(mdlOutline)
        self.txtGoal.setModel(mdlOutline)
        self.associatedNotes.setModel(mdlOutline)

    def getIndexes(self, sourceView):
        """Returns a list of indexes from list of QItemSelectionRange"""
        indexes = []

        if (sourceView is None) or (not hasattr(sourceView, 'selection')):
            return indexes

        for i in sourceView.selection().indexes():
            if i.column() != 0:
                continue

            if i not in indexes:
                indexes.append(i)

        return indexes

    def selectionChanged(self):
        if isinstance(self.sender(), QAbstractItemView):
            selectionModel = self.sender().selectionModel()
        else:
            selectionModel = self.sender()

        indexes = self.getIndexes(selectionModel)

        if len(indexes) == 0:
            self.setEnabled(False)
            self.associatedNotes.setCurrentModelIndex(QModelIndex())

        elif len(indexes) == 1:
            self.setEnabled(True)
            idx = indexes[0]
            self.txtSummarySentence.setCurrentModelIndex(idx)
            self.txtSummaryFull.setCurrentModelIndex(idx)
            self.cmbPOV.setCurrentModelIndex(idx)
            self.txtGoal.setCurrentModelIndex(idx)
            self.associatedNotes.setCurrentModelIndex(idx)

        else:
            self.setEnabled(True)
            self.txtSummarySentence.setCurrentModelIndexes(indexes)
            self.txtSummaryFull.setCurrentModelIndexes(indexes)
            self.cmbPOV.setCurrentModelIndexes(indexes)
            self.txtGoal.setCurrentModelIndexes(indexes)
            self.associatedNotes.setCurrentModelIndex(QModelIndex())

    def setDict(self, d):
        self.txtSummaryFull.setDict(d)

    def toggleSpellcheck(self, v):
        self.txtSummaryFull.toggleSpellcheck(v)
