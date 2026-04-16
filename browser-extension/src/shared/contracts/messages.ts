export type OverlayStatus = 'loading' | 'success' | 'error';
export type AnalysisAction = 'translation' | 'translation_with_explanation' | 'custom_prompt';
export type PopupConnectionStatus = 'reachable' | 'mock-mode' | 'unreachable';
export type RuntimeAvailability = 'live' | 'mock' | 'degraded';
export type DegradedReason = 'config-fallback' | 'mock-response' | 'offline' | 'unknown';
export type ModelCatalogSource = 'live' | 'config_fallback' | 'storage_fallback';

export interface SelectionRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface SelectionCapturePayload {
  text: string;
  rect: SelectionRect;
  viewportWidth: number;
  viewportHeight: number;
  devicePixelRatio: number;
  url: string;
  pageTitle: string;
}

export interface SelectionCaptureResponse {
  ok: boolean;
  payload?: SelectionCapturePayload;
  error?: string;
}

export interface AnalyzeApiResponse {
  ok: boolean;
  mode: AnalysisAction;
  translated_text: string;
  explanation: string | null;
  raw_response: string;
  used_mock: boolean;
  image_count: number;
  availability?: RuntimeAvailability;
  degraded_reason?: DegradedReason | null;
  selection_metadata?: Record<string, unknown> | null;
}

export interface AnalyzeRequestOptions {
  action: AnalysisAction;
  modelName?: string;
  customPrompt?: string;
}

export interface ModelOption {
  modelId: string;
  displayName: string;
}

export interface ModelListApiResponse {
  ok: boolean;
  models: ModelOption[];
  source: ModelCatalogSource;
  availability: RuntimeAvailability;
  detail?: string;
  degradedReason?: DegradedReason;
}

export interface PopupStatusPayload {
  connectionStatus: PopupConnectionStatus;
  availability: RuntimeAvailability;
  apiBaseUrl: string;
  checkedAt?: string;
  detail?: string;
  modelSource?: ModelCatalogSource;
  degradedReason?: DegradedReason;
}

export interface OverlayPayload {
  status: OverlayStatus;
  action?: AnalysisAction;
  modelName?: string;
  customPrompt?: string;
  selectedText?: string;
  translatedText?: string;
  explanation?: string | null;
  previewImageUrl?: string;
  error?: string;
  usedMock?: boolean;
  availability?: RuntimeAvailability;
  degradedReason?: DegradedReason;
  imageCount?: number;
  timingMs?: number;
  rawResponse?: string;
}

export interface CollectSelectionMessage {
  type: 'phase0.collectSelection';
  fallbackText?: string;
}

export interface RenderOverlayMessage {
  type: 'phase0.renderOverlay';
  payload: OverlayPayload;
}

export type ContentScriptMessage =
  | CollectSelectionMessage
  | RenderOverlayMessage;