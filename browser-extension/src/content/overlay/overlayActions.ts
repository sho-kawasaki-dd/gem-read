import { MAX_SELECTION_SESSION_ITEMS } from '../../shared/config/phase0';
import type {
  AnalysisAction,
  AppendSessionItemResponse,
  DeleteActiveArticleCacheResponse,
  ExportMarkdownPayload,
  ExportMarkdownResponse,
  OverlayPayload,
  RemoveSessionItemResponse,
  RunOverlayActionMessage,
  RunOverlayActionResponse,
  SelectionSessionItem,
  ToggleSessionItemImageResponse,
} from '../../shared/contracts/messages';
import { canAppendSelectionBatchItem } from '../selection/selectionBatchController';
import { collectSelection } from '../selection/snapshotStore';

export async function runOverlayAction(
  action: AnalysisAction,
  modelName: string,
  customPrompt: string,
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  if (action === 'custom_prompt' && customPrompt.trim().length === 0) {
    errorBox.textContent = 'Custom prompt cannot be empty.';
    errorSection.hidden = false;
    return;
  }

  const message: RunOverlayActionMessage = {
    type: 'phase1.runOverlayAction',
    payload: {
      action,
      modelName: modelName.trim() || undefined,
      customPrompt:
        action === 'custom_prompt' ? customPrompt.trim() : undefined,
    },
  };

  // Overlay は privileged 処理を持たず、実行そのものは background に委譲する。
  const response = (await chrome.runtime.sendMessage(message)) as
    | RunOverlayActionResponse
    | undefined;
  if (response && !response.ok) {
    errorBox.textContent = response.error ?? 'Overlay action failed.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

export async function addCurrentSelection(
  errorBox: HTMLElement,
  errorSection: HTMLElement,
  payload: OverlayPayload
): Promise<void> {
  if (!canAppendSelectionBatchItem()) {
    errorBox.textContent = `You can keep up to ${payload.maxSessionItems ?? MAX_SELECTION_SESSION_ITEMS} selections in one batch.`;
    errorSection.hidden = false;
    return;
  }

  const selection = collectSelection();
  if (!selection.ok || !selection.payload) {
    errorBox.textContent =
      selection.error ??
      'A page selection is required before adding it to the batch.';
    errorSection.hidden = false;
    return;
  }

  const response = (await chrome.runtime.sendMessage({
    type: 'phase2.appendSessionItem',
    payload: {
      selection: selection.payload,
      source: 'text-selection',
    },
  })) as AppendSessionItemResponse | undefined;

  if (response?.ok === false) {
    errorBox.textContent =
      response.error ?? 'Failed to add the current selection.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

export async function removeSelectionItem(
  itemId: string,
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  const response = (await chrome.runtime.sendMessage({
    type: 'phase2.removeSessionItem',
    payload: { itemId },
  })) as RemoveSessionItemResponse | undefined;

  if (response?.ok === false) {
    errorBox.textContent =
      response.error ?? 'Failed to remove the selection item.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

export async function toggleSelectionItemImage(
  itemId: string,
  includeImage: boolean,
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  const response = (await chrome.runtime.sendMessage({
    type: 'phase2.toggleSessionItemImage',
    payload: { itemId, includeImage },
  })) as ToggleSessionItemImageResponse | undefined;

  if (response?.ok === false) {
    errorBox.textContent =
      response.error ??
      'Failed to update image inclusion for the selection item.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

export async function deleteActiveArticleCache(
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  const response = (await chrome.runtime.sendMessage({
    type: 'phase4.deleteActiveArticleCache',
  })) as DeleteActiveArticleCacheResponse | undefined;

  if (response?.ok === false) {
    errorBox.textContent =
      response.error ?? 'Failed to delete the active article cache.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

export async function exportCurrentMarkdown(
  payload: OverlayPayload,
  sessionItems: SelectionSessionItem[],
  selectedText: string,
  errorBox: HTMLElement,
  errorSection: HTMLElement
): Promise<void> {
  const exportPayload = buildExportMarkdownPayload(
    payload,
    sessionItems,
    selectedText
  );
  const response = (await chrome.runtime.sendMessage({
    type: 'phase5.exportMarkdown',
    payload: exportPayload,
  })) as ExportMarkdownResponse | undefined;

  if (response?.ok === false) {
    errorBox.textContent =
      response.error ?? 'Failed to export the current Gemini result.';
    errorSection.hidden = false;
    return;
  }

  errorBox.textContent = '';
  errorSection.hidden = true;
}

function buildExportMarkdownPayload(
  payload: OverlayPayload,
  sessionItems: SelectionSessionItem[],
  selectedText: string
): ExportMarkdownPayload {
  const latestSelection = sessionItems.at(-1)?.selection;

  return {
    action: payload.action ?? 'translation',
    modelName: payload.modelName,
    translatedText: payload.translatedText,
    explanation: payload.explanation,
    rawResponse: payload.rawResponse,
    selectedText: selectedText.trim() || undefined,
    sessionItems,
    articleContext: payload.articleContext,
    usage: payload.usage,
    pageTitle:
      latestSelection?.pageTitle?.trim() ||
      payload.articleContext?.title?.trim() ||
      document.title ||
      'Gem Read Export',
    pageUrl:
      latestSelection?.url?.trim() ||
      payload.articleContext?.url?.trim() ||
      window.location.href,
  };
}
