import type { ExtensionSettings } from '../../shared/config/phase0';
import type {
  AnalysisAction,
  AnalyzeRequestOptions,
  ModelOption,
  SelectionCapturePayload,
} from '../../shared/contracts/messages';
import { loadExtensionSettings } from '../../shared/storage/settingsStorage';
import { sendAnalyzeTranslateRequest } from '../gateways/localApiGateway';
import { collectSelection, renderOverlay } from '../gateways/tabMessagingGateway';
import {
  getAnalysisSession,
  setAnalysisSession,
  type SelectionAnalysisSession,
} from '../services/analysisSessionStore';
import { cropSelectionImage } from '../services/cropSelectionImage';

export interface RunSelectionAnalysisOptions {
  action?: AnalysisAction;
  apiBaseUrl?: string;
  modelName?: string;
  customPrompt?: string;
  reuseCachedSession?: boolean;
}

export async function runSelectionAnalysis(
  tab: chrome.tabs.Tab,
  fallbackSelectionText: string,
  options: RunSelectionAnalysisOptions = {},
): Promise<void> {
  const tabId = tab.id;
  if (tabId === undefined) {
    return;
  }

  const settings = await loadExtensionSettings();
  const resolvedRequestOptions = resolveAnalyzeRequestOptions(settings, options);
  const modelOptions = buildModelOptions(settings);
  const cachedSession = options.reuseCachedSession ? getCachedSession(tabId) : undefined;

  try {
    await renderOverlay(tabId, {
      status: 'loading',
      action: resolvedRequestOptions.action,
      modelName: resolvedRequestOptions.modelName,
      modelOptions,
      customPrompt: resolvedRequestOptions.customPrompt,
      sessionReady: Boolean(cachedSession),
      selectedText: fallbackSelectionText,
    });

    const session = cachedSession ?? await createFreshSession(tab, tabId, fallbackSelectionText, modelOptions);

    const apiResponse = await sendAnalyzeTranslateRequest(
      session.selection,
      session.previewImageUrl,
      resolvedRequestOptions,
    );

    setAnalysisSession(tabId, {
      ...session,
      lastAction: apiResponse.mode,
      lastModelName: resolvedRequestOptions.modelName,
      lastCustomPrompt: resolvedRequestOptions.customPrompt,
      modelOptions,
    });

    await renderOverlay(tabId, {
      status: 'success',
      action: apiResponse.mode,
      modelName: resolvedRequestOptions.modelName,
      modelOptions,
      customPrompt: resolvedRequestOptions.customPrompt,
      sessionReady: true,
      selectedText: session.selection.text,
      translatedText: apiResponse.translated_text,
      explanation: apiResponse.explanation,
      previewImageUrl: session.previewImageUrl,
      usedMock: apiResponse.used_mock,
      availability: apiResponse.availability,
      degradedReason: apiResponse.degraded_reason ?? undefined,
      imageCount: apiResponse.image_count,
      timingMs: session.cropDurationMs,
      rawResponse: apiResponse.raw_response,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : '不明なエラーが発生しました。';
    await renderOverlay(tabId, {
      status: 'error',
      action: resolvedRequestOptions.action,
      modelName: resolvedRequestOptions.modelName,
      modelOptions,
      customPrompt: resolvedRequestOptions.customPrompt,
      sessionReady: Boolean(cachedSession || getCachedSession(tabId)),
      selectedText: fallbackSelectionText,
      error: message,
    });
  }
}

async function createFreshSession(
  tab: chrome.tabs.Tab,
  tabId: number,
  fallbackSelectionText: string,
  modelOptions: ModelOption[],
): Promise<SelectionAnalysisSession> {
  const selection = await collectSelection(tabId, fallbackSelectionText);
  if (!selection.ok || !selection.payload) {
    throw new Error(selection.error ?? '選択テキストを取得できませんでした。');
  }

  const resolvedSelection = {
    ...selection.payload,
    text: fallbackSelectionText.trim() || selection.payload.text,
  } satisfies SelectionCapturePayload;

  const screenshotDataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
    format: 'png',
  });
  const cropResult = await cropSelectionImage(
    screenshotDataUrl,
    resolvedSelection,
  );

  const session: SelectionAnalysisSession = {
    selection: resolvedSelection,
    previewImageUrl: cropResult.imageDataUrl,
    cropDurationMs: cropResult.durationMs,
    modelOptions,
    lastAction: 'translation',
  };
  setAnalysisSession(tabId, session);
  return session;
}

function getCachedSession(tabId: number): SelectionAnalysisSession | undefined {
  const session = getAnalysisSession(tabId);
  if (!session) {
    return undefined;
  }

  return {
    ...session,
    modelOptions: [...session.modelOptions],
  };
}

function buildModelOptions(settings: ExtensionSettings): ModelOption[] {
  return settings.lastKnownModels.map((modelId) => ({
    modelId,
    displayName: modelId,
  }));
}

function resolveAnalyzeRequestOptions(
  settings: ExtensionSettings,
  options: RunSelectionAnalysisOptions,
): AnalyzeRequestOptions & { apiBaseUrl: string } {
  const resolvedModelName = options.modelName ?? settings.defaultModel;

  return {
    action: options.action ?? 'translation',
    apiBaseUrl: options.apiBaseUrl ?? settings.apiBaseUrl,
    modelName: resolvedModelName || undefined,
    customPrompt: options.customPrompt?.trim() || undefined,
  };
}