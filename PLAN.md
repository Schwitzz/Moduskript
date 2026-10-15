# Moduskript (manuskript-ai & manuskript-ai-web) — Master Implementation Plan

## Overview & Vision
This plan establishes full feature parity between the PyQt5 Desktop Application (`/home/ab/workspaces/manuskript-ai/manuskript`) and the Web Application (`/home/ab/workspaces/manuskript-ai-web`), integrates the FastAPI/SvelteKit web server directly into the desktop workflow with a shared file structure and background execution, upgrades the Whiteboard with multi-board project storage and shape/line color customization, modernizes the desktop Settings experience, cleans up test artifacts, builds a release `.deb` package, updates documentation, and prepares for final sync to `Schwitzz/Moduskript`.

---

## Architectural Decisions (Confirmed)
1. **Repository Structure**: Keep `/home/ab/workspaces/manuskript-ai/manuskript` (Desktop) and `/home/ab/workspaces/manuskript-ai-web` (Web) as separate repositories for now while integrating their runtime and shared project storage.
2. **Shared Multi-Whiteboard Storage (`whiteboards.json`)**:
   - Store whiteboards inside each project folder (`<project>/whiteboards.json`) so both Desktop and Web read/write the exact same boards.
   - Support **multiple named whiteboards per project** (create, switch, rename, delete boards), migrating any legacy browser `localStorage` whiteboard automatically.
3. **Desktop Whiteboard Implementation**:
   - Native PyQt5 `QGraphicsView` / `QGraphicsScene` canvas (`manuskript/ui/views/whiteboardView.py`) with full parity to the web whiteboard: Rectangle, Circle, Triangle, Arrow, and Note nodes, editable labels, hover/toggle notes, 4 connector line types (`solid`, `dash`, `dot`, `solid-dashed`), custom colors for shapes and lines, and zoom/pan/fit controls.
4. **Web Server Integration & Background Execution**:
   - Manage the web server from the Desktop App (launch in browser, start/stop server, start on app launch, run in background when window closes via `QSystemTrayIcon` + background process management).
   - Commingle project storage so opening/saving a project in Desktop or Web operates on the shared project directory (with file-watcher / reload awareness and `.lock` safety).

---

## Logical Execution Flow & Checkpoints (`CHUNK-1.md` .. `CHUNK-8.md`)

We will execute this plan iteratively, one chunk at a time, validating tests at each checkpoint before proceeding:

| Chunk | File | Scope | Key Deliverables |
| :--- | :--- | :--- | :--- |
| **Chunk 1** | `CHUNK-1.md` | **Multi-Whiteboard Shared Storage & Shape/Line Colors (Web + API + msklib)** | ✅ **Complete** — Project-level `whiteboards.json` API (`GET/PUT`), multiple boards per project UI (create/rename/delete/switch), color pickers & palette for shapes, notes, and connector lines in Web Whiteboard. |
| **Chunk 2** | `CHUNK-2.md` | **Desktop Native Whiteboard (`QGraphicsView`) & Project Load/Save Parity** | ✅ **Complete** — Native PyQt5 Whiteboard tab in Desktop App reading/writing `whiteboards.json`, multi-board selector, shapes/notes/4 line styles, color pickers, hover & "Show notes" toggle, zoom/pan. |
| **Chunk 3** | `CHUNK-3.md` | **Outline Parity (Desktop & Web)** | ✅ **Complete** — Desktop `associatedNotes` enum/MMD support, Tree & Table view toggle in Desktop Outline, "+ Folder / Chapter / Scene / Note" workflow, chapter-under-scene visual indentation (`siblingDepthOffset`), Associated Notes manager in `metadataView` & `basicItemView`, and removal of inline `notes` column from Desktop Outline table. |
| **Chunk 4** | `CHUNK-4.md` | **Writing Space Parity — Markdown Code Visible vs. Readable Toggle & AI Dock Re-dock Fix (Desktop & Web)** | ✅ **Complete** — Toggle button in both Web Editor (CodeMirror 6 live-preview widget decoration) and Desktop Editor (`MDEditView` / `MarkdownHighlighter` + `FormatBar`) to switch between **MD Code Visible** and **Readable Mode**, plus a clear **Dock / Undock** button in the Desktop `AIDock` header so undocked AI Chat windows can be re-docked with one click. |
| **Chunk 5** | `CHUNK-5.md` | **Desktop Settings Workflow Revamp** | ✅ **Complete** — Modernized, intuitive `settingsWindow` with a wider icon+label sidebar, live search/filter bar, card-based sections, live theme switching (without requiring a full manual restart), revision quick presets, Readable Mode sync, and clean defaults. |
| **Chunk 6** | `CHUNK-6.md` | **Web App Integration, Commingled File Structure & Background Server** | ✅ **Complete** — `manuskript/web_server.py` manager + System Tray (`QSystemTrayIcon`), Tools menu "Launch Web App", Settings controls ("Start web server on launch", "Keep server running in background when closed", shared Projects Directory, port config), `.lock` sync safety, and live disk change detection. |
| **Chunk 7** | `CHUNK-7.md` | **Moduskript Rebranding, Test Cleanup, `.deb` Release Packaging & Documentation (`README.md`)** | Revise marketing & UI branding from **Manuskript** to **Moduskript** across Desktop & Web (window titles, About dialog, login/shell headers, PWA manifest, `.desktop` launcher, FastAPI title, and `.deb` package metadata while preserving `MANUSKRIPT` / `.msk` file-format compatibility), clean up temporary test/probe scripts, verify all test suites pass, build `.deb` into `releases/`, and update both `README.md` files. |
| **Chunk 8** | `CHUNK-8.md` | **Final User Validation & Git Sync to `Schwitzz/Moduskript`** | After your manual testing and sign-off, stage, commit, configure remotes, and push cleanly to `Schwitzz/Moduskript`. |

