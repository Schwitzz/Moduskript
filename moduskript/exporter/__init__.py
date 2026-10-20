#!/usr/bin/env python
# --!-- coding: utf8 --!--

from moduskript.exporter.moduskript import manuskriptExporter
from moduskript.exporter.pandoc import pandocExporter

exporters = [
    manuskriptExporter(),
    pandocExporter()
]

def getExporterByName(name):
    for e in exporters:
        if e.name == name:
            return e

    return None
