import { collectSelection, renderOverlay } from '../gateways/tabMessagingGateway';
import { sendAnalyzeTranslateRequest } from '../gateways/localApiGateway';
import { cropSelectionImage } from '../services/cropSelectionImage';

export async function runPhase0TranslationTest(
  tab: chrome.tabs.Tab,
  fallbackSelectionText: string,
): Promise<void> {
  const tabId = tab.id;
  if (tabId === undefined) {
    return;
  }

  try {
    await renderOverlay(tabId, {
      status: 'loading',
      selectedText: fallbackSelectionText,
    });

    const selection = await collectSelection(tabId, fallbackSelectionText);
    if (!selection.ok || !selection.payload) {
      await renderOverlay(tabId, {
        status: 'error',
        selectedText: fallbackSelectionText,
        error: selection.error ?? '選択テキストを取得できませんでした。',
      });
      return;
    }

    const resolvedSelection = {
      ...selection.payload,
      text: fallbackSelectionText.trim() || selection.payload.text,
    };

    const screenshotDataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
      format: 'png',
    });
    const cropResult = await cropSelectionImage(
      screenshotDataUrl,
      resolvedSelection,
    );
    const apiResponse = await sendAnalyzeTranslateRequest(resolvedSelection, cropResult.imageDataUrl);

    await renderOverlay(tabId, {
      status: 'success',
      selectedText: resolvedSelection.text,
      translatedText: apiResponse.translated_text,
      explanation: apiResponse.explanation,
      previewImageUrl: cropResult.imageDataUrl,
      usedMock: apiResponse.used_mock,
      imageCount: apiResponse.image_count,
      timingMs: cropResult.durationMs,
      rawResponse: apiResponse.raw_response,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : '不明なエラーが発生しました。';
    await renderOverlay(tabId, {
      status: 'error',
      selectedText: fallbackSelectionText,
      error: message,
    });
  }
}