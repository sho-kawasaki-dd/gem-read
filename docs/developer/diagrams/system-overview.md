# System Overview Diagram

This diagram shows the main runtime components and external dependencies.

```mermaid
flowchart LR
    User[User]
    MainWindow[MainWindow / Dialogs]
    SidePanel[SidePanelView]
    Bookmark[BookmarkPanelView]
    MainPresenter[MainPresenter]
    PanelPresenter[PanelPresenter]
    SettingsPresenter[SettingsPresenter]
    LanguagePresenter[LanguagePresenter]
    CachePresenter[CachePresenter]
    DocumentModel[DocumentModel]
    AIModel[AIModel]
    Config[AppConfig / JSON config]
    QAsync[qasync Event Loop]
    PyMuPDF[PyMuPDF]
    Gemini[Gemini API]

    User --> MainWindow
    User --> SidePanel
    MainWindow --> MainPresenter
    SidePanel --> PanelPresenter
    Bookmark --> MainPresenter
    MainPresenter --> DocumentModel
    MainPresenter --> SettingsPresenter
    MainPresenter --> LanguagePresenter
    MainPresenter --> CachePresenter
    MainPresenter --> PanelPresenter
    PanelPresenter --> AIModel
    DocumentModel --> PyMuPDF
    AIModel --> Gemini
    MainPresenter --> Config
    AIModel --> Config
    DocumentModel --> Config
    QAsync --> MainPresenter
    QAsync --> PanelPresenter
    QAsync --> DocumentModel
    QAsync --> AIModel
```

## Notes

- Views do not call models directly.
- Presenters orchestrate asynchronous model operations.
- qasync provides the bridge between Qt and asyncio.
