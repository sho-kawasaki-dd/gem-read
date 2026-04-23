## Plan: Desktop Capture Phase 1

Phase 1 should deliver the smallest Windows-only vertical slice that proves the desktop capture flow end-to-end: trigger capture, draw a rectangle, crop the selected screen area, send the crop image to Gemini through the existing AIModel adapter boundary, and reuse one modeless result window to show translation-only output. Reuse the existing qasync startup pattern and AI adapter pattern from the repository; do not add settings UI, OCR, WGC, or session replay in this phase.

**Steps**

1. Phase A: Bootstrap the new runtime surface. Create the desktop_capture package under d:/programming/py_apps/gem-read/src/desktop_capture with **init**.py, **main**.py, app.py, and config.py. Mirror the startup split used by the existing reader: **main**.py stays thin, app.py owns dotenv loading, config load, service wiring, and qasync startup. In app.py, call the Windows DPI-awareness API before QApplication creation so PySide6 logical coordinates can be converted consistently against mss bitmap coordinates. This step blocks all other implementation.
2. Extend build/runtime metadata in d:/programming/py_apps/gem-read/pyproject.toml. Add the mss dependency and include src/desktop_capture in the Hatch wheel packages list so uv run python -m desktop_capture works both in-place and after packaging. This depends on Step 1 only for the package path name.
3. Implement d:/programming/py_apps/gem-read/src/desktop_capture/config.py by mirroring the load/save structure from the existing reader config module, but with a separate platformdirs namespace for desktop capture. Keep Phase 1 settings limited to fixed defaults plus file persistence: capture backend default mss, delayed capture seconds, Gemini model name, output language, translation prompt, and fixed hotkey definition. Do not build any settings dialog yet. This can run in parallel with Step 4 once the package exists.
4. Phase B: Define the thin orchestration contracts before building widgets. Add a small presenter-centered contract surface inside the new package: one protocol or simple service boundary for screen capture, one for AI analysis, and one lightweight result view interface. Keep the presenter responsible for the state machine only: idle, selecting, capturing, analyzing, showing result, showing error. The presenter should accept already-normalized crop rectangles in physical pixels and return translation-only requests with include_explanation set to false. This step blocks Steps 5 through 8.
5. Implement d:/programming/py_apps/gem-read/src/desktop_capture/adapters/ai_gateway.py by reusing the existing AIModel and AnalysisRequest/AnalysisResult DTOs. The adapter should translate DesktopCaptureConfig into an AIModel instance and expose one analyze method that always sends mode translation, empty text, one cropped image byte payload, the configured model name, and the configured system prompt. Handle missing GEMINI_API_KEY as a user-facing error path rather than introducing browser_api-style mock mode in Phase 1.
6. Phase C: Build the capture interaction stack. Implement d:/programming/py_apps/gem-read/src/desktop_capture/capture/overlay.py as a full-screen transparent PySide6 overlay that tracks press-drag-release and emits a logical selection rectangle plus the QScreen chosen under the drag start. Keep the overlay focused on interaction and cleanup only; do not let it crop images itself. Convert logical coordinates to physical pixels using the selected screen devicePixelRatio before producing the capture request. Escape should cancel cleanly. This depends on Step 4.
7. Implement d:/programming/py_apps/gem-read/src/desktop_capture/capture/screenshot.py as the Phase 1 mss capture service. Capture the relevant monitor image, crop using the presenter-supplied physical rectangle, then encode the crop to JPEG bytes using Pillow at the repository default quality. Keep this module free of Qt widget concerns. Return image bytes plus capture metadata needed for diagnostics. This depends on Step 4 and can proceed in parallel with Step 6.
8. Implement d:/programming/py_apps/gem-read/src/desktop_capture/capture/hotkey.py and d:/programming/py_apps/gem-read/src/desktop_capture/capture/trigger_panel.py. The hotkey service should wrap RegisterHotKey and surface success/failure without owning business logic. The trigger panel should be a tiny always-available launcher with Capture now, Capture in 3s, and Capture in 5s buttons; it must remain the fallback path when hotkey registration fails. Delayed capture should disable controls while the countdown is active and then delegate to the presenter. This depends on Step 4 and can run in parallel with Steps 6 and 7.
9. Phase D: Wire the user-visible output surface. Implement d:/programming/py_apps/gem-read/src/desktop_capture/result_window.py as one reusable modeless window that can display loading, success, and error states. Keep rendering plain text in Phase 1 even if the backend returns Markdown. Reuse the same window instance for each capture and overwrite its content rather than spawning multiple windows. This depends on Step 4 and can run in parallel with Steps 6 through 8.
10. Implement d:/programming/py_apps/gem-read/src/desktop_capture/presenter.py to orchestrate the full sequence: request capture via overlay or delayed trigger, call the mss capture service, call the AI gateway, then update the result window and trigger panel state. The presenter should also centralize error messages for hotkey registration failure, empty or zero-area selections, missing API key, mss capture failure, and AI request failure. This depends on Steps 5 through 9.
11. Wire the runtime in d:/programming/py_apps/gem-read/src/desktop_capture/app.py so startup creates config, AI gateway, capture service, hotkey service, trigger panel, result window, and presenter; registers callbacks; shows the trigger panel; and unregisters the hotkey during shutdown. Keep entry files thin and keep all policy decisions in presenter/services rather than Qt widgets. This depends on Steps 3 and 5 through 10.
12. Phase E: Add focused tests around the non-UI logic. Add config persistence tests under d:/programming/py_apps/gem-read/tests, presenter tests with mock views and fake capture/AI services, and a narrow coordinate-normalization test for logical-to-physical rect conversion under mixed DPI assumptions. Avoid full Qt widget tests in Phase 1; the goal is to verify orchestration, failure handling, and scaling math without spinning up the real UI. This depends on the corresponding implementation steps.
13. Run behavior validation on Windows. Verify the default hotkey path, trigger panel fallback path, delayed capture path, DPI-correct cropping on at least one scaled display, and the end-to-end Gemini response path with a real API key. Treat black-screen DRM capture as a documented known limitation for Phase 1 rather than solving it here. This depends on the implementation being complete.