---

## Detailed Feature Breakdown by Requirement

### 1. Parity of Whiteboard, Outline, and Writing Space
- **Whiteboard (Chunk 1 & Chunk 2)**:
  - **Shared file format**: `whiteboards.json` stored in the project folder (`{"activeBoardId": "...", "boards": [{"id": "...", "name": "Main Board", "nodes": [...], "edges": [...], "viewport": {...}, "showAllNotes": false}]}`).
  - **Multiple Whiteboards**: Dropdown selector in the centered whiteboard toolbar to switch boards, `+ New Board`, `Rename Board`, and `Delete Board`.
  - **Color Options (Requirement 5)**: Palette of theme-harmonious colors (plus custom color picker) for shapes (`data.color`), notes (`data.color`), and connector lines (`edge.data.color`).
  - **Desktop Canvas**: Built with `QGraphicsView` and custom `QGraphicsItem` subclasses (`ShapeGraphicsItem`, `NoteGraphicsItem`, `EdgeGraphicsItem`) supporting drag, inline double-click label editing, hover note popovers, "Show All Notes" toggle, 4 line dash styles, and interactive connection mode.
- **Outline (Chunk 3)**:
  - Add `Outline.associatedNotes` to desktop `manuskript/enums.py` so `associatedNotes` in MMD headers are preserved byte-for-byte on Desktop load/save just like `msklib`.
  - Add **Tree / Table** view switcher and **+ Add (Folder, Chapter, Scene, Note)** toolbar to Desktop Outline.
  - Visually indent scenes beneath `.md` chapters (`label == Chapter`) in both Tree and Table views.
  - Remove the cluttered `Notes` column from the Outline table defaults and add the structured **Associated Notes** list/editor in the bottom/side inspector (`metadataView`).
