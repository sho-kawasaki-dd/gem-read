import { PHASE0_API_BASE_URL } from '../config/phase0';
import type {
  AnalysisAction,
  AnalyzeApiResponse,
  AnalyzeUsageMetrics,
  CacheStatusApiResponse,
  DegradedReason,
  ModelCatalogSource,
  ModelListApiResponse,
  ModelOption,
  PopupConnectionStatus,
  PopupStatusPayload,
  SelectionRect,
  SelectionSessionItem,
  SelectionSessionSource,
  TokenCountApiResponse,
} from '../contracts/messages';

interface AnalyzeSelectionMetadataItem {
  id: string;
  order: number;
  source: SelectionSessionSource;
  text: string;
  include_image: boolean;
  image_index: number | null;
  url: string;
  page_title: string;
  viewport_width: number;
  viewport_height: number;
  device_pixel_ratio: number;
  rect: SelectionRect;
}

interface AnalyzeSelectionMetadataPayload {
  url?: string;
  page_title?: string;
  viewport_width?: number;
  viewport_height?: number;
  device_pixel_ratio?: number;
  rect?: SelectionRect;
  items?: AnalyzeSelectionMetadataItem[];
}

interface AnalyzeTranslateRequestBody {
  text: string;
  images: string[];
  mode: AnalysisAction;
  model_name?: string;
  cache_name?: string;
  custom_prompt?: string;
  selection_metadata?: AnalyzeSelectionMetadataPayload;
}

interface RawAnalyzeApiResponse {
  ok: boolean;
  mode: AnalysisAction;
  translated_text: string;
  explanation: string | null;
  raw_response: string;
  used_mock: boolean;
  image_count: number;
  availability?: 'live' | 'mock';
  degraded_reason?: DegradedReason | null;
  selection_metadata?: Record<string, unknown> | null;
  usage?: RawAnalyzeUsageApiResponse | null;
}

interface RawAnalyzeUsageApiResponse {
  prompt_token_count?: number | null;
  cached_content_token_count?: number | null;
  candidates_token_count?: number | null;
  total_token_count?: number | null;
}

interface RawModelApiResponse {
  model_id: string;
  display_name: string;
}

interface RawModelListApiResponse {
  ok: boolean;
  models: RawModelApiResponse[];
  source: Extract<ModelCatalogSource, 'live' | 'config_fallback'>;
  availability: 'live' | 'degraded';
  detail?: string;
  degraded_reason?: DegradedReason | null;
}

interface RawHealthApiResponse {
  status: string;
}

interface RawCacheStatusApiResponse {
  ok: boolean;
  is_active: boolean;
  ttl_seconds?: number | null;
  token_count?: number | null;
  cache_name?: string | null;
  display_name?: string | null;
  model_name?: string | null;
  expire_time?: string | null;
}

interface RawTokenCountApiResponse {
  ok: boolean;
  token_count: number;
  model_name: string;
}

interface RawCreateCacheRequestBody {
  full_text: string;
  model_name?: string;
  display_name?: string;
}

export interface SendAnalyzeRequestOptions {
  action?: AnalysisAction;
  apiBaseUrl?: string;
  modelName?: string;
  cacheName?: string;
  customPrompt?: string;
}

export interface TokenCountRequestOptions {
  apiBaseUrl?: string;
  modelName?: string;
}

export interface CreateCacheRequestOptions {
  apiBaseUrl?: string;
  modelName?: string;
  displayName?: string;
}

export interface PopupBootstrapResult {
  status: PopupStatusPayload;
  models: ModelOption[];
}

/**
 * Background から browser_api へ送る HTTP payload をここで正規化する。
 * Content script は CSP の影響を受けやすいため、Local API 通信の詳細は shared gateway に寄せる。
 */
