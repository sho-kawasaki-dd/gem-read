# Testing Guide

## Testing Strategy

The project is designed so that most logic can be tested without launching a real Qt UI.

- Presenters are tested against mock views and mock models.
- Models are tested as async Python components.
- Protocols define the stable contracts used by both production code and tests.
- browser_api is tested with pytest against service and router layers.
- browser-extension unit tests use Vitest + jsdom, and smoke E2E uses Playwright on Chromium.

## Main Test Areas

### Document Model

Document tests cover:

- PDF and EPUB open flows
- rendering behavior
- extraction logic
- page cache behavior
- table-of-contents extraction

### AI Model

AI tests cover:

- request construction
- multimodal request handling
- retry behavior
- model enumeration
- context cache behavior

### Presenters

Presenter tests cover:

- open-file orchestration
- selection state updates
- side panel actions
- cache orchestration
- UI language application

## Practical Rule

If a new feature adds branching logic, prefer putting that logic in a presenter or model and covering it with tests before expanding the Qt view layer.

For the browser extension, keep entry files thin and prefer direct tests for usecases, services, overlay rendering, and selection state modules.

When reading or extending the Phase 1 browser-extension and browser_api code, use comments and docstrings as a guide to design intent rather than as a substitute for tests.

- Entry files should explain why they are thin, not restate the calls they make.
- Services and usecases should explain why state is cached, delegated, or normalized.
- Test fixtures and stubs should explain which contract they isolate.

## Browser API Test Commands

- Focused browser_api suite: `uv run pytest tests/test_browser_api/ -q`
- Full Python suite: `uv run pytest tests/ -q`
- Local browser API launch: `uv run python -m browser_api`
- Local browser API dev launch with reload: `uv run uvicorn browser_api.main:app --host 127.0.0.1 --port 8000 --reload`

The browser_api tests stub the AI gateway or FastAPI dependency wiring so they do not require live Gemini access.

## Browser Extension Test Commands

- Install extension dependencies: `npm install` (run inside `browser-extension/`)
- Unit tests: `npm run test`
- Coverage report: `npm run test:coverage`
- Chromium smoke E2E: `npm run test:e2e`
- Build regression check: `npm run build`

The Playwright smoke test loads the unpacked extension from `dist/`, saves popup settings against a stub local API, reopens the overlay through the background runtime, and exercises keyboard-first overlay flows such as `Esc`, `Alt+R`, and `Ctrl+Enter`. Native browser context menus are not automated in this smoke path; the unit test suite covers the background usecase that normally sits behind the context-menu click.

## Empty Batch Cache Guard Checks

- `openOverlaySession` must pass `allowAutoCreate: false` to `syncArticleCacheState` when the current batch has zero items. Unit test in `openOverlaySession.test.ts` covers both the zero-item and non-zero-item branches.
- `removeSelectionSessionItem` must preserve `articleContext` and `articleCacheState` (via `setAnalysisSession` with empty items) rather than clearing the session when the last item is removed. Unit test in `updateSelectionSession.test.ts` covers this.
- `clearSelectionBatch` must clear all items while preserving full session context. Unit test in `updateSelectionSession.test.ts` covers this.
- `Alt+Backspace` must send `{ type: 'phase3.clearSelectionBatch' }` when focus is outside editable targets. Unit test in `renderOverlay.test.ts` covers both the happy path and the "inside textarea" guard.
- `GET /cache/list` must return only caches with `display_name` prefixed `browser-extension:`. Python tests in `test_cache_router.py` cover list, empty list, and error propagation.

## Phase 4D Focus Checks

- Browser extension unit coverage should include article token estimation, article cache state rendering, and result usage rendering.
- Browser API tests should verify that analyze responses preserve Gemini usage metadata when it is available.
- Playwright smoke should cover one article-like page where overlay reopen triggers article extraction, token estimation, automatic cache creation, and a rerun against the cached session.

Phase 4D regression commands:

- `npm run test`
- `npm run test:e2e`
- `npm run build`
- `uv run pytest tests/test_browser_api/ -q`

When running the Playwright smoke manually, verify these points in addition to the existing Phase 3 keyboard checks:

