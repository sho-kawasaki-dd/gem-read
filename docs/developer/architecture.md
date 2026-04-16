# Architecture Guide

## Architectural Style

The application uses MVP with a passive view approach.

- View classes are responsible for rendering widgets and forwarding user actions through callbacks.
- Presenters coordinate user actions, model calls, and view updates.
- Models implement document processing and Gemini API logic without depending on Qt.
- Infrastructure isolates Qt and asyncio integration.

## Main Boundaries

### View Layer

The view layer is implemented with PySide6 widgets and dialogs. It knows nothing about business logic beyond callback registration and display commands.

### Presenter Layer

The presenter layer depends on Protocol contracts rather than concrete view or model implementations. This keeps tests lightweight and makes the dependency direction stable.

### Model Layer

The model layer exposes async methods for document rendering, selection extraction, Gemini requests, and context cache operations.

### Infrastructure Layer

The infrastructure layer integrates Qt and asyncio using qasync, allowing presenters to await model operations without blocking the GUI thread.

## Browser Extension Phase 1 Boundaries

The browser extension uses a runtime-first split rather than an MVC split.

- `background/` owns privileged browser operations such as context menus, screenshot capture, and Local API calls.
- `content/` owns DOM reads, selection tracking, and the on-page overlay.
- `popup/` is limited to settings and connectivity checks in Phase 1.
- `shared/` holds contracts and settings used across all extension runtimes.

This split matters because the extension cannot treat every runtime as a normal web page. The content script is close to the page DOM, but it should not become the place where privileged browser APIs or Local API communication are orchestrated. Background remains the coordinator so CSP, permission handling, and capture flows stay in one place.

### Thin Entry Rule

The top-level entry files in `browser-extension/src/` are intentionally thin.

- `background.ts`, `content.ts`, and `popup.ts` only bootstrap their runtime.
- The actual behavior lives under `background/`, `content/`, and `popup/`.

Keeping the entries thin makes the Chrome lifecycle easier to reason about and keeps tests focused on usecases, services, selection logic, and overlay rendering rather than on runtime bootstrapping.

### Overlay Session Reuse

Phase 1 supports one important practical optimization: after one selection has been captured and cropped, the overlay can rerun translation, translation with explanation, or custom prompt actions without asking the user to reselect the same text.

This is why the code stores a tab-scoped analysis session in the background runtime.

- Content script captures the current selection snapshot.
- Background captures and crops the screenshot once.
- Overlay reruns reuse the cached selection and crop preview.

Without that cache, every action button would need to reacquire live selection state, which is fragile because browser selections often disappear once the context menu or overlay interaction begins.

### Selection Snapshot and Crop Rationale

The content script stores the latest selection snapshot because live browser selection state is not stable across asynchronous boundaries.

- `selectionchange`, `contextmenu`, `mouseup`, and `keyup` update the last known selection snapshot.
- If live selection is gone later, the code can still recover the last valid rectangle and text.

The crop flow converts viewport coordinates into screenshot bitmap coordinates before resizing.

- Selection rectangles are captured in CSS viewport space.
- `captureVisibleTab` returns bitmap dimensions that may not match CSS pixels.
- The browser-extension crops and resizes before sending the image to Python so upstream requests stay small and focused.

## Browser API Boundaries

The Local Python API uses a thin hexagonal structure.

- `api/` owns FastAPI app creation, routers, schema translation, dependency wiring, and HTTP error mapping.
- `application/` owns use-case behavior such as model resolution, image decode, and degraded fallback behavior.
- `adapters/` isolate reuse of `pdf_epub_reader` assets like `AIModel` and config loading.

### Why Routers Stay Thin

Routers should not know how to resolve model names, decode browser image payloads, or emulate responses when `GEMINI_API_KEY` is missing. Those are application concerns, not HTTP concerns.

Keeping routers thin provides three benefits:

- tests can override dependencies at the FastAPI boundary without pulling in real Gemini behavior
- the browser API can evolve its fallback behavior without changing request parsing code
- reuse of desktop-side AI assets stays concentrated inside adapters and services

### Why Mock Mode Exists

Mock mode is intentional, not a temporary hack.

- If `GEMINI_API_KEY` is missing, popup and overlay still need a way to validate transport, selection capture, crop payloads, and UI state transitions.
- The service therefore returns deterministic mock responses and degraded model metadata instead of failing the entire flow.

This lets the extension remain testable and demoable even before live Gemini credentials are configured.

## Key Entry Points

- Windows launcher: `gem-read_launch.ps1`
- Application composition: `src/pdf_epub_reader/app.py`
- Event loop integration: `src/pdf_epub_reader/infrastructure/event_loop.py`
- Main UI orchestration: `src/pdf_epub_reader/presenters/main_presenter.py`
- Side panel AI orchestration: `src/pdf_epub_reader/presenters/panel_presenter.py`
- Document processing: `src/pdf_epub_reader/models/document_model.py`
- Gemini integration: `src/pdf_epub_reader/models/ai_model.py`

## Why These Diagrams Matter

This project has several flows that are easy to misunderstand from code alone:

- Qt and asyncio are integrated but isolated
- selection state is managed across async completion boundaries
- cache lifecycle depends on model identity and document lifecycle
- side panel actions are separated from document interaction logic
- browser-extension background and content runtimes intentionally do not share the same responsibilities
- browser_api uses degraded fallback behavior on purpose so extension flows stay testable without live credentials

The diagrams in `docs/developer/diagrams/` are intended to explain exactly those points.
