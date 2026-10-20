# --!-- coding: utf8 --!--
"""Restart Manuskript so a new colour scheme takes effect."""

import os
import sys

from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import qApp


def restartApp(mw):
    """Save the open project, start a fresh copy that reopens it, then quit.
    Returns False (and does nothing) if the user cancels a save prompt."""
    project = getattr(mw, "currentProject", None)
    if project:
        if not mw.handleUnsavedChanges():
            return False
        mw.saveDatas()
    args = [a for a in sys.argv if a.endswith(".msk") is False]
    if project and str(project).endswith(".msk"):
        args.append(project)
    if not args or not os.path.exists(args[0]):
        args = [os.path.abspath(sys.argv[0])] + args[1:]
    started = QProcess.startDetached(sys.executable, args)
    if started:
        mw.close()
        qApp.quit()
    return started
