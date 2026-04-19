import { beforeEach, describe, expect, it, vi } from 'vitest';

const countTokensMock = vi.hoisted(() => vi.fn());
const createContextCacheMock = vi.hoisted(() => vi.fn());
const deleteContextCacheMock = vi.hoisted(() => vi.fn());
const fetchContextCacheStatusMock = vi.hoisted(() => vi.fn());

vi.mock('../../../src/shared/gateways/localApiGateway', () => ({
  countTokens: countTokensMock,
  createContextCache: createContextCacheMock,
  deleteContextCache: deleteContextCacheMock,
  fetchContextCacheStatus: fetchContextCacheStatusMock,
}));

import {
  buildNavigatedSessionState,
  invalidateArticleCache,
  mergeCollectedArticleContext,
  syncArticleCacheState,
} from '../../../src/background/services/articleCacheService';

describe('articleCacheService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates an article cache automatically when the article is eligible', async () => {
    countTokensMock.mockResolvedValue({
      ok: true,
      tokenCount: 1400,
      modelName: 'gemini-2.5-flash',
    });
    createContextCacheMock.mockResolvedValue({
      ok: true,
      isActive: true,
      cacheName: 'cachedContents/article-1',
      displayName: 'browser-extension:Example article',
      modelName: 'gemini-2.5-flash',
      tokenCount: 2048,
      ttlSeconds: 3600,
      expireTime: '2026-04-17T10:00:00+00:00',
    });

    const session = await syncArticleCacheState(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
        articleContext: {
          title: 'Example article',
          url: 'https://example.com/article',
          bodyText: 'Long article body',
          bodyHash: 'abc123def4567890',
          source: 'readability',
          textLength: 1800,
        },
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
        allowAutoCreate: true,
      }
    );

    expect(countTokensMock).toHaveBeenCalled();
    expect(createContextCacheMock).toHaveBeenCalled();
    expect(session.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'active',
        cacheName: 'cachedContents/article-1',
        autoCreateEligible: true,
      })
    );
  });

  it('invalidates the tracked cache when the model changes', async () => {
    fetchContextCacheStatusMock.mockResolvedValue({
      ok: true,
      isActive: true,
      cacheName: 'cachedContents/article-1',
      modelName: 'gemini-2.5-pro',
    });
    deleteContextCacheMock.mockResolvedValue(undefined);
    countTokensMock.mockResolvedValue({
      ok: true,
      tokenCount: 200,
      modelName: 'gemini-2.5-flash',
    });

    const session = await syncArticleCacheState(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
        articleContext: {
          title: 'Example article',
          url: 'https://example.com/article',
          bodyText: 'Body',
          bodyHash: 'abc123def4567890',
          source: 'readability',
          textLength: 100,
        },
        articleCacheState: {
          status: 'active',
          cacheName: 'cachedContents/article-1',
          modelName: 'gemini-2.5-pro',
          articleUrl: 'https://example.com/article',
          articleIdentity: 'example.com/article::example article',
          articleHash: 'abc123def4567890',
        },
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
        allowAutoCreate: false,
      }
    );

    expect(deleteContextCacheMock).toHaveBeenCalledWith(
      'cachedContents/article-1',
      'http://127.0.0.1:9000'
    );
    expect(session.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'candidate',
        invalidationReason: 'model-changed',
        articleIdentity: 'example.com/article::example article',
      })
    );
  });

  it('reuses the tracked cache across section changes when article identity is stable', async () => {
    fetchContextCacheStatusMock.mockResolvedValue({
      ok: true,
      isActive: true,
      cacheName: 'cachedContents/article-1',
      modelName: 'gemini-2.5-flash',
      tokenCount: 2048,
      ttlSeconds: 3600,
      expireTime: '2026-04-17T10:00:00+00:00',
    });
    countTokensMock.mockResolvedValue({
      ok: true,
      tokenCount: 1400,
      modelName: 'gemini-2.5-flash',
    });

    const session = await syncArticleCacheState(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
        articleContext: {
          title: 'Example article',
          url: 'https://example.com/article/section-2',
          bodyText: 'Section two body',
          bodyHash: 'differenthash1234',
          source: 'readability',
          siteName: 'Example',
          textLength: 1700,
        },
        articleCacheState: {
          status: 'active',
          cacheName: 'cachedContents/article-1',
          modelName: 'gemini-2.5-flash',
          articleUrl: 'https://example.com/article/section-1',
          articleIdentity: 'example::example article',
          articleHash: 'abc123def4567890',
        },
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
        allowAutoCreate: false,
      }
    );

    expect(deleteContextCacheMock).not.toHaveBeenCalled();
    expect(session.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'active',
        cacheName: 'cachedContents/article-1',
        articleIdentity: 'example::example article',
        articleUrl: 'https://example.com/article/section-1',
      })
    );
  });

  it('invalidates the tracked cache when article identity changes', async () => {
    deleteContextCacheMock.mockResolvedValue(undefined);
    countTokensMock.mockResolvedValue({
      ok: true,
      tokenCount: 200,
      modelName: 'gemini-2.5-flash',
    });

    const session = await syncArticleCacheState(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
        articleContext: {
          title: 'Different article',
          url: 'https://example.com/different-article',
          bodyText: 'Different body',
          bodyHash: 'differenthash1234',
          source: 'readability',
          siteName: 'Example',
          textLength: 100,
        },
        articleCacheState: {
          status: 'active',
          cacheName: 'cachedContents/article-1',
          modelName: 'gemini-2.5-flash',
          articleUrl: 'https://example.com/article',
          articleIdentity: 'example::example article',
          articleHash: 'abc123def4567890',
        },
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
        allowAutoCreate: false,
      }
    );

    expect(deleteContextCacheMock).toHaveBeenCalledWith(
      'cachedContents/article-1',
      'http://127.0.0.1:9000'
    );
    expect(session.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'candidate',
        invalidationReason: 'article-identity-changed',
        articleIdentity: 'example::different article',
        articleUrl: 'https://example.com/different-article',
      })
    );
  });

  it('keeps a degraded state when remote deletion fails', async () => {
    deleteContextCacheMock.mockRejectedValue(new Error('delete failed'));

    const session = await invalidateArticleCache(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
        articleCacheState: {
          status: 'active',
          cacheName: 'cachedContents/article-1',
        },
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        reason: 'manual-delete',
        notice: 'Article cache was deleted manually for this tab.',
      }
    );

    expect(session.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'degraded',
        invalidationReason: 'manual-delete',
      })
    );
  });

  it('merges collected article context and clears stale page state on navigation', () => {
    const merged = mergeCollectedArticleContext(
      {
        items: [],
        modelOptions: [],
        lastAction: 'translation',
      },
      {
        ok: true,
        payload: {
          title: 'Example article',
          url: 'https://example.com/article',
          bodyText: 'Body',
          bodyHash: 'abc123def4567890',
          source: 'readability',
          textLength: 100,
        },
      }
    );

    const navigated = buildNavigatedSessionState(
      {
        ...merged,
        items: [
          {
            id: 'selection-1',
            source: 'text-selection',
            selection: {
              text: 'Selected text',
              rect: { left: 1, top: 2, width: 3, height: 4 },
              viewportWidth: 100,
              viewportHeight: 100,
              devicePixelRatio: 1,
              url: 'https://example.com/article',
              pageTitle: 'Example',
            },
            includeImage: false,
          },
        ],
        articleCacheState: {
          status: 'active',
          cacheName: 'cachedContents/article-1',
        },
      },
      'https://example.com/next'
    );

    expect(merged.articleContext?.title).toBe('Example article');
    expect(navigated.items).toEqual([]);
    expect(navigated.articleContext).toBeUndefined();
    expect(navigated.articleCacheState).toEqual(
      expect.objectContaining({
        status: 'active',
        cacheName: 'cachedContents/article-1',
      })
    );
  });
});