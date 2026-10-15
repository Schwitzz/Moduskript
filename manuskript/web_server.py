#!/usr/bin/env python
# --!-- coding: utf8 --!--
"""Web Server integration, background process controller, commingled project helpers,
and Settings page for Moduskript / Manuskript Desktop.
"""

import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests
from PyQt5.QtCore import QObject, QSettings, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (QCheckBox, QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
                             QWidget, qApp)

from manuskript.functions import openURL, writablePath

LOGGER = logging.getLogger(__name__)

DEFAULT_WEB_REPO = "/home/ab/workspaces/manuskript-ai-web"
DEFAULT_PORT = 8770


def _qs():
    return QSettings(qApp.organizationName(), qApp.applicationName())


def _get(name, default, typ=str):
    s = _qs()
    s.beginGroup("WebServer")
    try:
        return s.value(name, default, type=typ)
    finally:
        s.endGroup()


def _set(name, value):
    s = _qs()
    s.beginGroup("WebServer")
    s.setValue(name, value)
    s.endGroup()
    s.sync()


def _is_project_folder(path: Path) -> bool:
    """Return True if `path` is itself a single Manuskript/Moduskript project folder."""
    if not path.is_dir():
        return False
    if (path / "MANUSKRIPT").is_file():
        return True
    if (path / "infos.txt").is_file() and (path / "outline").is_dir():
        return True
    return False


def resolve_projects_dir(raw_path: str) -> str:
    """Smartly resolve a user-picked folder into the directory containing project folders.

    Handles all cases:
    1. User picked a single `<Project>` folder (e.g., `/path/to/MyNovel` containing `MANUSKRIPT`
       or `infos.txt` + `outline/`): returns its parent directory (`/path/to`).
    2. User picked a folder containing a single project subfolder (e.g., `/home/ab/Documents/manuskript`
       containing `MSK/Draft-0001` alongside an empty or sibling `projects/` folder): returns the
       subdirectory that actually contains the project(s).
    3. User picked a `<data>` root folder that has a `projects/` subdirectory with projects inside:
       returns `<data>/projects`.
    4. User picked a folder that directly contains projects (`.msk` files or `<Project>/MANUSKRIPT`
       subfolders): returns that folder itself.
    """
    if not raw_path or not str(raw_path).strip():
        return os.path.join(DEFAULT_WEB_REPO, "data", "projects")
    p = Path(str(raw_path).strip()).expanduser().resolve()
    if p.is_file() and p.suffix == ".msk":
        return str(p.parent)
    if _is_project_folder(p):
        return str(p.parent)
    if not p.is_dir():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return str(p)

    def _count_projects_in(directory: Path) -> int:
        if not directory.is_dir():
            return 0
        count = 0
        try:
            for child in directory.iterdir():
                if not child.name.startswith(".") and child.is_dir() and _is_project_folder(child):
                    count += 1
        except OSError:
            pass
        return count

    direct_count = _count_projects_in(p)
    if direct_count > 0:
        return str(p)

    # Check immediate subdirectories (e.g. `projects/`, `MSK/`, etc.) for projects
    best_sub = None
    best_count = 0
    try:
        for sub in sorted(p.iterdir(), key=lambda x: (x.name != "projects", x.name.lower())):
            if sub.is_dir() and not sub.name.startswith(".") and sub.name not in ("app", "templates"):
                c = _count_projects_in(sub)
                if c > best_count:
                    best_count = c
                    best_sub = sub
    except OSError:
        pass
    if best_sub is not None and best_count > 0:
        return str(best_sub)

    sub_projects = p / "projects"
    if sub_projects.is_dir():
        return str(sub_projects)
    return str(p)


