# Packt Cache Notes

## Status

This is intentionally a deferred follow-up, not an active bugfix track.

The browser extension now preserves article cache state across tab navigation and fresh selection runs, but Packt section changes can still trigger cache recreation.

The explicit cache ownership rollout is complete: browser-extension reruns now opt into a specific `cache_name`, and session teardown or extraction failure attempts remote cache deletion. The remaining Packt issue is about article identity drift, not stale implicit cache reuse.

## Why It Still Recreates

- Packt changes the section slug in the page URL, for example `.../ch04lvl1sec23/...` to `.../ch04lvl1sec25/...`.
- The extension compares a derived article identity before reusing the existing cache.
- On Packt, the identity can still drift across section moves because the extracted metadata is not stable enough.

## What Was Already Fixed

- Cache state is no longer dropped just because a new selection run starts after navigation.
- URL changes no longer trigger immediate cache deletion in the background runtime.
- Cache invalidation now prefers article identity over raw body hash changes.

## Current Tradeoff

The remaining issue appears to be site-specific rather than a general cache lifecycle bug.

Given the current token sizes and request shape, the practical cost impact is limited, so this was deferred to avoid overfitting the generic extension flow to one site.

## Resume Here If Needed

If this work is resumed, inspect the actual `cachedIdentity` and `currentIdentity` values from the service worker console first.

Use that to classify the failure mode:

1. URL-driven drift: identity falls back to a URL form that still includes the Packt section slug.
2. Title-driven drift: Readability or document title changes per section, so `siteName + title` is not stable enough.

## Recommended Next Step

Prefer a Packt-specific identity extractor over more generic heuristics.

Candidate approach:

1. Detect `subscription.packtpub.com` in content-side article extraction.
2. Derive a stable identity from book-level and chapter-level metadata, not section-level URL segments.
3. Keep the generic identity builder unchanged for other sites.

## Relevant Files

- `browser-extension/src/background/services/articleCacheService.ts`
- `browser-extension/src/background/usecases/runSelectionAnalysis.ts`
- `browser-extension/src/content/selection/articleContext.ts`