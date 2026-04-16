import { runSelectionAnalysis } from './runSelectionAnalysis';

/**
 * Phase 0 の context menu は translation 固定で共通フローを起動する。
 * 初回 capture の入口を一本化しておくと、Phase 1 以降も分岐を runSelectionAnalysis に集約できる。
 */
export async function runPhase0TranslationTest(
  tab: chrome.tabs.Tab,
  fallbackSelectionText: string
): Promise<void> {
  await runSelectionAnalysis(tab, fallbackSelectionText, {
    action: 'translation',
  });
}
