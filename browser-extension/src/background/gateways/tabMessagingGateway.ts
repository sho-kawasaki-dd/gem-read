import type {
  CollectSelectionMessage,
  ContentScriptMessage,
  OverlayPayload,
  RenderOverlayMessage,
  SelectionCaptureResponse,
} from '../../shared/contracts/messages';

export async function collectSelection(
  tabId: number,
  fallbackText: string,
): Promise<SelectionCaptureResponse> {
  const message: CollectSelectionMessage = {
    type: 'phase0.collectSelection',
    fallbackText,
  };
  return chrome.tabs.sendMessage(tabId, message);
}

export async function renderOverlay(tabId: number, payload: OverlayPayload): Promise<void> {
  const message: RenderOverlayMessage = {
    type: 'phase0.renderOverlay',
    payload,
  };
  await chrome.tabs.sendMessage(tabId, message as ContentScriptMessage);
}