# Chunk 6: Web App Integration, Commingled File Structure & Background Server

**Status:** ✅ Complete (Tests Passing: 83 Desktop pytest)

## Goal
1. Integrate the `manuskript-ai-web` server into the Desktop App so it can be started, stopped, configured, and launched in the user's browser directly from Desktop Manuskript.
2. Commingle the file structure so Desktop and Web read and write to the exact same project folders safely.
3. Provide options to **start the web-app server automatically on app launch** and **keep the web server running in the background when the desktop app is closed** (with a System Tray icon and background process management).

---

## Scope & Files to Modify / Create

### 1. Web Server Controller (`manuskript/web_server.py` — New Module)
- **`WebServerConfig` (QSettings group `"WebServer"`)**:
  - `enabledOnStartup: bool` (default `False`) — Start web server automatically when Desktop app starts.
  - `runInBackgroundOnClose: bool` (default `True`) — Keep web server running in background when Desktop window closes (minimizes to system tray and/or detaches server process).
  - `port: int` (default `8770`).
  - `host: str` (default `"127.0.0.1"`, with option for `"0.0.0.0"` LAN access).
  - `webRepoPath: str` (default `"/home/ab/workspaces/manuskript-ai-web"`, auto-detected from `/home/ab/workspaces/manuskript-ai-web` or `/usr/share/manuskript-web`).
  - `sharedProjectsDir: str` (default `"/home/ab/workspaces/manuskript-ai-web/data/projects"`).
- **`WebServerManager(QObject)`**:
  - Starts `uvicorn app.main:app` with `MSK_DATA_DIR`, `MSK_STATIC_DIR=<webRepo>/web/build`, `MSK_PORT`, and `MSK_COOKIE_SECURE=false`.
  - Tracks PID in `~/.local/share/manuskript/web_server.pid` and checks `GET /api/health` on startup so if a background server is already running from a previous session, Desktop adopts/connects to it rather than spawning a duplicate.
  - Provides `start()`, `stop()`, `restart()`, `is_running()`, and `open_in_browser(project_name=None)` (opens `http://localhost:<port>/` or deep-links to the active project).
  - When `runInBackgroundOnClose` is enabled, spawns uvicorn with `start_new_session=True` so even if the user quits the GUI without tray or closes the window, the server continues running cleanly in the background until explicitly stopped from Tray or Settings.

### 2. Commingled File Structure & Live Sync (`manuskript/mainWindow.py` & `welcome.py`)
- **Shared Projects Folder**:
  - Default `welcome.py`'s project creation and open directory to `WebServerConfig.sharedProjectsDir()` (`/home/ab/workspaces/manuskript-ai-web/data/projects`), and add a **"Shared Web Projects"** quick-list in the Welcome screen alongside Recent Files.
  - Ensure that when Desktop creates or saves a project `<Name>.msk` + `<Name>/` folder, `<Name>/MANUSKRIPT` is present so the Web Server immediately lists `<Name>` in `/api/projects`.
  - Conversely, if a project was created in the Web App (`<Name>/MANUSKRIPT` without `<Name>.msk`), automatically create the 1-byte `<Name>.msk` marker file so Desktop Manuskript can open it directly.
- **Locking & External Change Detection**:
  - Before Desktop saves (`loadSave.py` / `version_1.py`), write and clear `<project>/.lock` (`{"owner": "desktop", "at": time.time()}`) so the Web Server's `synclock.py` respects concurrent writes.
  - Add a `QFileSystemWatcher` / periodic signature check on the open project folder so if the user edits a scene or whiteboard in the Web App while the project is open on Desktop, Desktop shows a non-intrusive banner/toast (*"Project updated from Web App — Reload"*).

### 3. Desktop UI & System Tray Integration (`manuskript/mainWindow.py` & `manuskript/web_settingsPage.py`)
- **`WebServerSettingsPage`**: Added to the revamped `settingsWindow` (from Chunk 5) with live status indicator (Running / Stopped), Start / Stop / Open in Browser buttons, Port spinbox, LAN access checkbox, Startup & Background checkboxes, and Shared Projects Folder picker.
- **Main Menu & Toolbar**: Add **Launch Web App** (`Ctrl+Shift+W`) under `Tools` menu and on the main window header/toolbar.
- **System Tray Icon (`QSystemTrayIcon`)**:
  - Shows when the app or web server is running, with menu: *Show Moduskript*, *Open Web App in Browser*, *Web Server: Running/Stopped (Toggle)*, and *Quit Moduskript (Stop Server)* / *Close Window (Keep Server Running)*.

---

## Verification & Checkpoint Gate
1. **Integration Tests (`pytest`)**:
   - Test `WebServerManager` lifecycle (start, health check, adopt existing PID, stop, background persistence).
   - Test commingled project creation: create a project in Web -> open and edit in Desktop -> verify Web API sees the changes immediately, and vice versa.
2. **Checkpoint**: Pause and review test results with user before proceeding to Chunk 7.
