# Moduskript (Desktop Edition)

**Moduskript** is an open-source, AI-assisted novel and long-form writing studio for Linux/desktop, built as an enhanced fork of [Manuskript](https://github.com/olivierkes/manuskript) (`0.17.0`) and paired with the companion **Moduskript Web App** (`manuskript-ai-web`).

Both the Desktop App and the Web App read and write the **exact same plain-text Manuskript project folders (`.msk` / `MANUSKRIPT`)**, allowing you to write seamlessly on your desktop workstation, tablet, or phone.

---

## Key Features

### 1. Writing Space & Live Readable Markdown Mode
- **Readable vs. MD Code Toggle**: Switch live between **MD Code** (raw Markdown syntax visible) and **Readable Mode** (collapses raw `#`, `**`, `*`, `~~`, `>` tokens on inactive lines while rendering headings, bold, italic, strikethrough, and blockquotes cleanly; clicking any line reveals its Markdown syntax immediately).
- **Two-Row Formatting Bar (`FormatBar`)**:
  - Paragraph style switcher (*Body text, Heading 1–4, Quote, Bullet list, Numbered list*), font family, font size, Bold, Italic, Strikethrough, and **Readable / MD Code** toggle.
  - Alignment, line spacing, paragraph spacing, first-line indent, and **Tab width in spaces**.
- **Focus & Typewriter Modes**: Sentence, line, or paragraph focus dimming and centered typewriter scrolling.

### 2. Native Multi-Board Whiteboard (`Board` Tab)
- **Shared Project Persistence (`<project>/whiteboards.json`)**: Whiteboards are saved directly inside the project folder and shared byte-for-byte between Desktop and Web.
- **Multiple Whiteboards per Project**: Create, switch, rename, and delete multiple named boards (e.g., *Main Board*, *Subplot Map*, *Relationship Web*).
- **Shapes, Sticky Notes & Unobtrusive Hover Notes**:
  - Add **Rectangle**, **Circle**, **Triangle**, **Arrow**, and **Sticky Note** nodes.
  - Double-click any node or use the centered toolbar inspector to edit labels and attach notes.
  - Hover over a shape to preview its note popover, or click **Show notes** in the toolbar to display all shape notes simultaneously.
- **4 Connector Line Styles & Custom Colors**:
  - Connect nodes with **Solid**, **Dash**, **Dot**, or **Solid dashed** Bezier lines.
  - Customize colors for shapes, sticky notes, and connector lines from a 11-color theme palette or custom color picker.

### 3. Modernized Outline & Associated Notes
- **Tree & Table View Toggle**: Switch between a clean hierarchical Tree view and a multi-column Table view in the Outline tab.
- **Chapter & Indented Scene Workflow (`+ Add` Menu)**:
  - Add **Folders**, **Chapters** (`.md` documents labeled `Chapter`), **Scenes** (automatically placed and visually indented beneath their Chapter), and **Associated Notes**.
- **Structured Associated Notes Inspector**: Attach multiple titled notes (`associatedNotes`) to any Chapter, Scene, or Folder in both the Outline detail panel and the Editor right-hand Inspector.

### 4. Built-in AI Assistant Dock (`AIDock`)
- **Local & Cloud LLM Support**:
  - **Local (`llama.cpp` / OpenAI-compatible server)** with configurable Server URL, Context Budget, Temperature, and Thinking Effort (`Off`, `low`, `medium`, `high`, `xhigh`).
  - **Cloud Providers**: OpenAI, Anthropic Claude, and Google Gemini.
- **Project-Aware Context Assembly**: Automatically feeds selected text, current scene text, scene summary/notes, POV character sheet, and book summary into the prompt within your token budget.
- **Role Personas**: *Co-author*, *Editor*, *Publisher*, and *Reader* with customizable system prompts.
- **Dock / Undock Toggle**: Float the AI Chat window anywhere on screen and snap it right back into the main window with the one-click **Dock / Undock** button.

### 5. 32 WCAG-Verified Colour Schemes & Revamped Settings
- **32 Built-in Colour Schemes**: 25 dark themes (defaulting to *Midnight*, plus *Obsidian OLED*, *Nord*, *Dracula*, *Gruvbox*, *Tokyo Night*, *Catppuccin*, *Rosé Pine*, *Everforest*, *Kanagawa*, etc.) and 6 light themes (*Paper*, *Sepia*, *Solarized Light*, *Catppuccin Latte*, etc.) plus *System*.
- **Live Theme Switching**: Selecting any scheme, accent colour, UI font (*Inter* bundled), or density (*Compact*, *Comfortable*, *Spacious*) applies **live immediately** without requiring an application restart.
- **Revamped Settings Window**: Wide 215px icon+label sidebar, live **Search settings...** filter bar, and one-click Revision History presets (*Standard*, *Frequent*, *Light*, *Custom*).

### 6. Integrated Web App Server & Background Mode
- **Launch Web App from Desktop**: Start/stop the companion FastAPI + SvelteKit Web Server and open it in your browser directly from **Tools → Launch Web App in Browser (`Ctrl+Shift+W`)**, the System Tray icon, or **Settings → Web Server & Sync**.
- **Start on Launch & Run in Background on Close**:
  - Enable *"Start web-app server automatically when Moduskript starts"*.
  - Enable *"Keep web-app server running in the background when the desktop app is closed"* so you can continue writing from your phone or browser even after closing the desktop window.
- **Commingled File Structure & Live Reload**: Projects in the shared directory (`/home/ab/workspaces/manuskript-ai-web/data/projects`) are automatically bridged (`.msk` ↔ `MANUSKRIPT`), protected by `.lock` markers during saves, and auto-reloaded when external Web edits are detected.

---

## Installation

### Option 1: Install the Compiled `.deb` Package (Ubuntu / Debian)
A pre-compiled `.deb` package is located in the `releases/` folder:

```bash
sudo apt update
sudo apt install ./releases/moduskript_0.17.0-moduskript1_all.deb
```

Once installed, launch **Moduskript** from your desktop application launcher or run:

```bash
moduskript
# or
manuskript
```

### Option 2: Run Directly from Source
Install the required system dependencies:

```bash
sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-lxml \
  python3-markdown python3-enchant python3-requests libqt5svg5 pandoc \
  python3-pytest
```

Run Moduskript from the repository root:

```bash
python3 bin/manuskript
```

---

## Building the `.deb` Package
To rebuild the `.deb` package into `releases/`:

```bash
./package/create_deb.sh
```

---

## Running Automated Tests
```bash
QT_QPA_PLATFORM=offscreen pytest manuskript/tests/
```

---

## Known Issues & Upcoming Refinements (Next Iteration)

1. **File Sync / Commingled Folder Selection**: Selecting a custom folder and clicking Sync shows `1 project synced` in Desktop, but if the user picks a `<Project>/` folder directly (or a parent folder instead of `<dataDir>/projects`), the Web Server looking at `MSK_DATA_DIR/projects` does not list it. In addition, the running Web Server needs to reload/point directly to the selected projects folder.
2. **Board Tab Icon in Desktop App**: The `Board` (Whiteboard) tab in the left navigation bar needs a dedicated, crisp icon.
3. **Web App Initial Login / Account Setup**: Creating a new login on the initial setup screen can crash/fail (e.g., when cookies/CSRF or DB path permissions conflict); the initial login/setup flow is being reworked to be seamless and resilient.
4. **Desktop Icon Overhaul**: The legacy Numix/system fallback icons across the Desktop App need a comprehensive overhaul with modern, consistent SVG icons (Lucide-style).
5. **Web App "More" Menu Overhaul**: The Web App `/more` menu needs a cleaner, desktop-parity layout organizing Project Management, Templates, Book Info/Summary, World, Plots, AI Settings, Appearance, and Security.
6. **Web App Parity for Title Properties, World Builder, and Plots**: Enhance and surface General/Title properties (`infos.txt` + `summary.txt`), World Builder (`world.opml`), and Plots (`plots.xml`) in the Web App so they match Desktop capabilities and navigation.
7. **Desktop Writer/Editor Toolbar (More Icons, Less Text)**: Replace text-heavy labels and buttons in `FormatBar` and the editor header with a clean, icon-led toolbar matching the Web App editor.
8. **Desktop Whiteboard UX & Drag-to-Connect Handles**: Replace text buttons on the Desktop Whiteboard toolbar with crisp icons, streamline node/canvas interactions, and enable **click-and-drag line connections directly from node handles** in addition to click-to-link.
9. **Desktop AI Chat Dock Header & Icon-Driven Controls**: Hide the redundant native dock title bar (`×` close and tiny float button), use clean icons for **Dock/Undock**, **New Chat**, **Delete Chat**, **Refresh Models**, and **Provider/Role** indicators across the AI Chat dock and other pages.

---

## License & Credits
- **License**: GNU General Public License v3.0 (`COPYING`).
- **Credits**: Forked from [Manuskript](https://github.com/olivierkes/manuskript) by Olivier Keshavjee and contributors; extended into **Moduskript** ([Schwitzz/Moduskript](https://github.com/Schwitzz/Moduskript)).
