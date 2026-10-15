# Chunk 1: Multi-Whiteboard Shared Storage & Shape/Line Color Options (Web + API)

**Status:** ✅ Complete (Tests Passing: 313 server pytest, 141 vitest, 0 svelte-check errors, 18 Playwright E2E)

## Goal
1. Move whiteboard persistence from browser-only `localStorage` into the shared project folder (`<project>/whiteboards.json`) via the FastAPI server and `msklib`, so both the Web App and Desktop App read and write the exact same whiteboards.
2. Add **multi-whiteboard support per project** (create, switch, rename, delete multiple named boards within a project).
3. Build **color customization** for shapes, sticky notes, and connector lines on the whiteboard.

---

## Scope & Files to Modify / Create

### 1. Server & `msklib` (`/home/ab/workspaces/manuskript-ai-web/server/`)
- **`msklib/project.py`**:
  - Ensure `whiteboards.json` in the project root is loaded and preserved during `Project.load()` and `Project.save()` (never deleted as a phantom file).
- **`app/api/whiteboards.py`** *(New router)*:
  - `GET /api/projects/{name}/whiteboards`: Returns the project's whiteboard collection (`{"active_board_id": str, "boards": [...]}`). If `whiteboards.json` does not exist yet, returns a default board (`id: "default"`, `name: "Main Board"`, `nodes: []`, `edges: []`, `viewport: {"x": 0, "y": 0, "zoom": 1}`, `show_all_notes: False`).
  - `PUT /api/projects/{name}/whiteboards`: Atomically saves the full whiteboard collection to `<project>/whiteboards.json` (respecting `.lock` via `open_project`).
- **`app/main.py` & `web/src/lib/api-types.ts`**:
  - Register the `whiteboards` router and regenerate/update the TypeScript OpenAPI types.

### 2. Web Whiteboard Color Palette & Multi-Board UI (`/home/ab/workspaces/manuskript-ai-web/web/`)
- **`web/src/lib/whiteboard/colors.ts`** *(New)*:
  - Define preset colors (`DEFAULT` / Theme Accent, `#ef4444` Red, `#f97316` Orange, `#eab308` Amber, `#22c55e` Emerald, `#14b8a6` Teal, `#3b82f6` Blue, `#6366f1` Indigo, `#a855f7` Purple, `#ec4899` Pink, `#64748b` Slate) + custom hex color support.
- **`web/src/routes/whiteboard/ShapeNode.svelte`**:
  - Support `data.color?: string` for the shape icon, border, selection glow, and subtle background tint.
- **`web/src/routes/whiteboard/NoteNode.svelte`**:
  - Support `data.color?: string` for sticky note card styling.
- **`web/src/routes/whiteboard/DashedEdge.svelte`**:
  - Support `data.color?: string` for the SVG `<path>` stroke color alongside `data.lineType`.
- **`web/src/routes/whiteboard/+page.svelte`**:
  - Load/save boards from `GET/PUT /api/projects/{name}/whiteboards` (with automatic one-time migration if legacy `localStorage` data exists for that project).
  - Add a **Board Switcher** in the toolbar: dropdown to switch between boards, `+ New Board`, `Rename`, and `Delete Board`.
  - Add a **Color Picker** button/popover in the toolbar to set the color of the currently selected shape, note, or connector line (and default color for new shapes/lines).

---

## Verification & Checkpoint Gate
1. **Server Tests (`pytest`)**:
   - Test `GET /api/projects/{name}/whiteboards` default state, `PUT` round-trip persistence to `<project>/whiteboards.json`, multiple boards CRUD, and `msklib` round-trip preservation when saving outline/characters.
2. **Web Tests (`vitest` + `svelte-check` + `playwright`)**:
   - Unit test color definitions and multi-board state helpers.
   - E2E test creating a second whiteboard, adding colored shapes and colored dashed/dotted lines, reloading the page, and verifying persistence from the server.
3. **Checkpoint**: Pause and review test results with user before proceeding to Chunk 2.
