#!/usr/bin/env python
# --!-- coding: utf8 --!--


from moduskript.models import references as Ref
from moduskript.functions import mainWindow
from moduskript.enums import World
from PyQt5.QtWidgets import QTextEdit, QLineEdit
from moduskript.ui.highlighters.searchResultHighlighters.abstractSpecificSearchResultHighlighter import abstractSearchResultHighlighter


class worldSearchResultHighlighter(abstractSearchResultHighlighter):
    def __init__(self):
        super().__init__()

    def openView(self, searchResult):
        r = Ref.worldReference(searchResult.id())
        Ref.open(r)
        mainWindow().tabWorld.setEnabled(True)

    def retrieveWidget(self, searchResult):
        textEditMap = {
            World.name: (0, "txtWorldName", QLineEdit),
            World.description: (0, "txtWorldDescription", QTextEdit),
            World.passion: (1, "txtWorldPassion", QTextEdit),
            World.conflict: (1, "txtWorldConflict", QTextEdit),
        }

        tabIndex, widgetName, widgetClass = textEditMap[searchResult.column()]

        mainWindow().tabWorld.setCurrentIndex(tabIndex)
        return mainWindow().tabWorld.findChild(widgetClass, widgetName)
