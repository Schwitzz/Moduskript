#!/usr/bin/env python
# --!-- coding: utf8 --!--
from moduskript.exporter.pandoc.abstractPlainText import abstractPlainText


class abstractOutput(abstractPlainText):
    name = "SUBCLASSME"
    description = "SUBCLASSME"
    exportVarName = "SUBCLASSME"
    toFormat = "SUBCLASSME"
    icon = "SUBCLASSME"
    exportFilter = "SUBCLASSME"
    exportDefaultSuffix = ".SUBCLASSME"
    requires = {
        "Settings": True,
        "Preview": False,
    }

    def export(self, settingsWidget):
        filename = self.getExportFilename(settingsWidget)
        settingsWidget.writeSettings()
        if filename:
            content = self.output(settingsWidget, outputfile=filename)

