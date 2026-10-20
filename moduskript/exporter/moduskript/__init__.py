#!/usr/bin/env python
# --!-- coding: utf8 --!--
from PyQt5.QtWidgets import QTextEdit, qApp

from moduskript.exporter.basic import basicExporter, basicFormat
from moduskript.exporter.moduskript.HTML import HTML
from moduskript.exporter.moduskript.markdown import markdown
from moduskript.exporter.moduskript.plainText import plainText
from moduskript.functions import appPath, safeTranslate

import os


class manuskriptExporter(basicExporter):

    name = "Manuskript"
    description = safeTranslate(qApp, "Export", "Default exporter, provides basic formats used by other exporters.")
    exportTo = [
        plainText(),
        markdown(),
        HTML(),
        basicFormat("OPML", icon="text-x-opml+xml")
    ]
    icon = appPath(os.path.join("icons", "Manuskript", "icon-256px.png"))

    @classmethod
    def isValid(cls):
        return True