class WebServerConfig:
    """Persistent configuration in QSettings group 'WebServer'."""

    @staticmethod
    def startOnLaunch():
        return _get("startOnLaunch", False, bool)

    @staticmethod
    def setStartOnLaunch(val):
        _set("startOnLaunch", bool(val))

    @staticmethod
    def runInBackgroundOnClose():
        return _get("runInBackgroundOnClose", True, bool)

    @staticmethod
    def setRunInBackgroundOnClose(val):
        _set("runInBackgroundOnClose", bool(val))

    @staticmethod
    def port():
        p = _get("port", DEFAULT_PORT, int)
        return p if 1024 <= p <= 65535 else DEFAULT_PORT

    @staticmethod
    def setPort(val):
        _set("port", int(val))

    @staticmethod
    def allowLan():
        return _get("allowLan", False, bool)

    @staticmethod
    def setAllowLan(val):
        _set("allowLan", bool(val))

    @staticmethod
    def host():
        return "0.0.0.0" if WebServerConfig.allowLan() else "127.0.0.1"

    @staticmethod
    def webRepoPath():
        candidates = [
            _get("webRepoPath", ""),
            DEFAULT_WEB_REPO,
            "/usr/share/moduskript-web",
            "/usr/share/manuskript-web",
        ]
        for c in candidates:
            if c and os.path.isdir(os.path.join(c, "server")):
                return c
        return _get("webRepoPath", DEFAULT_WEB_REPO) or DEFAULT_WEB_REPO

    @staticmethod
    def setWebRepoPath(path):
        _set("webRepoPath", str(path or "").strip())

    @staticmethod
    def dataDir():
        default_data = os.path.join(WebServerConfig.webRepoPath(), "data")
        val = _get("dataDir", default_data)
        return val or default_data

    @staticmethod
    def setDataDir(path):
        clean = str(path or "").strip()
        _set("dataDir", clean)

    @staticmethod
    def appDataDir():
        """Directory holding `app/` (SQLite DB, AI chats) and `templates/`."""
        raw = WebServerConfig.dataDir()
        p = Path(raw).expanduser().resolve()
        if p.name == "projects":
            return str(p.parent)
        if _is_project_folder(p):
            return os.path.join(WebServerConfig.webRepoPath(), "data")
        if (p / "app").is_dir() or (p / "projects").is_dir():
            return str(p)
        # If user pointed dataDir at an arbitrary projects folder (e.g. ~/Documents/Novels),
        # keep app.db in the web repo data dir (or user writablePath) so auth DB is never lost.
        repo_data = os.path.join(WebServerConfig.webRepoPath(), "data")
        if os.path.isdir(repo_data) and os.access(repo_data, os.W_OK):
            return repo_data
        return writablePath("web_data")

    @staticmethod
    def sharedProjectsDir():
        raw = WebServerConfig.dataDir()
        resolved = resolve_projects_dir(raw)
        try:
            os.makedirs(resolved, exist_ok=True)
        except OSError:
            pass
        return resolved


def ensure_commingled_project_markers(projects_dir=None):
    """Ensure every project in `projects_dir` has both `<Name>/MANUSKRIPT` and `<Name>.msk`.

    - If `projects_dir` is itself a single project folder, syncs its parent folder so both
      `<Name>.msk` and `<Name>/MANUSKRIPT` exist side by side.
    - Projects created in the Web App have `<Name>/MANUSKRIPT` on disk; creating `<Name>.msk`
      allows Desktop Moduskript to open them directly.
    - Projects saved in Desktop Moduskript as a folder have `<Name>.msk` + `<Name>/`; ensuring
      `<Name>/MANUSKRIPT` allows the Web Server to list and open them immediately.
    Returns a list of `.msk` file paths found/synced in `projects_dir`.
    """
    target_dir = resolve_projects_dir(projects_dir) if projects_dir else WebServerConfig.sharedProjectsDir()
    root = Path(target_dir)
    if not root.is_dir():
        return []
    msk_files = []
    try:
        for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                marker_inside = entry / "MANUSKRIPT"
                msk_outside = root / f"{entry.name}.msk"
                if _is_project_folder(entry) and not marker_inside.exists():
                    try:
                        marker_inside.write_text("1", encoding="utf8")
                    except OSError:
                        pass
                if marker_inside.is_file() and not msk_outside.exists():
                    try:
                        msk_outside.write_text("1", encoding="utf8")
                    except OSError:
                        pass
                if msk_outside.is_file() and marker_inside.is_file():
                    msk_files.append(str(msk_outside))
    except OSError:
        pass
    return msk_files


def project_folder_signature(project_msk_path):
    """Compute a fast signature of a project folder's files to detect external Web App saves."""
    if not project_msk_path:
        return ""
    folder = Path(str(project_msk_path)[:-4] if str(project_msk_path).endswith(".msk") else str(project_msk_path))
    if not folder.is_dir():
        return ""
    h = hashlib.sha256()
    try:
        for dirpath, dirnames, filenames in os.walk(folder):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in sorted(filenames):
                if fn.startswith("."):
                    continue
                fp = Path(dirpath) / fn
                try:
                    st = fp.stat()
                    rel = os.path.relpath(fp, folder)
                    h.update(f"{rel}:{st.st_mtime_ns}:{st.st_size}\n".encode("utf8"))
                except OSError:
                    continue
    except OSError:
        return ""
    return h.hexdigest()


