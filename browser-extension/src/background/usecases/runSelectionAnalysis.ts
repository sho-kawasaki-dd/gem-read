import type { ExtensionSettings } from '../../shared/config/phase0';
import type {
  AnalysisAction,
  AnalyzeRequestOptions,
  ModelOption,
  SelectionCapturePayload,
} from '../../shared/contracts/messages';
import { loadExtensionSettings } from '../../shared/storage/settingsStorage';
import { sendAnalyzeTranslateRequest } from '../gateways/localApiGateway';
import {
  collectSelection,
  renderOverlay,
} from '../gateways/tabMessagingGateway';
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

/**
 * Phase 1 の解析フローを background 側で束ねる use case。
 * 初回実行では selection/crop/session 作成まで進め、overlay からの再実行では cached session を再利用する。
 */
export async function runSelectionAnalysis(
  tab: chrome.tabs.Tab,
  fallbackSelectionText: string,
  options: RunSelectionAnalysisOptions = {}
): Promise<void> {
  const tabId = tab.id;
  if (tabId === undefined) {
    return;
  }

  const settings = await loadExtensionSettings();
  const resolvedRequestOptions = resolveAnalyzeRequestOptions(
    settings,
    options
  );
  const modelOptions = buildModelOptions(settings);
  const cachedSession = options.reuseCachedSession
    ? getCachedSession(tabId)
    : undefined;

  try {
    // loading を先に描画して、selection 取得や crop の待ち時間でも UI 上の文脈を保つ。
    await renderOverlay(tabId, {
      status: 'loading',
      action: resolvedRequestOptions.action,
      modelName: resolvedRequestOptions.modelName,
      modelOptions,
      customPrompt: resolvedRequestOptions.customPrompt,
      sessionReady: Boolean(cachedSession),
      selectedText: fallbackSelectionText,
    });

    // overlay からの再実行では captureVisibleTab をやり直さず、直前 session をそのまま再利用する。
    const session =
      cachedSession ??
      (await createFreshSession(
        tab,
        tabId,
        fallbackSelectionText,
        modelOptions
      ));

    const apiResponse = await sendAnalyzeTranslateRequest(
      session.selection,
      session.previewImageUrl,
      resolvedRequestOptions
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
    const message =
      error instanceof Error ? error.message : '不明なエラーが発生しました。';
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
  modelOptions: ModelOption[]
): Promise<SelectionAnalysisSession> {
  const selection = await collectSelection(tabId, fallbackSelectionText);
  if (!selection.ok || !selection.payload) {
    throw new Error(selection.error ?? '選択テキストを取得できませんでした。');
  }

  // browser 提供の selectionText は整形差があるため、座標は content script、文字列は fallback と live snapshot の両方を見る。
  const resolvedSelection = {
    ...selection.payload,
    text: fallbackSelectionText.trim() || selection.payload.text,
  } satisfies SelectionCapturePayload;

  const screenshotDataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
    format: 'png',
  });
  // crop は browser 側で済ませ、Python には必要最小限の画像だけを送る。
  const cropResult = await cropSelectionImage(
    screenshotDataUrl,
    resolvedSelection
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
    // 呼び出し側が候補配列を書き換えても store 本体を汚染しないよう参照を切る。
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
  options: RunSelectionAnalysisOptions
): AnalyzeRequestOptions & { apiBaseUrl: string } {
  const resolvedModelName = options.modelName ?? settings.defaultModel;

  return {
    action: options.action ?? 'translation',
    apiBaseUrl: options.apiBaseUrl ?? settings.apiBaseUrl,
    modelName: resolvedModelName || undefined,
    customPrompt: options.customPrompt?.trim() || undefined,
  };
}
