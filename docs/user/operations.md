# Core Operations

## Launch the Application

- On Windows PowerShell, run `.\gem-read_launch.ps1` from the repository root.
- The launcher script delegates to `uv run python -m pdf_epub_reader`.

## Open a Document

- Use the open command from the menu.
- Drag and drop a supported file onto the document pane.
- Reopen a recent file from the recent files menu.

If the document is password protected, the application prompts for a password before retrying the open operation.

## Navigate the Document

- Scroll through pages in the central document pane.
- Use the bookmark panel to jump to entries from the table of contents.
- Use zoom controls to change the viewport scale.

## Select Content

- Drag on the document to create a selection.
- Use `Ctrl+drag` to append more selections.
- Press `Esc` to clear the current selection set.

Each accepted selection becomes a numbered slot in the side panel. Slots can be pending, ready, or error.

## Run AI Actions

From the side panel you can:

- Run translation
- Run translation with explanation
- Submit a custom prompt
- Choose whether to force sending the selected region as an image
- Switch the active Gemini model for the current request

When the selection includes cropped image content, the request can be sent as multimodal input.

## Useful Shortcuts

- `Ctrl+B`: toggle bookmark panel
- `Ctrl+,`: open settings
- `Ctrl+Shift+G`: open cache management
- `Esc`: clear selections

## Use the Browser Extension Phase 1 Preview

1. Start the local API with `uv run python -m browser_api`.
2. Open the extension popup and save the Local API Base URL.
3. Check the popup status badge.

Badge meanings:

- `Reachable`: extension can reach the local API and fetch a live model list
- `Mock Mode`: extension can reach the local API, but the API is returning fallback or mock-mode information
- `Unreachable`: extension cannot reach the configured local API URL

4. Select text on a page.
5. Use the selection context menu entry `Gem Read で翻訳`.
6. In the overlay, inspect the crop preview and the initial translation result.
7. If you want a different action without reselection, use one of the overlay actions:

- `Translate`
- `Translate + Explain`
- `Run Custom Prompt`

8. Optionally enter a different model ID in the overlay before rerunning.
9. Use the minimize button if you want to keep the current session available while reducing the overlay footprint.

Current Phase 1 scope:

- Single text selection
- Popup-managed local API URL and default model
- Overlay reruns for translation, explanation, and custom prompt

Not yet included in Phase 1:

- Multi-selection batching
- Free-rectangle capture mode
- Article-wide extraction
- Context Cache integration from the extension UI
