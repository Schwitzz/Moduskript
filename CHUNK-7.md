# Chunk 7: Test Cleanup, `.deb` Release Packaging & Documentation (`README.md`)

**Status:** ⬜ Pending

## Goal
1. Clean up all temporary test scripts, ad-hoc patch files, and log artifacts across the workspace while keeping all legitimate automated test suites green.
2. Compile the Desktop App into a `.deb` package and place it in `releases/`.
3. Revise both `README.md` files (`/home/ab/workspaces/manuskript-ai/manuskript/README.md` and `/home/ab/workspaces/manuskript-ai-web/README.md`) to accurately reflect the current state, features, architecture, screenshots, and installation instructions.

---

## Scope & Tasks

### 1. Clean Up Temporary Test & Probe Files
- Remove the ad-hoc scratch/probe scripts and logs in `/home/ab/workspaces/manuskript-ai/logs/` (`patch_*.py`, `probe_*.py`, `shot_*.py`, `run*.log`, `t_*.txt`, etc.), moving the improved `.deb` build logic into `/home/ab/workspaces/manuskript-ai/manuskript/package/build_deb.sh`.
- Remove temporary `.pytest_cache`, `__pycache__`, and any leftover temporary build directories.
- Run the full test suites in both repositories to verify everything is clean and passing:
  - Desktop: `pytest` in `/home/ab/workspaces/manuskript-ai/manuskript`
  - Web Server: `uv run pytest` in `/home/ab/workspaces/manuskript-ai-web/server`
  - Web Frontend: `npm run check && npm test && npx playwright test` in `/home/ab/workspaces/manuskript-ai-web/web`

### 2. Compile Desktop App into `.deb` in `releases/`
- Update `/home/ab/workspaces/manuskript-ai/manuskript/package/create_deb.sh` (and `package/build_deb.sh`) to:
  - Package the desktop application with all new modules (`ai`, `appearance`, `whiteboardView`, `web_server`, updated UI and icons).
  - Output the compiled `.deb` package directly into `/home/ab/workspaces/manuskript-ai/manuskript/releases/` (and copy to `/home/ab/workspaces/manuskript-ai/releases/`).
  - Verify package metadata, dependencies, permissions, and contents with `dpkg-deb -I` and `dpkg-deb -c`.

### 3. Revise Both `README.md` Files
- **Desktop `README.md` (`/home/ab/workspaces/manuskript-ai/manuskript/README.md`)**:
  - Introduce **Moduskript** (fork of Manuskript enhanced with AI Assistant, 32-Theme Appearance Engine, Native Multi-Board Whiteboard, Modernized Outline & Readable Markdown Editor, Revamped Settings, and Integrated Web Server).
  - Include screenshots from `screens/` (`ALL-SCHEMES.png`, `formatbar-midnight.png`, etc.).
  - Document installation via the compiled `.deb` in `releases/`, running from source, configuring Local (`llama.cpp`) and Cloud AI providers, and launching/syncing with the integrated Web App.
- **Web `README.md` (`/home/ab/workspaces/manuskript-ai-web/README.md`)**:
  - Document the full feature set: Write editor (with Readable / MD Code toggle, typewriter & focus modes, 32 themes), Outline (Tree & Table views, drag-and-drop, chapters & indented scenes, associated notes), Multi-Board Whiteboard (shapes, sticky notes, 4 line styles, custom colors, hover/toggle notes), Corkboard, Characters, Plots, World, Project Templates, and Streaming AI Assistant.
  - Document commingled file storage with the Desktop App, Docker deployment, local development, and test commands.

---

## Verification & Checkpoint Gate
1. Confirm `.deb` package is built in `releases/` and inspects cleanly.
2. Confirm all Desktop and Web automated tests pass with zero stray test artifacts.
3. **Checkpoint**: Pause for your full manual testing and validation before Chunk 8 (Git commit & sync to `Schwitzz/Moduskript`).
