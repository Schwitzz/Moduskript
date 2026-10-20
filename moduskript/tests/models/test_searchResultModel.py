#!/usr/bin/env python
# --!-- coding: utf8 --!--

from moduskript.models.searchResultModel import searchResultModel
from moduskript.enums import Character


def test_searchResultModel_constructionOk():
    searchResult = searchResultModel("Character", "3", Character.notes, "Lucas", "A > B > C", (15, 18), "This is <b>Lucas</b>")
    assert searchResult.id() == "3"
    assert searchResult.column() == Character.notes
    assert searchResult.title() == "Lucas"
    assert searchResult.path() == "A > B > C"
    assert searchResult.pos() == (15, 18)
    assert searchResult.context() == "This is <b>Lucas</b>"

