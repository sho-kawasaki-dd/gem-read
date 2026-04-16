import type {
  CacheOverlaySessionMessage,
  ContentScriptMessage,
  RunOverlayActionResponse,
  SeedOverlaySessionResponse,
} from '../shared/contracts/messages';
import { renderOverlay } from './overlay/renderOverlay';
import { collectSelection, startSelectionTracking } from './selection/snapshotStore';

export function registerContentRuntime(): void {
  console.log('Gem Read Content Script Loaded');
  startSelectionTracking();

  chrome.runtime.onMessage.addListener((message: ContentScriptMessage, _sender, sendResponse) => {
    if (message.type === 'phase0.collectSelection') {
      sendResponse(collectSelection(message.fallbackText));
      return false;
    }

    if (message.type === 'phase0.renderOverlay') {
      renderOverlay(message.payload);
    }

    if (message.type === 'phase1.seedOverlaySession') {
      void handleSeedOverlaySession(message, sendResponse);
      return true;
    }

    if (message.type === 'phase1.invokeOverlayAction') {
      void handleInvokeOverlayAction(message, sendResponse);
      return true;
    }

    return false;
  });
}

async function handleSeedOverlaySession(
  message: Extract<ContentScriptMessage, { type: 'phase1.seedOverlaySession' }>,
  sendResponse: (response: SeedOverlaySessionResponse) => void,
): Promise<void> {
  const selection = collectSelection(message.payload.fallbackText);
  if (!selection.ok || !selection.payload) {
    sendResponse({
      ok: false,
      error: selection.error ?? 'Failed to collect selection for overlay session.',
    });
    return;
  }

  const runtimeMessage: CacheOverlaySessionMessage = {
    type: 'phase1.cacheOverlaySession',
    payload: {
      selection: selection.payload,
      previewImageUrl: message.payload.previewImageUrl,
      cropDurationMs: message.payload.cropDurationMs,
      modelOptions: message.payload.modelOptions ?? [],
    },
  };

  const response = await chrome.runtime.sendMessage(runtimeMessage) as SeedOverlaySessionResponse | undefined;
  sendResponse(response ?? { ok: true });
}

async function handleInvokeOverlayAction(
  message: Extract<ContentScriptMessage, { type: 'phase1.invokeOverlayAction' }>,
  sendResponse: (response: RunOverlayActionResponse) => void,
): Promise<void> {
  const response = await chrome.runtime.sendMessage({
    type: 'phase1.runOverlayAction',
    payload: message.payload,
  }) as RunOverlayActionResponse | undefined;
  sendResponse(response ?? { ok: true });
}