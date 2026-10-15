# Chunk 2: Desktop Native Whiteboard (`QGraphicsView`) & Project Load/Save Parity

**Status:** ⬜ Pending

## Goal
Build a native PyQt5 Whiteboard in the Desktop App (`manuskript/ui/views/whiteboardView.py`) with full feature and file parity to the Web App's whiteboard, reading and writing the same `<project>/whiteboards.json` file (including multiple boards per project, shapes, notes, 4 connector line types, hover/toggle notes, and shape/line colors).

---

## Scope & Files to Modify / Create

### 1. Project Load/Save Support (`/home/ab/workspaces/manuskript-ai/manuskript/`)
- **`manuskript/load_save/version_1.py`**:
  - On `loadProject()`: Read `whiteboards.json` from the project folder (or zip) and load it into `mw.whiteboardView.loadData(...)`.
  - On `saveProject()`: Serialize `mw.whiteboardView.saveData()` to `whiteboards.json` in `files` so `version_1.py` writes it to `<project>/whiteboards.json` and keeps it in `cache` (preventing phantom file deletion on save).

### 2. Native PyQt5 Whiteboard Widget (`manuskript/ui/views/whiteboardView.py`)
- **`WhiteboardView(QWidget)`**:
  - **Centered Top Toolbar**:
    - **Board Selector**: `QComboBox` to switch between named whiteboards + `+ New Board`, `Rename`, `Delete Board` buttons.
    - **Add Node Menu**: Rectangle, Circle, Triangle, Arrow, Note (shapes start with blank label `""` by default).
    - **Shape Type Switcher**: Change selected shape between Rectangle, Circle, Triangle, Arrow.
    - **Line Style & Connection Mode Button**: Live icon preview of `solid`, `dash`, `dot`, `solid-dashed`; selecting a style updates the selected edge and activates Connection Mode (click Node 1 -> Node 2 or drag between handles).
    - **Color Picker**: Palette menu + `QColorDialog` to color the selected shape, note, or connector edge.
    - **Show All Notes Toggle**: Toggles persistent note popovers above all shapes that have notes.
    - **Delete Selected**, **Zoom In**, **Zoom Out**, **Fit View**.
    - **Inline Inspector Bar**: When a shape is selected, displays `Label` and `Note` `QLineEdit` inputs in the toolbar.
  - **Canvas (`QGraphicsScene` + `QGraphicsView`)**:
    - Dot-grid background matching the active Appearance colour scheme.
    - **`ShapeGraphicsItem`**: Renders Rectangle, Circle, Triangle, or Arrow in `data.color` (or theme accent), left/right connection handles, double-click inline label editing, top-right note badge icon, and hover/force-visible note popover card.
    - **`NoteGraphicsItem`**: Sticky note card with multi-line editable text and customizable color.
    - **`EdgeGraphicsItem`**: Cubic Bezier curve (`QPainterPath`) connecting source and target nodes with `Qt.SolidLine`, `Qt.DashLine`, `Qt.DotLine`, or `Qt.DashDotLine` (`solid-dashed`) and custom stroke color.

### 3. MainWindow Integration (`manuskript/mainWindow.py`)
- Add **Board (Whiteboard)** to the main left navigation (`lstTabs` / `tabMain`) so writers can switch to the Whiteboard just like in the Web App.
- Connect any whiteboard modification to `mw.startTimerNoChanges()` / `projectDirty = True` for automatic saving.

---

## Verification & Checkpoint Gate
1. **Desktop Tests (`pytest`)**:
   - Unit and widget tests for `WhiteboardView`: creating multiple boards, adding shapes/notes/edges, changing line styles and colors, serializing to `whiteboards.json`, and round-trip loading/saving a project via `version_1.py` + cross-compatibility test with `msklib`.
2. **Checkpoint**: Pause and review test results and screenshots with user before proceeding to Chunk 3.
