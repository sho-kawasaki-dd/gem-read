# Cache Lifecycle Diagram

This diagram describes the lifecycle of Gemini context cache integration.

```mermaid
stateDiagram-v2
    [*] --> NoCache

    NoCache --> Creating: create_cache request
    Creating --> Active: cache created
    Creating --> NoCache: creation failed

    Active --> Active: update TTL
    Active --> Active: analyze with matching model
    Active --> NoCache: invalidate cache
    Active --> NoCache: open another document
    Active --> NoCache: shutdown cleanup
    Active --> NoCache: cache expires
    Active --> NoCache: model mismatch and user confirms invalidation
    Active --> FallbackRetry: cache-backed analyze fails
    FallbackRetry --> NoCache: clear internal cache linkage
    FallbackRetry --> NoCache: retry without cache
```

## Notes

- Cache is tied to a model name.
- `AIModel.analyze()` uses cached content only when the active cache model matches the current request model.
- The UI countdown is driven by cache expiration time from `CacheStatus`.
