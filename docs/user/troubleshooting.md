# Troubleshooting

## PowerShell Launcher Does Not Start

Check the following:

- Run `.\gem-read_launch.ps1` from the repository root
- `uv` is installed and available on `PATH`
- Dependencies have been installed with `uv sync --dev`
- PowerShell execution policy is not blocking local scripts in the current session

## AI Features Do Not Work

Check the following:

- `GEMINI_API_KEY` is present in `.env`
- The selected model is valid and enabled
- The machine has network access to Gemini API
- The side panel model selector is not disabled

## Browser Extension Popup Shows Unreachable

Check the following:

- `uv run python -m browser_api` is still running
- The popup Local API Base URL matches the actual host and port
- The URL uses `127.0.0.1` or `localhost`, not a LAN or remote host
- Another process is not already occupying the expected port

If you changed the port, save the new URL in the popup and refresh the status.

## Browser Extension Popup Shows Mock Mode

This means the extension can reach the local API, but the backend is not in a fully live state.

Typical causes:

- `GEMINI_API_KEY` is not configured
- live Gemini model enumeration failed and the API fell back to configured models

This state is expected during local wiring or UI testing. Translation requests still return explicit mock-mode banners in the overlay.

## Browser Extension Overlay Actions Stay Disabled

Overlay rerun buttons only activate after one selection session has been captured.

Check the following:

- Text is selected on the page before using `Gem Read で翻訳`
- The first translation request completed far enough to show the overlay
- You did not open only the popup shortcut overlay without running an initial selection request

If needed, reselect the text and run the context menu action again.

## Browser Extension Overlay Shows Error After Rerun

Check the following:

- The local API is still reachable from the popup
- The selected model name is valid
- `Run Custom Prompt` has non-empty prompt text
- The page still allows the content script to stay loaded

If the popup status is `Unreachable`, reconnect the local API first.

## Document Opens but AI Fails

This usually means local viewing is working but AI configuration is incomplete.

Check:

- API key configuration
- Selected models in settings
- Error text shown in the side panel result area

## Cache Operations Fail

Possible causes:

- The selected model does not support context caching
- The API request failed remotely
- Cached content expired

If needed, invalidate the cache and create it again.

## Math or Markdown Rendering Looks Wrong

Check whether the response includes Markdown or LaTeX syntax that should be rendered in the side panel. If output is still incorrect, verify the local KaTeX bundle and the rendered response content.

## UI Language Looks Wrong After Change

Main window and side panel update immediately. Some dialogs apply new language text when they are opened again.
