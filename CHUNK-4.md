# Chunk 4: Writing Space Parity — Markdown Code Visible vs. Readable Toggle & AI Dock Re-Dock Fix (Desktop & Web)

**Status:** ⬜ Pending

## Goal
1. Implement a live toggle in both the **Web App Writing Space** and the **Desktop App Writing Space** to switch between:
   - **MD Code Visible Mode**: Shows all raw Markdown syntax characters (`#`, `**`, `*`, `~~`, `>`, `- `, `[text](url)`) inline with syntax highlighting.
   - **Readable Mode (Live Clean Preview)**: Hides/collapses Markdown formatting tokens on lines outside the active cursor block while rendering headings, bold, italic, strikethrough, blockquotes, and lists cleanly—allowing the writer to read and edit prose without visual markdown clutter, and automatically revealing a line's raw tokens when the cursor moves onto that line.
2. **Fix Desktop AI Chat Re-Docking (`manuskript/ai/dock.py`)**:
   - Currently, when `AIDock` (`QDockWidget`) is undocked (floating), Qt's custom dock stylesheet (`style.dockSS()`) and Linux window managers give no obvious button to re-dock it back into the main window.
   - Add an explicit, always-visible **Dock / Float** button (`btnDockToggle`) in the top bar of `AIDock` (plus `topLevelChanged` signal sync) that toggles `self.setFloating(not self.isFloating())` and re-attaches the dock to `Qt.RightDockWidgetArea` when clicked.

---

## Scope & Files to Modify / Create

### 1. Web App Writing Space (`/home/ab/workspaces/manuskript-ai-web/web/`)
- **`web/src/lib/editor/readable-markdown.ts`** *(New CodeMirror 6 extension)*:
  - Uses `@codemirror/language` (`syntaxTree`) and `Decoration.replace({})` / `Decoration.mark({})` inside a `ViewPlugin`.
  - When `readableMode` is enabled:
    - For any line **not** containing the primary cursor/selection, hides `HeaderMark` (`#`), `EmphasisMark` (`*`, `_`, `**`), `StrikethroughMark` (`~~`), `QuoteMark` (`>`), and `CodeMark` (`` ` ``), while applying clean CSS classes for Heading 1–4 sizes, bold, italic, strikethrough, and blockquotes.
    - When the cursor enters a line, the raw Markdown tokens on that line immediately reappear so editing is natural and byte-exact.
  - When `readableMode` is disabled (**MD Code Visible**):
    - All raw Markdown tokens remain visible across the entire document.
- **`web/src/routes/write/+page.svelte`**:
  - Add a clear toolbar toggle button (**MD Code / Readable**) with icon (`Code` / `BookOpen`) and tooltip (`"Toggle Markdown code visible or readable mode"`), persisting the user's preference in `localStorage`.

### 2. Desktop App Writing Space (`/home/ab/workspaces/manuskript-ai/manuskript/`)
- **`manuskript/ui/highlighters/markdownHighlighter.py` & `manuskript/ui/views/MDEditView.py`**:
  - Add `readableMode` support (backed by `settings.textEditor["readableMode"]`, defaulting to `False` or user preference).
  - In `MarkdownHighlighter.applyFormattingForToken()`:
    - When `readableMode` is active and `self.currentBlock() != self.editor.textCursor().block()`, format opening and closing markup ranges (`token.openingMarkupLength`, `token.closingMarkupLength`) with near-zero point size / transparent foreground (`setFontPointSize(0.1)`, `QColor(0, 0, 0, 0)`, ` setFontLetterSpacingPercentage(0)`) so `# `, `**`, `*`, `~~` visually collapse while the text body keeps its full Heading/Bold/Italic formatting.
    - Connect `cursorPositionChanged` on `MDEditView` to rehighlight the previous and current blocks when the cursor moves between lines so the active line always reveals its Markdown code for effortless editing.
- **`manuskript/ui/editors/formatBar.py`**:
  - Add a checkable **Readable / MD Code** toggle button (`btnReadableMode`) on Row 1 of `FormatBar` so the writer can switch modes with one click at any time.
- **`manuskript/ai/dock.py`**:
  - Add `self.btnDock = QPushButton(self.tr("Dock"))` / `self.tr("Undock")` in the top header row of `AIDock` (next to `New` and `Del`).
  - Connect `self.topLevelChanged.connect(self._updateDockButton)` and `self.btnDock.clicked.connect(self._toggleFloating)` so when the AI Chat window is floating (undocked), a prominent **"Dock"** button is immediately visible to snap it right back into the main window's dock area (`self.setFloating(False)`).

---

## Verification & Checkpoint Gate
1. **Web Tests (`vitest` + `playwright`)**:
   - Test toggling between MD Code Visible and Readable Mode in `/write`, verifying that markdown tokens are hidden on inactive lines in Readable Mode, shown on the active cursor line, and never alter the underlying document text.
2. **Desktop Tests (`pytest`)**:
   - Test `FormatBar` toggle button and `MarkdownHighlighter` formatting behavior in both `readableMode=True` and `readableMode=False`.
3. **Checkpoint**: Pause and review test results with user before proceeding to Chunk 5.
