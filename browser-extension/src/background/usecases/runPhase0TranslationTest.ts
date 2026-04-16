import { runSelectionAnalysis } from './runSelectionAnalysis';

export async function runPhase0TranslationTest(
  tab: chrome.tabs.Tab,
  fallbackSelectionText: string,
): Promise<void> {
  await runSelectionAnalysis(tab, fallbackSelectionText, {
    action: 'translation',
  });
}