class WebServerManager(QObject):
    """Manages starting, stopping, health-checking, and background execution of the Web App server."""

    statusChanged = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None

    @staticmethod
    def pidFilePath():
        return os.path.join(writablePath("web_server"), "web_server.pid")

    @staticmethod
    def logFilePath():
        return os.path.join(writablePath("web_server"), "web_server.log")

    def serverUrl(self, project_name=None):
        port = WebServerConfig.port()
        base = f"http://127.0.0.1:{port}"
        if project_name:
            return f"{base}/write"
        return base

    def isRunning(self, timeout=0.6):
        port = WebServerConfig.port()
        try:
            r = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return True
        except Exception:
            pass
        return False

    def _readSavedPidInfo(self):
        pf = self.pidFilePath()
        if not os.path.isfile(pf):
            return None
        try:
            data = json.loads(Path(pf).read_text(encoding="utf8"))
            pid = int(data.get("pid", 0))
            if pid > 0:
                os.kill(pid, 0)
                return data
        except Exception:
            pass
        return None

    def _readSavedPid(self):
        info = self._readSavedPidInfo()
        return int(info["pid"]) if info and "pid" in info else None

    def _writePid(self, pid):
        pf = self.pidFilePath()
        try:
            Path(pf).write_text(
                json.dumps({
                    "pid": pid,
                    "port": WebServerConfig.port(),
                    "projects_dir": WebServerConfig.sharedProjectsDir(),
                    "at": time.time(),
                }),
                encoding="utf8",
            )
        except OSError:
            pass

    def _clearPid(self):
        try:
            Path(self.pidFilePath()).unlink(missing_ok=True)
        except OSError:
            pass

    def _findPythonExecutable(self, server_dir):
        venv_py = os.path.join(server_dir, ".venv", "bin", "python")
        if os.path.isfile(venv_py) and os.access(venv_py, os.X_OK):
            return [venv_py, "-m", "uvicorn"]
        uv_bin = "/usr/bin/uv"
        for p in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(p, "uv")
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                uv_bin = cand
                break
        if os.path.isfile(uv_bin):
            return [uv_bin, "run", "uvicorn"]
        return [sys.executable, "-m", "uvicorn"]

    def start(self, wait_ready=True, timeout=8.0, force_restart=False):
        """Start the FastAPI/Uvicorn web server (restarting if projects_dir changed)."""
        ensure_commingled_project_markers()
        wanted_projects_dir = WebServerConfig.sharedProjectsDir()

        if self.isRunning():
            saved_info = self._readSavedPidInfo()
            if force_restart or (
                saved_info and saved_info.get("projects_dir") != wanted_projects_dir
            ):
                self.stop()
            else:
                self.statusChanged.emit(True, f"Running on port {WebServerConfig.port()}")
                return True

        repo = WebServerConfig.webRepoPath()
        server_dir = os.path.join(repo, "server")
        if not os.path.isdir(server_dir):
            msg = f"Web server directory not found: {server_dir}"
            LOGGER.error(msg)
            self.statusChanged.emit(False, msg)
            return False

        static_dir = os.path.join(repo, "web", "build")
        app_data_dir = WebServerConfig.appDataDir()
        os.makedirs(wanted_projects_dir, exist_ok=True)
        os.makedirs(os.path.join(app_data_dir, "app"), exist_ok=True)
        os.makedirs(os.path.join(app_data_dir, "templates"), exist_ok=True)

        port = WebServerConfig.port()
        host = WebServerConfig.host()

        env = os.environ.copy()
        env["MSK_DATA_DIR"] = app_data_dir
        env["MSK_PROJECTS_DIR_OVERRIDE"] = wanted_projects_dir
        env["MSK_COOKIE_SECURE"] = "false"
        if os.path.isdir(static_dir):
            env["MSK_STATIC_DIR"] = static_dir

        cmd = self._findPythonExecutable(server_dir) + [
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ]

        log_fh = open(self.logFilePath(), "ab")
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=server_dir,
                env=env,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            self._writePid(self._proc.pid)
        except Exception as e:
            log_fh.close()
            msg = f"Failed to start web server: {e}"
            LOGGER.error(msg)
            self.statusChanged.emit(False, msg)
            return False

        if wait_ready:
            deadline = time.time() + timeout
            while time.time() < deadline:
                if self.isRunning(timeout=0.3):
                    self.statusChanged.emit(True, f"Running on port {port}")
                    return True
                if self._proc.poll() is not None:
                    break
                time.sleep(0.15)

        running = self.isRunning(timeout=0.5)
        self.statusChanged.emit(
            running,
            f"Running on port {port}" if running else "Server failed to start (check log)",
        )
        return running

    def restart(self, wait_ready=True, timeout=8.0):
        self.stop()
        return self.start(wait_ready=wait_ready, timeout=timeout, force_restart=True)

    def stop(self):
        """Stop the running web server (owned process, saved PID, or port listener)."""
        pid = None
        if self._proc is not None and self._proc.poll() is None:
            pid = self._proc.pid
        if pid is None:
            pid = self._readSavedPid()

        if pid is not None:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception:
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
            deadline = time.time() + 3.0
            while time.time() < deadline:
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except OSError:
                    break

        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                pass
            self._proc = None

        self._clearPid()
        self.statusChanged.emit(False, "Stopped")
        return not self.isRunning(timeout=0.2)

    def openInBrowser(self, project_name=None):
        ensure_commingled_project_markers()
        self.start(wait_ready=True)
        openURL(self.serverUrl(project_name))


