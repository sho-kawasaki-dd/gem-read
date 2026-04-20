import type {
  ArticleCacheInvalidationReason,
  ArticleCacheState,
  ArticleContext,
  ArticleContextResponse,
} from '../../shared/contracts/messages';
import {
  countTokens,
  createContextCache,
  deleteContextCache,
} from '../../shared/gateways/localApiGateway';
import type { SelectionAnalysisSession } from './analysisSessionStore';

const AUTO_CACHE_MIN_TEXT_LENGTH = 4000;
const AUTO_CACHE_MIN_TOKEN_ESTIMATE = 1200;
const CACHE_DISPLAY_NAME_PREFIX = 'browser-extension:';
const AUTO_CREATE_DISABLED_NOTICE =
  'Automatic full article cache creation is disabled in popup settings.';

export interface SyncArticleCacheOptions {
  apiBaseUrl: string;
  modelName?: string;
  allowAutoCreate?: boolean;
  autoCreateDisabledBySetting?: boolean;
}

export interface InvalidateArticleCacheOptions {
  apiBaseUrl: string;
  reason: ArticleCacheInvalidationReason;
  notice: string;
}

export async function syncArticleCacheState(
  session: SelectionAnalysisSession,
  options: SyncArticleCacheOptions
): Promise<SelectionAnalysisSession> {
  const resolvedModelName = normalizeModelName(
    options.modelName ?? session.lastModelName
  );
  const resolvedModelKey = normalizeModelKey(resolvedModelName);
  const articleContext = session.articleContext;
  const now = new Date().toISOString();
  const existingState = session.articleCacheState;
  const existingModelKey = normalizeModelKey(existingState?.modelName);
  const shouldInvalidateCachedModel = Boolean(
    existingState?.cacheName &&
    existingModelKey &&
    resolvedModelKey &&
    existingModelKey !== resolvedModelKey
  );

  if (!articleContext) {
    if (!existingState) {
      return session.articleContextError
        ? {
            ...session,
            articleCacheState: {
              status: 'idle',
              autoCreateEligible: false,
              notice: session.articleContextError,
              lastValidatedAt: now,
            },
          }
        : session;
    }

    if (existingState.cacheName) {
      return {
        ...session,
        articleCacheState: await invalidateTrackedState(existingState, {
          apiBaseUrl: options.apiBaseUrl,
          reason: 'extraction-failed',
          notice:
            session.articleContextError ??
            'Article cache was cleared because article extraction failed.',
        }),
      };
    }

    return {
      ...session,
      articleCacheState: {
        ...existingState,
        status: existingState.status === 'active' ? 'invalidated' : 'idle',
        autoCreateEligible: false,
        notice: session.articleContextError ?? existingState.notice,
        lastValidatedAt: now,
      },
    };
  }

  let nextState = buildSeedCacheState(
    existingState,
    articleContext,
    resolvedModelName,
    now
  );
  nextState = refreshTrackedCacheTtl(nextState, articleContext, now);

  if (shouldInvalidateCachedModel) {
    console.warn('[GemRead] articleCache: model changed → invalidating', {
      cachedModel: existingState?.modelName,
      resolvedModel: resolvedModelName,
    });
    nextState = await invalidateTrackedState(nextState, {
      apiBaseUrl: options.apiBaseUrl,
      reason: 'model-changed',
      notice: 'Article cache was cleared because the selected model changed.',
    });
    if (nextState.status === 'degraded') {
      return {
        ...session,
        articleCacheState: nextState,
      };
    }

    nextState = bindTrackedArticleState(nextState, articleContext);
  }

  if (shouldInvalidateForArticleChange(nextState, articleContext)) {
    console.warn('[GemRead] articleCache: article changed → invalidating', {
      reason: 'article-identity-changed',
      cachedIdentity: nextState.articleIdentity,
      currentIdentity: buildArticleIdentity(articleContext),
      cachedUrl: nextState.articleUrl,
      currentUrl: articleContext.url,
      cachedHash: nextState.articleHash,
      currentHash: articleContext.bodyHash,
    });
    nextState = await invalidateTrackedState(nextState, {
      apiBaseUrl: options.apiBaseUrl,
      reason: 'article-identity-changed',
      notice:
        'Article cache was cleared because the extracted article changed.',
    });
    if (nextState.status === 'degraded') {
      return {
        ...session,
        articleCacheState: nextState,
      };
    }

    nextState = bindTrackedArticleState(nextState, articleContext);
  } else {
    console.debug('[GemRead] articleCache: no article change detected', {
      cacheName: nextState.cacheName,
      cachedIdentity: nextState.articleIdentity,
      currentIdentity: buildArticleIdentity(articleContext),
      cachedUrl: nextState.articleUrl,
      currentUrl: articleContext.url,
      cachedHash: nextState.articleHash,
      currentHash: articleContext.bodyHash,
    });
  }

  if (!resolvedModelName) {
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: 'idle',
        autoCreateEligible: false,
        notice: 'Choose a Gemini model before article cache can be managed.',
        lastValidatedAt: now,
      },
    };
  }

  if (!isCacheSupportedModel(resolvedModelName)) {
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: 'unsupported',
        autoCreateEligible: false,
        notice:
          'The current model is not expected to support context cache creation.',
        lastValidatedAt: now,
      },
    };
  }

  const tokenEstimateResult = await resolveTokenEstimate(
    nextState,
    articleContext,
    resolvedModelName,
    options.apiBaseUrl,
    now
  );
  nextState = tokenEstimateResult.state;

  if (nextState.status === 'active') {
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        autoCreateEligible: true,
      },
    };
  }

  if (!nextState.autoCreateEligible) {
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: nextState.status === 'degraded' ? 'degraded' : 'candidate',
        notice:
          nextState.notice ??
          'Article context is below the automatic cache creation threshold.',
        lastValidatedAt: now,
      },
    };
  }

  if (!options.allowAutoCreate) {
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: 'candidate',
        notice: options.autoCreateDisabledBySetting
          ? AUTO_CREATE_DISABLED_NOTICE
          : 'Article context is eligible for automatic cache creation.',
        lastValidatedAt: now,
      },
    };
  }

  console.info('[GemRead] articleCache: auto-creating cache', {
    url: articleContext.url,
    textLength: articleContext.textLength,
    tokenEstimate: nextState.tokenEstimate,
    model: resolvedModelName,
  });

  try {
    const createdStatus = await createContextCache(articleContext.bodyText, {
      apiBaseUrl: options.apiBaseUrl,
      modelName: resolvedModelName,
      displayName: buildCacheDisplayName(articleContext),
    });
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: 'active',
        cacheName: createdStatus.cacheName,
        displayName:
          createdStatus.displayName ?? buildCacheDisplayName(articleContext),
        modelName: normalizeModelName(
          createdStatus.modelName ?? resolvedModelName
        ),
        articleUrl: articleContext.url,
        articleIdentity: buildArticleIdentity(articleContext),
        articleHash: articleContext.bodyHash,
        tokenCount: createdStatus.tokenCount,
        ttlSeconds: createdStatus.ttlSeconds,
        expireTime: createdStatus.expireTime,
        invalidationReason: undefined,
        notice: 'Article cache created automatically for the current tab.',
        lastValidatedAt: now,
      },
    };
  } catch (error) {
    const message = toErrorMessage(error);
    return {
      ...session,
      articleCacheState: {
        ...nextState,
        status: isUnsupportedCacheError(message) ? 'unsupported' : 'degraded',
        autoCreateEligible: false,
        notice: `Article cache could not be created: ${message}`,
        lastValidatedAt: now,
      },
    };
  }
}

