# Chunk 5: Desktop Settings Workflow Revamp

**Status:** ✅ Complete (Tests Passing: 80 Desktop pytest)

## Goal
Overhaul the unintuitive, cramped Manuskript `settingsWindow` into a clean, modern, and intuitive Settings experience that is easy to navigate, supports live search/filtering, groups options logically, and applies theme/editor changes smoothly.

---

## Problems with Base Manuskript Settings (Being Fixed)
1. **Cramped Sidebar**: Fixed 140px icon-above-text list where labels clip and icons are inconsistent.
2. **Scattered & Confusing Options**: View settings have cryptic matrix dropdowns ("Tree Icon / Text / Background / InfoFolder / InfoText"); Revisions have confusing inverted math spinboxes; Editor settings are split between `FormatBar`, `Views -> Text Editor`, and `Appearance`.
3. **Forced Restart for Themes**: Changing a colour scheme in `Appearance` required a full app restart instead of live re-styling.
4. **No Search or Reset**: Hard to find specific settings or restore sensible defaults.

---

## Scope & Files to Modify / Create

### 1. Modernized Settings Shell (`manuskript/settingsWindow.py` & `manuskript/ui/settings_ui.py`)
- **Left Sidebar Navigation (210px wide)**:
  - Add a **Search settings...** (`QLineEdit`) filter bar at the top of the sidebar that filters settings pages and highlights matching controls.
  - Replace centered stacked icons with clean, left-aligned horizontal icon + label items (`40px` row height, modern selection pill styling):
    1. **Appearance & Theme** (default landing page — 32 colour schemes, live apply, density, UI font & size, accent colour)
    2. **Writing & Editor** (Readable vs. MD Code mode, editor font, line/paragraph spacing, tab width in spaces, focus mode, typewriter mode, cursor & max width)
    3. **General & Saving** (Language, autosave toggles & intervals, revision history with simple presets: *Light / Standard / Frequent / Custom*, `.msk` folder vs. zip format)
    4. **Views & Corkboard** (Clean card-based layout for Outline columns, Tree badge info, Corkboard style & background)
    5. **Labels & Statuses** (Side-by-side or tabbed management of project Labels with color swatches and Statuses)
    6. **Fullscreen** (Fullscreen theme & auto-hide panels)
    7. **AI Assistant** (`AISettingsPage` — Provider, Server URL / API Key, Model, Context sources, Role prompts)
    8. **Web Server & Sync** *(Hooked up in Chunk 6)* (Start/Stop web server, Start on launch, Run in background on close, Port, Shared Projects Folder)

### 2. Live Theme Application (`manuskript/appearance/`)
- Enhance `AppearanceSettingsPage` so selecting any of the 32 colour schemes or changing UI font/density/accent colour **applies live immediately** to the running `qApp` and `MainWindow` (via `Appearance.apply(qApp)` + refreshing editor/corkboard palettes), while keeping the optional "Restart" button only as a fallback.

---

## Verification & Checkpoint Gate
1. **Desktop Tests (`pytest`)**:
   - Update and expand `manuskript/tests/test_settingsWindow.py` to test all sidebar pages, search filter bar, live theme switching, revision presets, and editor settings sync with `FormatBar`.
2. **Checkpoint**: Pause and review test results and visual screenshots of the new Settings window with user before proceeding to Chunk 6.
