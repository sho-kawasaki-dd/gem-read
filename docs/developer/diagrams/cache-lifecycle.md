# Cache Lifecycle Diagram

This diagram describes the lifecycle of Gemini context cache integration.

```mermaid
stateDiagram-v2
    [*] --> NoCache

    NoCache --> Creating: create_cache request
    Creating --> Active: cache created
    Creating --> NoCache: creation failed

    Active --> Active: update TTL
    Active --> Active: analyze with explicit cache_name
    Active --> NoCache: invalidate cache
    Active --> NoCache: open another document
    Active --> NoCache: tab close or overlay clear cleanup
    Active --> NoCache: article extraction failure cleanup
    Active --> NoCache: cache expires
    Active --> NoCache: model mismatch and user confirms invalidation
    Active --> FallbackRetry: cache-backed analyze fails
    FallbackRetry --> NoCache: clear internal cache linkage
    FallbackRetry --> NoCache: retry without cache
```

## Notes

- Cache is tied to a model name.
- browser-extension sends `cache_name` only for active, model-matched article caches.
- `AIModel.analyze()` uses the explicit `cache_name` when provided; otherwise it falls back to the desktop app's internal active cache state.
- Explicit cache failures retry without cache but do not overwrite the desktop app's internal cache linkage.
- The UI countdown is driven by cache expiration time from `CacheStatus`.