export async function invalidateArticleCache(
  session: SelectionAnalysisSession,
  options: InvalidateArticleCacheOptions
): Promise<SelectionAnalysisSession> {
  const existingState = session.articleCacheState;
  if (!existingState) {
    return {
      ...session,
      articleCacheState: {
        status: 'invalidated',
        autoCreateEligible: false,
        invalidationReason: options.reason,
        notice: options.notice,
        lastValidatedAt: new Date().toISOString(),
      },
    };
  }

  return {
    ...session,
    articleCacheState: await invalidateTrackedState(existingState, options),
  };
}

export function mergeCollectedArticleContext(
  session: SelectionAnalysisSession,
  result: ArticleContextResponse | { ok: false; error?: string }
): SelectionAnalysisSession {
  if (result.ok && result.payload) {
    return {
      ...session,
      articleContext: result.payload,
      articleContextError: undefined,
    };
  }

  if (session.articleContext) {
    return {
      ...session,
      articleContextError: result.error,
    };
  }

  return {
    ...session,
    articleContext: undefined,
    articleContextError: result.error,
  };
}

export function buildNavigatedSessionState(
  session: SelectionAnalysisSession,
  nextUrl: string
): SelectionAnalysisSession {
  // 選択内容とページコンテキストはクリアするが、キャッシュ状態はそのまま保持する。
  // SPA ではセクション切り替えで URL が変わるため、ここでキャッシュを削除すると
  // セクション移動のたびに再作成が走る。次回の同期で article identity を比較し、
  // 次回の syncArticleCacheState に委ねる。
  return {
    ...session,
    items: [],
    articleContext: undefined,
    articleContextError: `Page changed to ${nextUrl}. Article context will be refreshed on the next run.`,
  };
}

