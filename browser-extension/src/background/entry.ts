import { ensurePhase0ContextMenu } from './menus/phase0ContextMenu';
import { runPhase0TranslationTest } from './usecases/runPhase0TranslationTest';
import { PHASE0_MENU_ID } from '../shared/config/phase0';

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

    void runPhase0TranslationTest(tab, info.selectionText ?? '');
  });
}