- **Writing Space — MD Code Visible vs. Readable Toggle (Chunk 4)**:
  - **Desktop (`FormatBar` & `MDEditView` / `MarkdownHighlighter`)**: Add a "Readable / MD Code" toggle button (`btnReadableMode`) in `FormatBar`. When in **Readable Mode**, markdown formatting tokens (`#`, `**`, `*`, `~~`, `>`, `[text](url)`) on non-active blocks are collapsed/hidden (tiny/transparent font format) while keeping the rendered styles (large headings, bold, italic, strikethrough, blockquotes) crisp and readable; clicking a line reveals its raw markdown for editing, or toggling **MD Code Visible** shows all syntax tokens everywhere.
  - **Web (`web/src/routes/write/+page.svelte`)**: Add a matching **Readable / MD Code** toggle button in the Write toolbar using a CodeMirror 6 `StateField` / `ViewPlugin` decoration that hides markdown syntax markers (`# `, `**`, `*`, `~~`, `` ` ``, `[url]`) on lines outside the cursor selection in Readable Mode, and reveals all raw markdown symbols in MD Code Mode.

### 2. Revamp "Settings" Workflow (Chunk 5)
- Redesign `manuskript/settingsWindow.py` & `settings_ui`:
  - Replace the cramped 140px icon-only vertical menu with a modern, clear 210px navigation sidebar with crisp icons, readable category titles, and a **Search settings...** filter box at the top.
  - Reorganize settings into logical, user-friendly pages:
    1. **Appearance & Theme** (32 colour schemes with visual previews, live-apply without forcing a cold restart, UI density, font family & size, accent colour).
    2. **Editor & Writing** (Readable vs. MD Code default, typography, line/paragraph spacing, tab width in spaces, focus & typewriter mode, spellcheck).
    3. **Project & Saving** (Autosave intervals, revision history rules simplified with presets, default shared projects folder, `.msk` folder vs. zip format).
    4. **Views & Corkboard** (Simplified Tree, Outline Table columns, and Corkboard card appearance).
    5. **Labels & Statuses** (Clean inline color & name management).
    6. **AI Assistant** (Providers, Local llama.cpp / OpenAI / Anthropic / Gemini keys, context toggles, role prompts).
    7. **Web Server & Sync** (Server status badge, Start/Stop button, Open in Browser button, Port setting, "Start web server automatically on launch", "Keep web server running in background when app is closed", Shared Projects Directory path).

### 3 & 4. Web App Integration, Commingled File Structure & Background Server (Chunk 6)
- **Commingled File Structure**:
  - Configure a unified **Projects Directory** (defaulting to `/home/ab/workspaces/manuskript-ai-web/data/projects` or user-configured path in `QSettings` synced with `MSK_DATA_DIR`).
  - When a project is opened or created in Desktop Manuskript inside the shared directory, or when Desktop opens a `.msk` project, ensure the folder structure (`<Name>/MANUSKRIPT`, `outline/`, `characters/`, `whiteboards.json`, etc.) is immediately visible to the Web Server.
  - Add a lightweight `QFileSystemWatcher` / mtime check in Desktop Manuskript so when the Web App saves changes to the open project, Desktop prompts or auto-reloads cleanly (and respects `.lock` via `synclock` conventions).
- **Integrated Web Server Manager (`manuskript/web_server.py`)**:
  - Controls the `uvicorn` server process from `/home/ab/workspaces/manuskript-ai-web/server` (serving the built SvelteKit static frontend from `web/build`).
  - Toolbar & Tools Menu actions: **Launch Web App in Browser**, **Start/Stop Web Server**.
  - **Start on Launch**: If enabled in Settings, automatically starts the web server when Desktop Manuskript starts.
  - **Run in Background on Close**:
    - Adds a `QSystemTrayIcon` with context menu (*Open Moduskript*, *Open Web App in Browser*, *Web Server: Running (Port 8770)*, *Stop Web Server*, *Quit Completely*).
    - If "Keep web server running in background when closed" is enabled, closing the main window either minimizes to tray or detaches the server process (`start_new_session=True` with PID tracking in `~/.local/share/manuskript/web_server.pid`) so the web app remains accessible even after the GUI exits.

### 5. Whiteboard Shape & Line Color Options (Chunk 1 & Chunk 2)
- Curated color palette (Default/Theme Accent, Red, Orange, Amber, Emerald, Teal, Blue, Indigo, Purple, Pink, Slate) + custom hex color picker.
- Applies to:
  - **Shapes**: Stroke & subtle fill tint (`color-mix` on web, `QColor` with alpha on desktop).
  - **Notes**: Sticky note card background/border tint.
  - **Connector Lines**: Stroke color on `DashedEdge.svelte` (Web) and `EdgeGraphicsItem` (Desktop) across all 4 line types (`solid`, `dash`, `dot`, `solid-dashed`).

### 6, 7, 8, 9. Moduskript Rebranding, Cleanup, Packaging, Documentation & Git Sync (Chunk 7 & Chunk 8)
- **Revise Marketing & Branding from Manuskript to Moduskript**:
  - Update user-facing branding, window titles, About dialog, Welcome screen, system tray labels, `.desktop` launcher (`Name=Moduskript`), `.deb` control metadata (`Package: moduskript`, `Provides/Replaces/Conflicts: manuskript`), Web App login/header/PWA `manifest.webmanifest`, and FastAPI title to **Moduskript** (while preserving the internal `MANUSKRIPT` marker file and `.msk` extension so existing projects remain 100% compatible).
- **Clean up test files**: Remove temporary ad-hoc scripts and logs in `/home/ab/workspaces/manuskript-ai/logs/` (preserving any reusable packaging script in `package/`), clean up stray `.pytest_cache` / `__pycache__` / temporary test artifacts.
- **Compile `.deb`**: Update `package/create_deb.sh` (and build helper) to package the desktop app cleanly and output the `.deb` into `/home/ab/workspaces/manuskript-ai/manuskript/releases/` (and `/home/ab/workspaces/manuskript-ai/releases/`).
- **Revise `README.md`s**: Rewrite both `/home/ab/workspaces/manuskript-ai/manuskript/README.md` and `/home/ab/workspaces/manuskript-ai-web/README.md` with current features, architecture, screenshots from `screens/`, installation (`.deb`, from source, Docker), AI setup, Web Server integration, and usage instructions.
- **Git Sync**: After your testing and confirmation, commit changes and push to `Schwitzz/Moduskript`.
