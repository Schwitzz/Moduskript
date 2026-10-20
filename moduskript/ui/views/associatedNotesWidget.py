#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Associated Notes manager widget for Outline items (Chapters, Scenes, Folders).

Displays, creates, edits, and deletes structured notes stored in `Outline.associatedNotes`
(JSON array `[{"id": "...", "title": "...", "text": "..."}]`), matching the Web App's
Inspector & Outline detail panel.
"""

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel,
                             QLineEdit, QPlainTextEdit, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from moduskript.enums import Outline
from moduskript.functions.outlineHelpers import (add_associated_note,
                                                 delete_associated_note,
                                                 parse_associated_notes,
                                                 update_associated_note)


class AssociatedNotesWidget(QWidget):
    """Compact widget for viewing and editing an outlineItem's associatedNotes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = None
        self._current_index = QModelIndex()
        self._updating = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(6)

        hdr = QHBoxLayout()
        self.lblHeader = QLabel(self.tr("Associated Notes"))
        font = self.lblHeader.font()
        font.setBold(True)
        self.lblHeader.setFont(font)
        hdr.addWidget(self.lblHeader)
        hdr.addStretch(1)

        self.btnAddNote = QPushButton(self.tr("+ New note"))
        self.btnAddNote.setToolTip(self.tr("Add a note associated with this chapter or scene"))
        self.btnAddNote.clicked.connect(self.promptAddNote)
        hdr.addWidget(self.btnAddNote)
        outer.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMinimumHeight(90)
        self.container = QWidget()
        self.notesLayout = QVBoxLayout(self.container)
        self.notesLayout.setContentsMargins(0, 0, 0, 0)
        self.notesLayout.setSpacing(6)
        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll, 1)

        self.setEnabled(False)

    def setModel(self, mdl_outline):
        if self._model is not None:
            try:
                self._model.dataChanged.disconnect(self._onModelDataChanged)
            except Exception:
                pass
        self._model = mdl_outline
        if self._model is not None:
            self._model.dataChanged.connect(self._onModelDataChanged)

    def currentItem(self):
        if self._current_index and self._current_index.isValid():
            return self._current_index.internalPointer()
        return None

    def setCurrentModelIndex(self, index):
        self._current_index = index if (index and index.isValid()) else QModelIndex()
        item = self.currentItem()
        self.setEnabled(item is not None)
        self.refresh()

    def _onModelDataChanged(self, topLeft, bottomRight):
        if self._updating or not self._current_index.isValid():
            return
        cur_item = self.currentItem()
        if topLeft.isValid() and topLeft.internalPointer() == cur_item:
            if topLeft.column() <= Outline.associatedNotes <= bottomRight.column():
                self.refresh()

    def _clearLayout(self):
        while self.notesLayout.count():
            child = self.notesLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def refresh(self):
        self._clearLayout()
        item = self.currentItem()
        if item is None:
            return
        notes = parse_associated_notes(item.data(Outline.associatedNotes))
        if not notes:
            lbl = QLabel(self.tr("No associated notes yet."))
            lbl.setStyleSheet("color: gray; font-size: 11px;")
            self.notesLayout.addWidget(lbl)
            self.notesLayout.addStretch(1)
            return

        for note in notes:
            nid = note["id"]
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            cv = QVBoxLayout(card)
            cv.setContentsMargins(6, 6, 6, 6)
            cv.setSpacing(4)

            top_row = QHBoxLayout()
            txt_title = QLineEdit(note["title"])
            txt_title.setPlaceholderText(self.tr("Note title"))
            txt_title.editingFinished.connect(
                lambda nid=nid, w=txt_title: self._updateNoteTitle(nid, w.text())
            )
            top_row.addWidget(txt_title, 1)

            btn_del = QPushButton("×")
            btn_del.setFixedWidth(24)
            btn_del.setToolTip(self.tr("Delete note"))
            btn_del.clicked.connect(lambda _c=False, nid=nid: self.deleteNote(nid))
            top_row.addWidget(btn_del)
            cv.addLayout(top_row)

            txt_body = QPlainTextEdit(note["text"])
            txt_body.setPlaceholderText(self.tr("Write note..."))
            txt_body.setMaximumHeight(68)
            txt_body.textChanged.connect(
                lambda nid=nid, w=txt_body: self._updateNoteText(nid, w.toPlainText())
            )
            cv.addWidget(txt_body)
            self.notesLayout.addWidget(card)

        self.notesLayout.addStretch(1)

    def addNote(self, title, text=""):
        item = self.currentItem()
        if item is None:
            return None
        self._updating = True
        try:
            created = add_associated_note(item, title, text)
        finally:
            self._updating = False
        self.refresh()
        return created

    def promptAddNote(self):
        item = self.currentItem()
        if item is None:
            return None
        title, ok = QInputDialog.getText(
            self,
            self.tr("New Associated Note"),
            self.tr("Note title:"),
        )
        if not ok or not title.strip():
            return None
        text, ok2 = QInputDialog.getMultiLineText(
            self,
            self.tr("New Associated Note"),
            self.tr("Note text:"),
        )
        if not ok2:
            return None
        return self.addNote(title.strip(), text)

    def _updateNoteTitle(self, note_id, new_title):
        item = self.currentItem()
        if item is None:
            return
        self._updating = True
        try:
            update_associated_note(item, note_id, title=new_title)
        finally:
            self._updating = False

    def _updateNoteText(self, note_id, new_text):
        item = self.currentItem()
        if item is None:
            return
        self._updating = True
        try:
            update_associated_note(item, note_id, text=new_text)
        finally:
            self._updating = False

    def deleteNote(self, note_id):
        item = self.currentItem()
        if item is None:
            return
        self._updating = True
        try:
            delete_associated_note(item, note_id)
        finally:
            self._updating = False
        self.refresh()