export async function sendAnalyzeTranslateRequest(
  sessionItems: SelectionSessionItem[],
  options: SendAnalyzeRequestOptions = {}
): Promise<AnalyzeApiResponse> {
  const apiBaseUrl = options.apiBaseUrl ?? PHASE0_API_BASE_URL;
  const action = options.action ?? 'translation';
  const requestBody = buildAnalyzeRequestBody(sessionItems, {
    action,
    modelName: options.modelName,
    cacheName: options.cacheName,
    customPrompt: options.customPrompt,
  });

  const response = await fetch(`${apiBaseUrl}/analyze/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API request failed (${response.status}): ${errorText}`
    );
  }

  const payload = (await response.json()) as RawAnalyzeApiResponse;
  return {
    ok: payload.ok,
    mode: payload.mode,
    translated_text: payload.translated_text,
    explanation: payload.explanation,
    raw_response: payload.raw_response,
    used_mock: payload.used_mock,
    image_count: payload.image_count,
    availability: payload.availability,
    degraded_reason: payload.degraded_reason,
    selection_metadata: payload.selection_metadata,
    usage: mapAnalyzeUsage(payload.usage),
  };
}

export function buildAnalyzeTextFromSessionItems(
  sessionItems: SelectionSessionItem[]
): string {
  return sessionItems
    .map((item) => item.selection.text.trim())
    .filter((text) => text.length > 0)
    .map((text, index) => `${index + 1}. ${text}`)
    .join('\n\n');
}

function buildAnalyzeRequestBody(
  sessionItems: SelectionSessionItem[],
  options: Pick<
    SendAnalyzeRequestOptions,
    'action' | 'modelName' | 'cacheName' | 'customPrompt'
  >
): AnalyzeTranslateRequestBody {
  if (sessionItems.length === 0) {
    throw new Error(
      'At least one session item is required before running analysis.'
    );
  }

  const images: string[] = [];
  const metadataItems = sessionItems.map((item, order) => {
    const shouldIncludeImage =
      item.includeImage && Boolean(item.previewImageUrl);
    const imageIndex = shouldIncludeImage
      ? images.push(item.previewImageUrl as string) - 1
      : null;

    return {
      id: item.id,
      order,
      source: item.source,
      text: item.selection.text.trim(),
      include_image: item.includeImage,
      image_index: imageIndex,
      url: item.selection.url,
      page_title: item.selection.pageTitle,
      viewport_width: item.selection.viewportWidth,
      viewport_height: item.selection.viewportHeight,
      device_pixel_ratio: item.selection.devicePixelRatio,
      rect: { ...item.selection.rect },
    } satisfies AnalyzeSelectionMetadataItem;
  });

  const text = buildAnalyzeTextFromSessionItems(sessionItems);
  const primarySelection = sessionItems[0]?.selection;

  return {
    text,
    images,
    mode: options.action ?? 'translation',
    model_name: options.modelName,
    cache_name: options.cacheName,
    custom_prompt: options.customPrompt,
    selection_metadata: primarySelection
      ? {
          url: primarySelection.url,
          page_title: primarySelection.pageTitle,
          viewport_width: primarySelection.viewportWidth,
          viewport_height: primarySelection.viewportHeight,
          device_pixel_ratio: primarySelection.devicePixelRatio,
          rect: { ...primarySelection.rect },
          items: metadataItems,
        }
      : { items: metadataItems },
  };
}

/**
 * Popup は health と model catalog をまとめて確認し、UI 初期表示に必要な状態を一度で得る。
 * model 取得に失敗しても設定画面は開けるよう、degraded な bootstrap 結果を返して描画を継続する。
 */
export async function fetchPopupBootstrap(
  apiBaseUrl: string = PHASE0_API_BASE_URL
): Promise<PopupBootstrapResult> {
  await fetchHealth(apiBaseUrl);

  try {
    const modelCatalog = await fetchModelCatalog(apiBaseUrl);
    return {
      status: {
        connectionStatus: getConnectionStatus(modelCatalog),
        availability: modelCatalog.availability,
        apiBaseUrl,
        checkedAt: new Date().toISOString(),
        detail: modelCatalog.detail,
        modelSource: modelCatalog.source,
        degradedReason: modelCatalog.degradedReason,
      },
      models: modelCatalog.models,
    };
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : 'Failed to fetch model list.';
    return {
      status: {
        connectionStatus: 'mock-mode',
        availability: 'degraded',
        apiBaseUrl,
        checkedAt: new Date().toISOString(),
        detail,
        modelSource: 'storage_fallback',
        degradedReason: 'config-fallback',
      },
      models: [],
    };
  }
}

