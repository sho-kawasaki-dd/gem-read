import { ensurePhase0ContextMenu } from './menus/phase0ContextMenu';
import { setAnalysisSession } from './services/analysisSessionStore';
import { runSelectionAnalysis } from './usecases/runSelectionAnalysis';
import { PHASE0_MENU_ID } from '../shared/config/phase0';
import type {
  BackgroundRuntimeMessage,
  RunOverlayActionResponse,
} from '../shared/contracts/messages';

/**
 * Background runtime は権限が必要な処理の集約点であり、Local API 通信もここを通す。
 * Content script から直接 localhost を叩かせないことで、対象ページの CSP と権限境界を横断しない。
 */
export function registerBackgroundRuntime(): void {
  console.log('Gem Read Background Service Worker Loaded');

  chrome.runtime.onInstalled.addListener(() => {
    void ensurePhase0ContextMenu();
  });

  chrome.runtime.onStartup.addListener(() => {
    void ensurePhase0ContextMenu();
  });

  chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId !== PHASE0_MENU_ID || !tab?.id) {
      return;
    }

    void runSelectionAnalysis(tab, info.selectionText ?? '', {
      action: 'translation',
    });
  });

  chrome.runtime.onMessage.addListener(
    (message: BackgroundRuntimeMessage, sender, sendResponse) => {
      if (
        message.type === 'phase1.cacheOverlaySession' &&
        sender.tab?.id !== undefined
      ) {
        // Overlay 上の再実行は再選択を要求しないため、直前の selection/crop 結果を tab 単位で保持する。
        setAnalysisSession(sender.tab.id, {
          selection: message.payload.selection,
          previewImageUrl: message.payload.previewImageUrl,
          cropDurationMs: message.payload.cropDurationMs,
          modelOptions: message.payload.modelOptions,
          lastAction: 'translation',
        });
        sendResponse({ ok: true });
        return false;
      }

      if (message.type !== 'phase1.runOverlayAction' || !sender.tab) {
        return false;
      }

      void handleOverlayAction(message, sender.tab, sendResponse);
      return true;
    }
  );
}

async function handleOverlayAction(
  message: BackgroundRuntimeMessage,
  tab: chrome.tabs.Tab,
  sendResponse: (response: RunOverlayActionResponse) => void
): Promise<void> {
  try {
    // Overlay の action button は capture をやり直さず、既存 session の再利用だけ background に依頼する。
    await runSelectionAnalysis(tab, '', {
      action: message.payload.action,
      modelName: message.payload.modelName,
      customPrompt: message.payload.customPrompt,
      reuseCachedSession: true,
    });
    sendResponse({ ok: true });
  } catch (error) {
    sendResponse({
      ok: false,
      error: error instanceof Error ? error.message : 'Overlay action failed.',
    });
  }
}