- The overlay shows an `Article Context` card on pages where Readability or the DOM fallback can extract a long article body.
- The overlay shows a `Tokens` section with current request estimate, article baseline, cache impact, and last response usage when available.
- Automatic cache creation only happens when the extracted article is large enough and the active model supports caching.
- Manual cache deletion updates the overlay state without breaking rerun support for the current selection batch.
- If `/tokens/count` fails, the overlay still renders and falls back to degraded token messaging instead of becoming unusable.

## Explicit Cache Ownership Checks

- browser-extension analyze requests should include `cache_name` only when the current tab session has an active article cache whose model matches the selected analyze model.
- browser-extension should not poll `GET /cache/status`; cache reuse now relies on local `expireTime` countdown plus backend lazy validation during analyze.
- tab close and overlay clear should attempt remote cache deletion before the local session is dropped.
- article extraction failure with an active cache should attempt remote deletion and surface `invalidated` or `degraded` state locally.
- navigation alone should preserve the cached article state until the next sync decides whether the article identity still matches.

## CI Checks

- `.github/workflows/browser-api-tests.yml`: runs `uv sync --dev` and `uv run pytest tests/test_browser_api/ -q`
- `.github/workflows/browser-extension-unit.yml`: runs `npm ci` and `npm run test` in `browser-extension/`
- `.github/workflows/browser-extension-playwright.yml`: runs `npm ci`, `npx playwright install chromium`, and `npm run test:e2e` in `browser-extension/`

These workflows are intentionally split so branch protection can require each gate independently and failures can be retried without rerunning unrelated suites.

## Browser API Coverage Areas

- `application/services/analyze_service.py`: model resolution, Base64 image decode, AI key fallback, and response shaping
- `/health`, `/models`, and `/analyze/translate`: success responses, request validation, custom prompt behavior, config fallback behavior, 400 mapping, and upstream AI error mapping

## Browser Extension Coverage Areas

- `background/usecases/runSelectionAnalysis.ts`: settings-aware orchestration, session reuse, and action reruns
- `background/services/cropSelectionImage.ts`: crop coordinate scaling and output encoding
- `shared/gateways/localApiGateway.ts`: popup bootstrap and analyze request shaping
- `content/selection/snapshotStore.ts`: selection capture, fallback reuse, and guidance errors
- `content/overlay/renderOverlay.ts`: DOM rendering, action controls, keyboard bindings, minimize flow, and background-driven cached-session restore behavior
- `popup/ui/renderPopup.ts`: popup status rendering, settings persistence, and background-driven cached-session reopen flow

## Smoke Launch Checks

- Validate the canonical startup path with `uv run python -m pdf_epub_reader`.
- Validate the browser API startup path with `uv run python -m browser_api`.
- On Windows, also validate `.\gem-read_launch.ps1` to ensure the PowerShell wrapper still resolves the repository root correctly.

## Browser Extension Manual Checks

- Start `uv run python -m browser_api` before opening the extension popup.
- In the popup, confirm `Reachable`, `Mock Mode`, or `Unreachable` matches the local API state.
- With `GEMINI_API_KEY` unset, confirm popup can still reach the API and the overlay shows explicit mock-mode text.
- On a regular http or https page, build a batch first and confirm `Ctrl+Shift+8` restores the cached full overlay panel for that tab.
- With no cached session, confirm `Ctrl+Shift+8` shows the launcher-only overlay instead of a full panel.
- With a live text selection active, confirm `Ctrl+Shift+9` appends only the current live text selection to the batch.
- With no live text selection active, confirm `Ctrl+Shift+9` renders an explicit full-overlay error instead of failing silently.
- Confirm `Ctrl+Shift+Y` starts rectangle capture and `Esc` still cancels rectangle mode without minimizing the overlay.
- Confirm `Esc` minimizes the overlay, `Shift+Esc` closes it and clears the tab session, `Alt+R` reruns the last action, and `Ctrl+Enter` submits the custom prompt only while the textarea is focused.
- Confirm the popup `Open Overlay On Active Tab` button triggers the same cached-session reopen flow as the browser command.
- On restricted pages where content scripts cannot run, confirm commands do not inject the overlay and document that limitation instead of treating it as a regression.