async function fetchHealth(apiBaseUrl: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/health`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API health check failed (${response.status}): ${errorText}`
    );
  }

  const payload = (await response.json()) as RawHealthApiResponse;
  if (payload.status !== 'ok') {
    throw new Error(`Unexpected Local API health response: ${payload.status}`);
  }
}

async function fetchModelCatalog(
  apiBaseUrl: string
): Promise<ModelListApiResponse> {
  const response = await fetch(`${apiBaseUrl}/models`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API model request failed (${response.status}): ${errorText}`
    );
  }

  const payload = (await response.json()) as RawModelListApiResponse;
  return {
    ok: payload.ok,
    models: payload.models.map((model) => ({
      modelId: model.model_id,
      displayName: model.display_name,
    })),
    source: payload.source,
    availability: payload.availability,
    detail: payload.detail,
    degradedReason: payload.degraded_reason ?? undefined,
  };
}

function getConnectionStatus(
  modelCatalog: ModelListApiResponse
): PopupConnectionStatus {
  // live catalog が返ってこなくても mock/config fallback なら接続自体は成立しているため、mock-mode として扱う。
  if (modelCatalog.availability === 'live' && modelCatalog.source === 'live') {
    return 'reachable';
  }

  return 'mock-mode';
}

export async function countTokens(
  text: string,
  options: TokenCountRequestOptions = {}
): Promise<TokenCountApiResponse> {
  const apiBaseUrl = options.apiBaseUrl ?? PHASE0_API_BASE_URL;
  const response = await fetch(`${apiBaseUrl}/tokens/count`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      model_name: options.modelName,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API token request failed (${response.status}): ${errorText}`
    );
  }

  const payload = (await response.json()) as RawTokenCountApiResponse;
  return {
    ok: payload.ok,
    tokenCount: payload.token_count,
    modelName: payload.model_name,
  };
}

export async function createContextCache(
  fullText: string,
  options: CreateCacheRequestOptions = {}
): Promise<CacheStatusApiResponse> {
  const apiBaseUrl = options.apiBaseUrl ?? PHASE0_API_BASE_URL;
  const requestBody: RawCreateCacheRequestBody = {
    full_text: fullText,
    model_name: options.modelName,
    display_name: options.displayName,
  };

  const response = await fetch(`${apiBaseUrl}/cache/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API cache create failed (${response.status}): ${errorText}`
    );
  }

  return mapCacheStatusResponse(
    (await response.json()) as RawCacheStatusApiResponse
  );
}

export async function deleteContextCache(
  cacheName: string,
  apiBaseUrl: string = PHASE0_API_BASE_URL
): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/cache/${encodeURIComponent(cacheName)}`,
    {
      method: 'DELETE',
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Local API cache delete failed (${response.status}): ${errorText}`
    );
  }
}

function mapCacheStatusResponse(
  payload: RawCacheStatusApiResponse
): CacheStatusApiResponse {
  return {
    ok: payload.ok,
    isActive: payload.is_active,
    ttlSeconds: payload.ttl_seconds ?? undefined,
    tokenCount: payload.token_count ?? undefined,
    cacheName: payload.cache_name ?? undefined,
    displayName: payload.display_name ?? undefined,
    modelName: payload.model_name ?? undefined,
    expireTime: payload.expire_time ?? undefined,
  };
}

function mapAnalyzeUsage(
  usage: RawAnalyzeUsageApiResponse | null | undefined
): AnalyzeUsageMetrics | undefined {
  if (!usage) {
    return undefined;
  }

  return {
    promptTokenCount: usage.prompt_token_count ?? undefined,
    cachedContentTokenCount: usage.cached_content_token_count ?? undefined,
    candidatesTokenCount: usage.candidates_token_count ?? undefined,
    totalTokenCount: usage.total_token_count ?? undefined,
  };
}
