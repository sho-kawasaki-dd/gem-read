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

## Browser API Test Commands

- Focused browser_api suite: `uv run pytest tests/test_browser_api/ -q`
- Full Python suite: `uv run pytest tests/ -q`

The browser_api tests stub the AI gateway or FastAPI dependency wiring so they do not require live Gemini access.

## Browser Extension Test Commands

- Install extension dependencies: `npm install` (run inside `browser-extension/`)
- Unit tests: `npm run test`
- Coverage report: `npm run test:coverage`
- Chromium smoke E2E: `npm run test:e2e`
- Build regression check: `npm run build`

The Playwright smoke test loads the unpacked extension from `dist/`, selects text on a local fixture page, verifies selection capture through the service worker, and confirms overlay rendering. Native browser context menus are not automated in this smoke path; the unit test suite covers the background usecase that normally sits behind the context-menu click.

## CI Checks

- `.github/workflows/browser-api-tests.yml`: runs `uv sync --dev` and `uv run pytest tests/test_browser_api/ -q`
- `.github/workflows/browser-extension-unit.yml`: runs `npm ci` and `npm run test` in `browser-extension/`
- `.github/workflows/browser-extension-playwright.yml`: runs `npm ci`, `npx playwright install chromium`, and `npm run test:e2e` in `browser-extension/`

These workflows are intentionally split so branch protection can require each gate independently and failures can be retried without rerunning unrelated suites.

## Browser API Coverage Areas

- `application/services/analyze_service.py`: model resolution, Base64 image decode, AI key fallback, and response shaping
- `/health` and `/analyze/translate`: success responses, request validation, 400 mapping, and upstream AI error mapping

## Browser Extension Coverage Areas

- `background/usecases/runPhase0TranslationTest.ts`: loading, success, and error overlay orchestration
- `background/services/cropSelectionImage.ts`: crop coordinate scaling and output encoding
- `content/selection/snapshotStore.ts`: selection capture, fallback reuse, and guidance errors
- `content/overlay/renderOverlay.ts`: DOM rendering, visibility toggles, and close interaction

## Smoke Launch Checks

- Validate the canonical startup path with `uv run python -m pdf_epub_reader`.
- On Windows, also validate `.\gem-read_launch.ps1` to ensure the PowerShell wrapper still resolves the repository root correctly.
