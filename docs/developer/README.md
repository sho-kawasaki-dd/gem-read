# Developer Documentation

This section explains how the application is structured and which diagrams should be used to understand or extend it.

## Supported Local Launch Paths

- Windows PowerShell wrapper: `.\gem-read_launch.ps1`
- Canonical module startup: `uv run python -m pdf_epub_reader`
- Browser API module startup: `uv run python -m browser_api`
- Browser API dev server: `uv run uvicorn browser_api.main:app --host 127.0.0.1 --port 8000 --reload`

## Read First

1. [docs/developer/architecture.md](docs/developer/architecture.md)
2. [docs/developer/runtime-flows.md](docs/developer/runtime-flows.md)
3. [docs/developer/testing.md](docs/developer/testing.md)

## Diagrams

1. [docs/developer/diagrams/system-overview.md](docs/developer/diagrams/system-overview.md)
2. [docs/developer/diagrams/layer-dependencies.md](docs/developer/diagrams/layer-dependencies.md)
3. [docs/developer/diagrams/open-file-sequence.md](docs/developer/diagrams/open-file-sequence.md)
4. [docs/developer/diagrams/selection-to-ai-sequence.md](docs/developer/diagrams/selection-to-ai-sequence.md)
5. [docs/developer/diagrams/cache-lifecycle.md](docs/developer/diagrams/cache-lifecycle.md)

## Documentation Goals

- Make the MVP boundaries explicit
- Make runtime flows easier to reason about
- Keep diagrams close to code so they can be updated with implementation changes

## Browser Extension Browser Workflow Notes

- The extension is local-first and only talks to `http://127.0.0.1:*` or `http://localhost:*`.
- Popup settings own the API base URL, connection status, and default model.
- The overlay can rerun translation, translation with explanation, and custom prompt actions after one selection session has been captured.
- `Ctrl+Shift+8` and the popup helper restore a cached session for the current tab. If no cached session exists, they intentionally fall back to a launcher-only overlay.
- `Ctrl+Shift+9` uses only the current live text selection. When no live text selection exists, it opens the full overlay with an explicit error instead of silently doing nothing.
- If `GEMINI_API_KEY` is missing, the browser API intentionally returns mock-mode responses so popup and overlay flows remain testable.