class WebServerSettingsPage(QScrollArea):
    """Settings page for configuring and controlling the integrated Web App server."""

    def __init__(self, mw=None, parent=None):
        super().__init__(parent)
        self.mw = mw
        self.manager = getattr(mw, "webServerManager", None) or WebServerManager(self)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        body = QWidget()
        self.setWidget(body)
        lay = QVBoxLayout(body)

        # 1. Server Status & Actions
        grp_status = QGroupBox(self.tr("Web App Server Control"))
        v_status = QVBoxLayout(grp_status)

        status_row = QHBoxLayout()
        self.lblStatusBadge = QLabel()
        font = self.lblStatusBadge.font()
        font.setBold(True)
        self.lblStatusBadge.setFont(font)
        status_row.addWidget(QLabel(self.tr("Status:")))
        status_row.addWidget(self.lblStatusBadge, 1)
        v_status.addLayout(status_row)

        btn_row = QHBoxLayout()
        self.btnStart = QPushButton(self.tr("Start Web Server"))
        self.btnStop = QPushButton(self.tr("Stop Web Server"))
        self.btnLaunchBrowser = QPushButton(self.tr("Open Web App in Browser"))
        self.btnStart.clicked.connect(self._onStartClicked)
        self.btnStop.clicked.connect(self._onStopClicked)
        self.btnLaunchBrowser.clicked.connect(self._onOpenBrowserClicked)
        btn_row.addWidget(self.btnStart)
        btn_row.addWidget(self.btnStop)
        btn_row.addWidget(self.btnLaunchBrowser)
        v_status.addLayout(btn_row)
        lay.addWidget(grp_status)

        # 2. Startup & Background Behaviour
        grp_bg = QGroupBox(self.tr("Startup & Background Mode"))
        v_bg = QVBoxLayout(grp_bg)
        self.chkStartOnLaunch = QCheckBox(
            self.tr("Start web-app server automatically when Moduskript starts")
        )
        self.chkRunInBackground = QCheckBox(
            self.tr("Keep web-app server running in the background when the desktop app is closed")
        )
        self.chkAllowLan = QCheckBox(
            self.tr("Allow LAN / VPN connections (bind to 0.0.0.0 instead of 127.0.0.1)")
        )
        v_bg.addWidget(self.chkStartOnLaunch)
        v_bg.addWidget(self.chkRunInBackground)
        v_bg.addWidget(self.chkAllowLan)
        lay.addWidget(grp_bg)

        # 3. Network & Commingled File Structure
        grp_paths = QGroupBox(self.tr("Network & Commingled Project Storage"))
        f_paths = QFormLayout(grp_paths)

        self.spnPort = QSpinBox()
        self.spnPort.setRange(1024, 65535)
        f_paths.addRow(self.tr("Server port:"), self.spnPort)

        data_row = QHBoxLayout()
        self.txtDataDir = QLineEdit()
        self.btnBrowseDataDir = QPushButton(self.tr("Browse..."))
        self.btnBrowseDataDir.clicked.connect(self._browseDataDir)
        data_row.addWidget(self.txtDataDir, 1)
        data_row.addWidget(self.btnBrowseDataDir)
        f_paths.addRow(self.tr("Projects / Data Folder:"), data_row)

        self.lblProjectsDirInfo = QLabel()
        self.lblProjectsDirInfo.setWordWrap(True)
        f_paths.addRow(self.tr("Active Commingled Projects Folder:"), self.lblProjectsDirInfo)

        self.btnSyncMarkers = QPushButton(self.tr("Sync Shared Project Markers Now"))
        self.btnSyncMarkers.clicked.connect(self._syncMarkersNow)
        f_paths.addRow("", self.btnSyncMarkers)
        lay.addWidget(grp_paths)
        lay.addStretch(1)

        self._loadValues()
        self._connectSignals()
        self.refreshStatus()

    def _loadValues(self):
        self._loading = True
        self.chkStartOnLaunch.setChecked(WebServerConfig.startOnLaunch())
        self.chkRunInBackground.setChecked(WebServerConfig.runInBackgroundOnClose())
        self.chkAllowLan.setChecked(WebServerConfig.allowLan())
        self.spnPort.setValue(WebServerConfig.port())
        self.txtDataDir.setText(WebServerConfig.dataDir())
        self.lblProjectsDirInfo.setText(WebServerConfig.sharedProjectsDir())
        self._loading = False

    def _connectSignals(self):
        self.chkStartOnLaunch.toggled.connect(WebServerConfig.setStartOnLaunch)
        self.chkRunInBackground.toggled.connect(WebServerConfig.setRunInBackgroundOnClose)
        self.chkAllowLan.toggled.connect(WebServerConfig.setAllowLan)
        self.spnPort.valueChanged.connect(WebServerConfig.setPort)
        self.txtDataDir.editingFinished.connect(self._onDataDirChanged)
        self.manager.statusChanged.connect(lambda _r, _m: self.refreshStatus())

    def _onDataDirChanged(self):
        WebServerConfig.setDataDir(self.txtDataDir.text())
        resolved = WebServerConfig.sharedProjectsDir()
        self.lblProjectsDirInfo.setText(resolved)
        ensure_commingled_project_markers(resolved)
        if self.manager.isRunning(timeout=0.2):
            self.manager.restart(wait_ready=True)

    def _browseDataDir(self):
        d = QFileDialog.getExistingDirectory(
            self, self.tr("Select Projects or Data Folder"), self.txtDataDir.text()
        )
        if d:
            self.txtDataDir.setText(d)
            self._onDataDirChanged()

    def _syncMarkersNow(self):
        WebServerConfig.setDataDir(self.txtDataDir.text())
        resolved = WebServerConfig.sharedProjectsDir()
        self.lblProjectsDirInfo.setText(resolved)
        found = ensure_commingled_project_markers(resolved)
        if self.mw and hasattr(self.mw, "welcome"):
            self.mw.welcome.populateTemplates()
        if self.manager.isRunning(timeout=0.2):
            self.manager.restart(wait_ready=True)
        names = [os.path.basename(p)[:-4] for p in found]
        summary = ", ".join(names) if names else self.tr("none found")
        self.lblStatusBadge.setText(
            self.tr("Synced %d project(s) (%s)") % (len(found), summary)
        )

    def _onStartClicked(self):
        self.manager.start(wait_ready=True)
        self.refreshStatus()

    def _onStopClicked(self):
        self.manager.stop()
        self.refreshStatus()

    def _onOpenBrowserClicked(self):
        proj = None
        if self.mw and getattr(self.mw, "currentProject", None):
            proj = self.mw.projectName()
        self.manager.openInBrowser(proj)
        self.refreshStatus()

    def refreshStatus(self):
        running = self.manager.isRunning(timeout=0.3)
        port = WebServerConfig.port()
        if running:
            self.lblStatusBadge.setText(
                self.tr("Running at http://127.0.0.1:%d") % port
            )
            self.btnStart.setEnabled(False)
            self.btnStop.setEnabled(True)
        else:
            self.lblStatusBadge.setText(self.tr("Stopped"))
            self.btnStart.setEnabled(True)
            self.btnStop.setEnabled(False)
