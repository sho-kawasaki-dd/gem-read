# Layer Dependency Diagram

This diagram focuses on dependency direction rather than runtime calls.

```mermaid
flowchart TB
    subgraph Views[View Layer]
        MainView[MainWindow]
        SideView[SidePanelView]
        Dialogs[Settings / Cache / Language Dialogs]
    end

    subgraph ViewContracts[View Protocols]
        IMainView[IMainView]
        ISidePanelView[ISidePanelView]
        IDialogs[ISettingsDialogView / ICacheDialogView / ILanguageDialogView]
    end

    subgraph Presenters[Presenter Layer]
        MainPresenter[MainPresenter]
        PanelPresenter[PanelPresenter]
        OtherPresenters[Settings / Cache / Language Presenters]
    end

    subgraph ModelContracts[Model Protocols]
        IDocumentModel[IDocumentModel]
        IAIModel[IAIModel]
    end

    subgraph Models[Model Layer]
        DocumentModel[DocumentModel]
        AIModel[AIModel]
    end

    subgraph Infra[Infrastructure]
        EventLoop[event_loop.py / qasync]
    end

    MainView -.implements.-> IMainView
    SideView -.implements.-> ISidePanelView
    Dialogs -.implements.-> IDialogs

    MainPresenter --> IMainView
    MainPresenter --> IDocumentModel
    MainPresenter --> PanelPresenter
    PanelPresenter --> ISidePanelView
    PanelPresenter --> IAIModel
    OtherPresenters --> IDialogs

    DocumentModel -.implements.-> IDocumentModel
    AIModel -.implements.-> IAIModel

    EventLoop --> Presenters
    EventLoop --> Models
```

## Notes

- Qt classes belong in the view layer and infrastructure layer, not in presenters or models.
- Protocols are the dependency boundary used by presenters and tests.
