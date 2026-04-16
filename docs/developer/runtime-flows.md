# Runtime Flows

## Startup Flow

1. On Windows PowerShell, `.\gem-read_launch.ps1` changes to the repository root and runs `uv run python -m pdf_epub_reader`.
2. `python -m pdf_epub_reader` calls `main()`.
3. `main()` loads `.env` and delegates to `run_app()`.
4. `run_app()` creates or reuses `QApplication`, installs a qasync event loop, and schedules `_app_main()`.
5. `_app_main()` creates config, models, views, and presenters.
6. The main window is shown.
7. On shutdown, cache invalidation cleanup is attempted before event loop teardown.

## Open File Flow

1. The view emits an open request, recent-file request, or file-drop event.
2. `MainPresenter.open_file()` clears selection state and displays opening status.
3. Existing cache is invalidated if active.
4. `DocumentModel.open_document()` returns `DocumentInfo`.
5. Placeholder pages are derived from page sizes and base DPI.
6. The view receives page placeholders and table-of-contents entries.
7. Page images are rendered later through viewport-driven requests.

## Selection Flow

1. The user creates one or more rectangular selections.
2. `MainPresenter` allocates stable selection slots and marks them pending.
3. `DocumentModel.extract_content()` resolves text and optional image data.
4. The selection snapshot is updated to ready or error.
5. `PanelPresenter` rebuilds the combined preview string from ordered slots.
6. AI requests use the current side panel model and current selection snapshot.

## Cache Flow

1. Full document text is extracted.
2. `AIModel.create_cache()` creates remote cached content for a selected model.
3. `PanelPresenter` updates cache UI state and countdown.
4. `AIModel.analyze()` includes cached content when the model matches.
5. If cache-backed analysis fails for non-rate-limit reasons, AIModel clears the cache linkage and retries without cache.
6. Cache can expire, be invalidated manually, be replaced, or be cleared on shutdown.

## Browser Extension Phase 1 Flow

1. The user selects text on a web page.
2. The content script tracks the selection snapshot so text and rectangle data survive short-lived browser selection loss.
3. A context-menu action reaches the background runtime.
4. Background requests the latest selection snapshot from the content script.
5. Background captures a visible-tab screenshot.
6. Background converts viewport coordinates into bitmap coordinates and crops the selected area before any API call.
7. Background sends text, cropped image, model choice, and selection metadata to `browser_api`.
8. The overlay first renders a loading state, then renders the translated result, explanation, or error state.

## Overlay Rerun Flow

1. After the first successful capture, background stores a tab-scoped analysis session.
2. The overlay exposes translation, translation-with-explanation, and custom-prompt action buttons.
3. When the user presses one of those buttons, the content script forwards the request to background.
4. Background reuses the cached selection and crop preview instead of reacquiring the live browser selection.
5. The new API result is rendered into the same overlay.

This rerun flow exists because live browser selections are unreliable once the user starts interacting with overlay controls.

## Popup Bootstrap Flow

1. The popup loads saved extension settings from `chrome.storage.local`.
2. The popup checks `/health` on the Local API.
3. If health succeeds, the popup requests `/models`.
4. If model loading succeeds, the popup renders a reachable state with live model choices.
5. If model loading fails but health succeeded, the popup stays usable and renders a degraded state instead of failing closed.

This distinction lets users tell the difference between an offline Local API and a reachable API that is running in mock or config-fallback mode.
