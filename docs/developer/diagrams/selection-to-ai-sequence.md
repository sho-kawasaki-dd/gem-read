# Selection to AI Sequence Diagram

This diagram shows how a user selection becomes an AI request.

```mermaid
sequenceDiagram
    actor User
    participant View as MainWindow
    participant MP as MainPresenter
    participant DM as DocumentModel
    participant PP as PanelPresenter
    participant SP as SidePanelView
    participant AI as AIModel

    User->>View: drag selection rectangle
    View->>MP: set_on_selection_requested(page, rect, append)
    MP->>MP: allocate stable selection slot
    MP->>View: show_selection_highlights(snapshot: pending)
    MP->>PP: set_selection_snapshot(snapshot: pending)
    PP->>SP: set_selection_snapshot(...)
    PP->>SP: set_combined_selection_preview(...)

    MP->>DM: extract_content(page, rect, dpi, force_image, auto_detect_image, auto_detect_math)
    alt extraction succeeds
        DM-->>MP: SelectionContent
        MP->>MP: update slot to ready
    else extraction fails
        DM-->>MP: exception
        MP->>MP: update slot to error
    end

    MP->>View: show_selection_highlights(updated snapshot)
    MP->>PP: set_selection_snapshot(updated snapshot)
    PP->>SP: set_selection_snapshot(...)
    PP->>SP: set_combined_selection_preview(...)

    User->>SP: click translate / explain / custom prompt
    SP->>PP: translate or custom prompt callback
    PP->>PP: build AnalysisRequest from ordered slots
    PP->>SP: show_loading(true)
    PP->>AI: analyze(request)
    AI-->>PP: AnalysisResult or AI error
    PP->>SP: update_result_text(...)
    PP->>SP: show_loading(false)
```

## Notes

- Selection slots preserve user order even if async extraction completes later.
- The side panel does not build model requests on its own; PanelPresenter does that orchestration.
