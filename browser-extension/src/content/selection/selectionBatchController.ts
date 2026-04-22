import { MAX_SELECTION_SESSION_ITEMS } from '../../shared/config/phase0';
import type { SelectionSessionItem } from '../../shared/contracts/messages';

/**
 * content 側で保持する ordered batch の mirror。
 * canonical session は background が持ち、ここでは overlay 再描画や keyboard 操作に必要な読み取り専用の写像だけを持つ。
 */
let sessionItems: SelectionSessionItem[] = [];

export function syncSelectionBatch(
  items: SelectionSessionItem[] | undefined
): SelectionSessionItem[] {
  // background から届いた payload を毎回置き換え、content 側で独自に batch を進化させない。
  sessionItems = (items ?? []).map((item) => ({ ...item }));
  return getSelectionBatchSnapshot();
}

export function getSelectionBatchSnapshot(): SelectionSessionItem[] {
  return sessionItems.map((item) => ({ ...item }));
}

export function clearSelectionBatch(): void {
  sessionItems = [];
}

export function canAppendSelectionBatchItem(): boolean {
  return sessionItems.length < MAX_SELECTION_SESSION_ITEMS;
}

export function getSelectionBatchCapacity(): {
  current: number;
  max: number;
} {
  return {
    current: sessionItems.length,
    max: MAX_SELECTION_SESSION_ITEMS,
  };
}