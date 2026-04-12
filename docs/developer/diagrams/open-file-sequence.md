# Open File Sequence Diagram

This diagram shows the main open-document path, including cache invalidation and password retry.

```mermaid
sequenceDiagram
    actor User
    participant View as MainWindow
    participant MP as MainPresenter
    participant AI as AIModel
    participant DM as DocumentModel

    User->>View: open file / drop file / pick recent file
    View->>MP: callback with file path
    MP->>MP: clear selection state
    MP->>View: show opening status
    MP->>AI: get_cache_status()
    alt active cache exists
        MP->>AI: invalidate_cache()
        MP->>MP: reset panel cache status
    end

    MP->>DM: open_document(file_path, password=None)
    alt password required
        DM-->>MP: DocumentPasswordRequired
        MP->>View: show password dialog
        View-->>MP: password or cancel
        alt cancelled
            MP->>View: show cancelled status
        else password entered
            MP->>DM: open_document(file_path, password)
            DM-->>MP: DocumentInfo
        end
    else open succeeds
        DM-->>MP: DocumentInfo
    end

    MP->>MP: build placeholder PageData from page_sizes
    MP->>View: set_window_title(...)
    MP->>View: display_pages(placeholders)
    MP->>View: display_toc(entries)
    MP->>View: show loaded status
```

## Notes

- Actual page image rendering is deferred until the view requests needed pages.
- Cache is cleared when switching documents so analysis state cannot leak across files.