**Relevant files**

- d:/programming/py_apps/gem-read/desktop-capture-plan.md — source scope and explicit Phase 1 constraints to preserve
- d:/programming/py_apps/gem-read/pyproject.toml — add mss and include src/desktop_capture in wheel packaging
- d:/programming/py_apps/gem-read/src/pdf_epub_reader/infrastructure/event_loop.py — reuse the qasync QApplication startup and shutdown pattern
- d:/programming/py_apps/gem-read/src/pdf_epub_reader/app.py — reuse the thin entry plus app wiring structure
- d:/programming/py_apps/gem-read/src/pdf_epub_reader/dto/ai_dto.py — reuse AnalysisRequest, AnalysisResult, and translation-mode flags
- d:/programming/py_apps/gem-read/src/pdf_epub_reader/models/ai_model.py — reuse AIModel through an adapter, not directly from UI code
- d:/programming/py_apps/gem-read/src/browser_api/adapters/ai_gateway.py — reference the adapter boundary pattern that hides AIModel details
- d:/programming/py_apps/gem-read/src/pdf_epub_reader/utils/config.py — mirror config load/save and platformdirs handling with a separate namespace
- d:/programming/py_apps/gem-read/browser-extension/src/content/selection/rectangleSelectionController.ts — reference cleanup and single-active-selection interaction flow only; do not copy browser-specific assumptions blindly
- d:/programming/py_apps/gem-read/src/desktop_capture/**main**.py — new thin entry file
- d:/programming/py_apps/gem-read/src/desktop_capture/app.py — new runtime composition root and DPI-awareness setup
- d:/programming/py_apps/gem-read/src/desktop_capture/config.py — new desktop-capture-only config persistence
- d:/programming/py_apps/gem-read/src/desktop_capture/adapters/ai_gateway.py — new adapter from DesktopCaptureConfig to AIModel
- d:/programming/py_apps/gem-read/src/desktop_capture/capture/overlay.py — new rectangle selection overlay
- d:/programming/py_apps/gem-read/src/desktop_capture/capture/screenshot.py — new mss-based capture and crop service
- d:/programming/py_apps/gem-read/src/desktop_capture/capture/hotkey.py — new RegisterHotKey wrapper
- d:/programming/py_apps/gem-read/src/desktop_capture/capture/trigger_panel.py — new fallback launcher UI
- d:/programming/py_apps/gem-read/src/desktop_capture/presenter.py — new flow orchestrator
- d:/programming/py_apps/gem-read/src/desktop_capture/result_window.py — new reusable result display window
- d:/programming/py_apps/gem-read/tests/mocks/mock_views.py — reference mock-view style for presenter tests
- d:/programming/py_apps/gem-read/tests/test_presenters/test_language_presenter.py — reference patch-and-assert presenter testing pattern

**Verification**

1. Run a focused Python test slice for the new config and presenter tests with uv run pytest on the new or updated desktop-capture-related tests.
2. Launch the app with uv run python -m desktop_capture and verify startup does not crash when GEMINI_API_KEY is missing; it should surface a controlled error in the result window or trigger panel when capture is attempted.
3. Verify RegisterHotKey success on the primary Windows setup and confirm the trigger panel remains fully usable when registration intentionally fails or is disabled.
4. Validate delayed capture by clicking Capture in 3s and switching focus to another app before the overlay appears.
5. Validate DPI correctness on at least one non-100 percent display by selecting a known UI element edge and confirming the cropped image shown to Gemini matches the visual selection.
6. Validate the end-to-end happy path with a real Gemini key by capturing a small on-screen Japanese text region and checking that translation-only output appears in the single reused result window.
7. Record the expected Phase 1 limitation when a DRM-protected app returns a black screenshot; do not expand scope into WGC during this implementation.

**Decisions**

- Phase 1 output is translation only.
- Phase 1 uses one reusable modeless result window rather than one window per capture.
- Phase 1 does not include a settings UI; configuration lives in DesktopCaptureConfig defaults plus JSON persistence only.
- Phase 1 remains Windows-only and treats RegisterHotKey plus mss as the only supported capture path.
- Missing API credentials should produce a visible error, not a mocked translation.
- WGC, OCR, Markdown rendering, custom prompts, and session replay are explicitly excluded from this phase.

**Further Considerations**

1. Fixed hotkey default recommendation: keep Ctrl+Shift+G as the initial hardcoded default in config for Phase 1, and defer configurability to a later settings phase.
2. Capture rectangle ownership recommendation: let overlay own logical pointer tracking and screen detection, but let a pure helper function perform logical-to-physical rect conversion so that the scaling math is unit-testable.
