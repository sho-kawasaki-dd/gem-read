export type OverlayStatus = 'loading' | 'success' | 'error';

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
  mode: string;
  translated_text: string;
  explanation: string | null;
  raw_response: string;
  used_mock: boolean;
  image_count: number;
}

export interface OverlayPayload {
  status: OverlayStatus;
  selectedText?: string;
  translatedText?: string;
  explanation?: string | null;
  previewImageUrl?: string;
  error?: string;
  usedMock?: boolean;
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