function buildSeedCacheState(
  existingState: ArticleCacheState | undefined,
  articleContext: ArticleContext,
  resolvedModelName: string | undefined,
  now: string
): ArticleCacheState {
  const currentArticleIdentity = buildArticleIdentity(articleContext);
  const tracksActiveCache = Boolean(existingState?.cacheName);

  return {
    status: existingState?.status ?? 'idle',
    autoCreateEligible: existingState?.autoCreateEligible,
    cacheName: existingState?.cacheName,
    displayName: existingState?.displayName,
    modelName: resolvedModelName ?? existingState?.modelName,
    articleUrl: tracksActiveCache
      ? (existingState?.articleUrl ?? articleContext.url)
      : articleContext.url,
    articleIdentity: tracksActiveCache
      ? existingState?.articleIdentity
      : currentArticleIdentity,
    articleHash: tracksActiveCache
      ? (existingState?.articleHash ?? articleContext.bodyHash)
      : articleContext.bodyHash,
    tokenEstimate: existingState?.tokenEstimate,
    tokenCount: existingState?.tokenCount,
    ttlSeconds: existingState?.ttlSeconds,
    expireTime: existingState?.expireTime,
    invalidationReason: existingState?.invalidationReason,
    notice: existingState?.notice,
    lastValidatedAt: now,
  };
}

async function resolveTokenEstimate(
  state: ArticleCacheState,
  articleContext: ArticleContext,
  modelName: string,
  apiBaseUrl: string,
  now: string
): Promise<{ state: ArticleCacheState }> {
  const eligibleByTextLength =
    articleContext.textLength >= AUTO_CACHE_MIN_TEXT_LENGTH;

  try {
    const tokenResult = await countTokens(articleContext.bodyText, {
      apiBaseUrl,
      modelName,
    });
    const autoCreateEligible =
      eligibleByTextLength ||
      tokenResult.tokenCount >= AUTO_CACHE_MIN_TOKEN_ESTIMATE;

    return {
      state: {
        ...state,
        tokenEstimate: tokenResult.tokenCount,
        autoCreateEligible,
        notice: autoCreateEligible
          ? state.notice
          : 'Article context is below the automatic cache creation threshold.',
        lastValidatedAt: now,
      },
    };
  } catch (error) {
    return {
      state: {
        ...state,
        autoCreateEligible: eligibleByTextLength,
        notice: eligibleByTextLength
          ? state.notice
          : `Token estimate is unavailable: ${toErrorMessage(error)}`,
        lastValidatedAt: now,
      },
    };
  }
}

async function invalidateTrackedState(
  state: ArticleCacheState,
  options: InvalidateArticleCacheOptions
): Promise<ArticleCacheState> {
  if (!state.cacheName) {
    return {
      ...state,
      status: 'invalidated',
      autoCreateEligible: false,
      invalidationReason: options.reason,
      notice: options.notice,
      lastValidatedAt: new Date().toISOString(),
    };
  }

  try {
    await deleteContextCache(state.cacheName, options.apiBaseUrl);
    return {
      ...state,
      status: 'invalidated',
      autoCreateEligible: false,
      cacheName: undefined,
      tokenCount: undefined,
      ttlSeconds: undefined,
      expireTime: undefined,
      invalidationReason: options.reason,
      notice: options.notice,
      lastValidatedAt: new Date().toISOString(),
    };
  } catch (error) {
    return {
      ...state,
      status: 'degraded',
      autoCreateEligible: false,
      invalidationReason: options.reason,
      notice: `${options.notice} Remote cache deletion failed: ${toErrorMessage(error)}`,
      lastValidatedAt: new Date().toISOString(),
    };
  }
}

function shouldInvalidateForArticleChange(
  state: ArticleCacheState,
  articleContext: ArticleContext
): boolean {
  if (!state.cacheName) {
    return false;
  }

  const currentIdentity = buildArticleIdentity(articleContext);
  if (state.articleIdentity) {
    return state.articleIdentity !== currentIdentity;
  }

  return Boolean(
    state.articleHash && state.articleHash !== articleContext.bodyHash
  );
}

