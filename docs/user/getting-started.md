# Getting Started

## What This App Does

Gem Read is a local desktop reader for PDF and EPUB documents.
It lets you open documents, select one or more rectangular regions, and send the extracted content to Gemini for translation or custom analysis.

## Requirements

- Python 3.13 or newer
- A desktop environment that can run a PySide6 application
- `GEMINI_API_KEY` if you want to use AI features

## Install

```bash
uv sync --dev
```

## Configure Environment

Create a `.env` file in the repository root:

```env
GEMINI_API_KEY=your-api-key-here
```

The application can start without this key, but AI features will fail until the key is set.

## Launch

```bash
uv run python -m pdf_epub_reader
```

## Launch from Windows PowerShell

From the repository root, you can also use the bundled launcher:

```powershell
.\gem-read_launch.ps1
```

## Browser Extension Phase 1 Preview

The browser extension is a separate local-first workflow in this repository.

Before loading the extension in Chromium, start the local API:

```bash
uv run python -m browser_api
```

The default bind is `http://127.0.0.1:8000`. To change it, set `BROWSER_API_PORT` before launch.

```powershell
$env:BROWSER_API_PORT = "8010"
uv run python -m browser_api
```

Then load the unpacked extension from `browser-extension/dist/` after running:

```bash
cd browser-extension
npm install
npm run build
```

Open the extension popup, set the Local API Base URL, save it, and wait for the popup badge to show one of these states:

- `Reachable`: local API and live model catalog are available
- `Mock Mode`: local API is reachable but Gemini credentials or live model enumeration are unavailable
- `Unreachable`: popup cannot reach the local API URL

## First Run Checklist

1. Open a PDF or EPUB file.
2. Confirm that pages render in the main document pane.
3. Open the settings dialog and review rendering and AI options.
4. If you plan to use AI, choose available models in settings and confirm the side panel model selector is enabled.
5. Try a simple selection and run a translation request.

## Browser Extension First Run Checklist

1. Start `uv run python -m browser_api`.
2. Build and load the extension from `browser-extension/dist/`.
3. Open the popup and save the Local API Base URL.
4. Confirm the popup status badge is not `Unreachable`.
5. Select text on a web page and use the context menu entry `Gem Read で翻訳`.
6. After the first result appears, try `Translate + Explain` or `Run Custom Prompt` from the overlay.
