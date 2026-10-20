#!/usr/bin/env python
# --!-- coding: utf8 --!--

from moduskript.importer.folderImporter import folderImporter
from moduskript.importer.markdownImporter import markdownImporter
from moduskript.importer.opmlImporter import opmlImporter
from moduskript.importer.mindMapImporter import mindMapImporter
from moduskript.importer.pandocImporters import markdownPandocImporter, \
    odtPandocImporter, ePubPandocImporter, docXPandocImporter, HTMLPandocImporter, \
    rstPandocImporter, LaTeXPandocImporter, OPMLPandocImporter

importers = [
    # Internal
    markdownImporter,
    folderImporter,
    opmlImporter,
    mindMapImporter,

    # Pandoc
    markdownPandocImporter,
    odtPandocImporter,
    ePubPandocImporter,
    docXPandocImporter,
    HTMLPandocImporter,
    rstPandocImporter,
    LaTeXPandocImporter,
    OPMLPandocImporter,
    ]