function bindTrackedArticleState(
  state: ArticleCacheState,
  articleContext: ArticleContext
): ArticleCacheState {
  return {
    ...state,
    articleUrl: articleContext.url,
    articleIdentity: buildArticleIdentity(articleContext),
    articleHash: articleContext.bodyHash,
  };
}

function refreshTrackedCacheTtl(
  state: ArticleCacheState,
  articleContext: ArticleContext,
  now: string
): ArticleCacheState {
  if (!state.cacheName || !state.expireTime) {
    return state;
  }

  const expireTimeMs = parseCacheExpireTimeMs(state.expireTime);
  if (expireTimeMs === undefined) {
    return state;
  }

  const remainingMs = expireTimeMs - new Date(now).getTime();

  if (remainingMs <= 0) {
    return bindTrackedArticleState(
      {
        ...state,
        status: 'invalidated',
        autoCreateEligible: false,
        cacheName: undefined,
        tokenCount: undefined,
        ttlSeconds: undefined,
        expireTime: undefined,
        invalidationReason: 'ttl-expired',
        notice: 'Article cache expired and will be recreated when needed.',
        lastValidatedAt: now,
      },
      articleContext
    );
  }

  return {
    ...state,
    ttlSeconds: Math.max(0, Math.floor(remainingMs / 1000)),
    lastValidatedAt: now,
  };
}

const ISO_TIMEZONE_SUFFIX_PATTERN = /(z|[+-]\d{2}:\d{2})$/i;

export function parseCacheExpireTimeMs(
  expireTime: string | undefined
): number | undefined {
  const normalized = expireTime?.trim();
  if (!normalized) {
    return undefined;
  }

  const utcCandidate = ISO_TIMEZONE_SUFFIX_PATTERN.test(normalized)
    ? normalized
    : `${normalized}Z`;
  const parsedMs = Date.parse(utcCandidate);

  return Number.isNaN(parsedMs) ? undefined : parsedMs;
}

function buildArticleIdentity(articleContext: ArticleContext): string {
  const normalizedSiteName = normalizeIdentityPart(articleContext.siteName);
  const normalizedTitle = normalizeIdentityPart(articleContext.title);
  const normalizedByline = normalizeIdentityPart(articleContext.byline);

  if (normalizedSiteName && normalizedTitle) {
    return normalizedByline
      ? `${normalizedSiteName}::${normalizedTitle}::${normalizedByline}`
      : `${normalizedSiteName}::${normalizedTitle}`;
  }

  const normalizedUrl = normalizeArticleUrl(articleContext.url);
  if (normalizedUrl) {
    return normalizedTitle
      ? `${normalizedUrl}::${normalizedTitle}`
      : normalizedUrl;
  }

  return normalizedTitle || articleContext.bodyHash;
}

function normalizeIdentityPart(value: string | undefined): string | undefined {
  const normalized = value?.trim().toLowerCase().replace(/\s+/g, ' ');
  return normalized || undefined;
}

function normalizeArticleUrl(url: string | undefined): string | undefined {
  if (!url) {
    return undefined;
  }

  try {
    const parsedUrl = new URL(url);
    const normalizedPath = parsedUrl.pathname.replace(/\/+$/, '') || '/';
    return `${parsedUrl.host.toLowerCase()}${normalizedPath}`;
  } catch {
    return undefined;
  }
}

function buildCacheDisplayName(articleContext: ArticleContext): string {
  const normalizedTitle = articleContext.title
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 72);
  return `${CACHE_DISPLAY_NAME_PREFIX}${normalizedTitle || 'untitled-article'}`;
}

function isCacheSupportedModel(modelName: string): boolean {
  return !/lite/i.test(modelName);
}

function isUnsupportedCacheError(message: string): boolean {
  const normalized = message.toLowerCase();
  return (
    message.includes('サポートしていません') ||
    normalized.includes('does not support context cache') ||
    normalized.includes('not support') ||
    normalized.includes('not supported for createcachedcontent')
  );
}

function normalizeModelName(modelName: string | undefined): string | undefined {
  const normalized = modelName?.trim();
  return normalized ? normalized : undefined;
}

function normalizeModelKey(modelName: string | undefined): string | undefined {
  const normalized = normalizeModelName(modelName);
  if (!normalized) {
    return undefined;
  }

  return normalized.replace(/^models\//i, '');
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Unexpected article cache error.';
}
