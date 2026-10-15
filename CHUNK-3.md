# Chunk 3: Outline Parity (Desktop & Web)

**Status:** ⬜ Pending

## Goal
Bring the Desktop App's Outline view and metadata inspector to full parity with the Web App's Outline capabilities:
1. Preserve `associatedNotes` metadata across Desktop load/save (`enums.py` & `version_1.py`).
2. Support **Tree View** and **Table View** switching in the Desktop Outline tab with column visibility picker and sorting.
3. Add the **+ Add (Folder, Chapter, Scene, Note)** workflow where Chapters are `.md` items (`label == Chapter`) and Scenes created under/after a Chapter automatically place and visually indent beneath their Chapter (`siblingDepthOffset`).
4. Remove the inline `notes` column from the Outline table view and add the structured **Associated Notes** manager (add, edit, delete multiple titled notes per chapter/scene) in the Inspector (`metadataView.py`).

---

## Scope & Files to Modify / Create

### 1. Model & Enum Compatibility
- **`manuskript/enums.py`**:
  - Add `associatedNotes` to `class Outline(IntEnum)` so Desktop Manuskript reads and writes `associatedNotes:` in `.md` and `folder.txt` MMD headers without stripping them.
- **`manuskript/settings.py`**:
  - Update default `outlineViewColumns` to match Web Outline columns (`title`, `wordCount`, `label`, `status`, `compile`, `POV`, `summarySentence`, `goal`, `goalPercentage`), ensuring `notes` is not shown inline in the table.

### 2. Chapter/Scene Hierarchy & Placement Logic (`manuskript/functions/outlineHelpers.py` & `outlineBasics.py`)
- Implement Python equivalents of the Web App's `isChapterItem`, `resolvePlacementForAdd`, and `siblingDepthOffset`:
  - **Add Chapter**: Creates a `.md` item with the `Chapter` label (creating or finding the `"Chapter"` label in `mdlLabels`) and book icon.
  - **Add Scene**: Places the new `.md` scene right after the active Chapter (and its existing scenes, before the next Chapter).
  - **Visual Indentation (`outlineTitleDelegate` / `outlineView`)**: Visually indents scene rows under a preceding `.md` Chapter so the hierarchy looks identical in Desktop and Web.

### 3. Associated Notes UI in Desktop Inspector (`manuskript/ui/views/metadataView.py`)
- Add an **Associated Notes** section to `metadataView` (used in both the Outline tab and the Editor/Redac tab):
  - Displays the list of `associatedNotes` (JSON array `[{"id": "...", "title": "...", "text": "..."}]`) for the selected Folder, Chapter, or Scene.
  - `+ New Note` button/dialog, inline title/body editing, and delete button, synced directly to `Outline.associatedNotes` on the model.

### 4. Outline Toolbar & Tree/Table Toggle (`manuskript/mainWindow.py` & `manuskript/ui/views/outlineView.py`)
- Add toolbar controls above the Outline view:
  - **Tree / Table** view mode toggle.
  - **Columns** visibility menu.
  - **+ Add** menu (`New Folder`, `New Chapter`, `New Scene`, `Add Note`).

---

## Verification & Checkpoint Gate
1. **Desktop & Cross-App Tests (`pytest`)**:
   - Test creating Chapters, Scenes, and Associated Notes in Desktop, saving the project, and verifying `msklib` (Web) reads the exact same `associatedNotes` and chapter structure.
   - Test creating Associated Notes in Web, opening in Desktop, and verifying lossless round-trip.
2. **Checkpoint**: Pause and review test results with user before proceeding to Chunk 4.
