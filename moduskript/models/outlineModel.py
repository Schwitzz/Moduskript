#!/usr/bin/env python
# --!-- coding: utf8 --!--

from moduskript.models.abstractModel import abstractModel
from moduskript.models.searchableModel import searchableModel
from moduskript.models.outlineItem import outlineItem

class outlineModel(abstractModel, searchableModel):
    def __init__(self, parent):
        abstractModel.__init__(self, parent)
        self.rootItem = outlineItem(model=self, title="Root", ID="0")


    def findItemsByPOV(self, POV):
        "Returns a list of IDs of all items whose POV is ``POV``."
        return self.rootItem.findItemsByPOV(POV)

    def searchableItems(self):
        result = []

        for child in self.rootItem.children():
            result += self._searchableItems(child)

        return result

    def _searchableItems(self, item):
        result = [item]

        for child in item.children():
            result += self._searchableItems(child)

        return result
