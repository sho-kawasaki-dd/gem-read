import type { ContentScriptMessage } from '../shared/contracts/messages';
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

    return false;
  });
}