# AGENTS.md — Moduskript Workspace

## Repository Layout & Boundaries

This workspace spans two linked repositories that share the same plain-text project format (`<Project>/MANUSKRIPT` + `<Project>.msk`):

- **Desktop App (`PyQt5`)**: `/home/ab/workspaces/moduskript` (GitHub: `Schwitzz/Moduskript`, branch `appearance-mod`)
  - Entrypoints: `bin/moduskript` -> `moduskript/main.py` -> `moduskript/mainWindow.py`
  - Python package root: `/home/ab/workspaces/moduskript/moduskript/`
  - System-installed binary `/usr/bin/moduskript` loads from `/usr/share/moduskript/` when installed via `.deb`; rebuild the `.deb` after desktop changes so `/home/ab/workspaces/moduskript/releases/` stays current.
- **Web App (`FastAPI` + `SvelteKit 5`)**: `/home/ab/workspaces/moduskript-web`
  - Backend: `/home/ab/workspaces/moduskript-web/server` (`app/` FastAPI routes, `msklib/` file format reader/writer)
  - Frontend: `/home/ab/workspaces/moduskript-web/web` (Svelte 5 runes, Tailwind v4, CodeMirror 6, `@xyflow/svelte`), built statically to `web/build` and served by FastAPI (`MSK_STATIC_DIR=../web/build`).

---

## Developer Commands

### Desktop App (`/home/ab/workspaces/moduskript`)
- **Run from source**:
  ```bash
  python3 bin/moduskript
  ```
- **Run all desktop tests** (always pass `QT_QPA_PLATFORM=offscreen` in headless environments):
  ```bash
  QT_QPA_PLATFORM=offscreen pytest moduskript/tests/
  ```
- **Run a single desktop test file**:
  ```bash
  QT_QPA_PLATFORM=offscreen pytest moduskript/tests/test_formatBar.py
  ```
- **Regenerate Qt `.ui` / `.qrc` Python files** (only if editing `.ui` or `.qrc` files):
  ```bash
  make ui
  ```
- **Build `.deb` package** (outputs to `/home/ab/workspaces/moduskript/releases/`):
  ```bash
  ./package/create_deb.sh
  ```

### Web App — Backend (`/home/ab/workspaces/moduskript-web/server`)
- **Run backend tests**:
  ```bash
  cd /home/ab/workspaces/moduskript-web/server && uv run pytest
  ```
- **Run a single backend test file**:
  ```bash
  cd /home/ab/workspaces/moduskript-web/server && uv run pytest tests/test_api_projects.py
  ```

### Web App — Frontend (`/home/ab/workspaces/moduskript-web/web`)
- **Required verification order** (`check -> test -> build`):
  ```bash
  cd /home/ab/workspaces/moduskript-web/web && npm run check && npm test && npm run build
  ```
- **Run a single Vitest unit test**:
  ```bash
  cd /home/ab/workspaces/moduskript-web/web && npx vitest run src/lib/editor/readable-markdown.test.ts
  ```
- **Run Playwright E2E tests** (requires `npm run build` first because Playwright launches `uvicorn` serving `../web/build`):
  ```bash
  cd /home/ab/workspaces/moduskript-web/web && npm run build && npx playwright test
  ```

---

## Architecture & Operational Gotchas

- **Commingled Project Storage & Sync**:
  - Desktop (`moduskript/web_server.py`, `moduskript/load_save/version_1.py`) and Web (`server/app/projects.py`, `server/msklib/`) read and write the same project directories on disk.
  - Projects require both `<Project>/MANUSKRIPT` (inside the folder) and `<Project>.msk` (sibling file) for Desktop and Web discovery. `WebServerConfig.ensureProjectMarkers()` bridges these automatically.
  - Multi-board whiteboards are stored in `<Project>/whiteboards.json` and shared between `moduskript/ui/views/whiteboardView.py` (Desktop) and `web/src/routes/whiteboard/+page.svelte` (Web).
  - Shared AI settings (`ai_settings.json`, `ai_models_cache.json`) and SQLite chat histories (`chats.db`) live in `<data_dir>/ai/`, shared between `moduskript/ai/config.py` and `server/app/routes_ai.py`.
- **Desktop Unhandled Exceptions Exit Immediately**:
  - `moduskript/logging.py` installs `sys.excepthook = handle_uncaught_exception`, which logs `CRITICAL` to `~/.local/share/manuskript/manuskript/logs/` and calls `sys.exit(1)`.
  - Never call `.isRunning()` or other Qt methods on a `QThread` / `QObject` wrapper after `deleteLater()` without clearing the reference and guarding against `RuntimeError` (deleted C/C++ wrapper).
- **Desktop Lazy Settings Window (`mainWindow().sw`)**:
  - `MainWindow.sw` is `None` until the user opens `Edit -> Settings`. Any live editor or UI update (e.g., `FormatBar`) must directly update `textEditView` widgets via `loadFontSettings()` rather than relying on `mainWindow().sw.updateAllWidgets()`.
- **Desktop Highlighter Block Format Rules**:
  - `BasicHighlighter.highlightBlockBefore` applies `self._defaultBlockFormat` on rehighlight. Per-paragraph block format overrides (such as alignment) must be stored in `QTextBlockFormat.UserProperty` and preserved in `highlightBlockBefore`.
- **Web Static Build**:
  - The FastAPI server serves the compiled SvelteKit static bundle from `/home/ab/workspaces/moduskript-web/web/build`. Always run `npm run build` in `web/` after modifying frontend files so the live server and Desktop-managed Web server serve the updated UI.
