export type OverlayTabId = 'workspace' | 'gemini';

/**
 * overlay shortcut は textarea や input 編集を壊さないことを優先する。
 * そのため、まず editable target 上かどうかを shadow DOM を含めて判定する。
 */
export function isEditableTarget(event: KeyboardEvent): boolean {
  for (const entry of event.composedPath()) {
    if (!(entry instanceof HTMLElement)) {
      continue;
    }

    const tagName = entry.tagName;
    if (
      tagName === 'INPUT' ||
      tagName === 'TEXTAREA' ||
      tagName === 'SELECT' ||
      entry.isContentEditable
    ) {
      return true;
    }
  }

  const activeElement = document.activeElement;
  return activeElement instanceof HTMLElement
    ? activeElement.isContentEditable ||
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeElement.tagName)
    : false;
}

export function getFocusedOverlayTabButton(
  root: ShadowRoot
): HTMLButtonElement | null {
  const activeElement = root.activeElement;
  if (
    activeElement instanceof HTMLButtonElement &&
    activeElement.matches('.panel-tab[data-tab-id]')
  ) {
    return activeElement;
  }

  return null;
}

export function resolveKeyboardOverlayTab(
  root: ShadowRoot,
  focusedTabButton: HTMLButtonElement,
  key: string
): OverlayTabId | null {
  // disabled tab を飛ばして roving tabindex を維持し、ARIA tab として自然な移動に寄せる。
  const enabledButtons = Array.from(
    root.querySelectorAll<HTMLButtonElement>('.panel-tab[data-tab-id]')
  ).filter((button) => !button.disabled);
  if (enabledButtons.length === 0) {
    return null;
  }

  const currentIndex = enabledButtons.indexOf(focusedTabButton);
  if (currentIndex === -1) {
    return null;
  }

  if (key === 'Home') {
    return readOverlayTabId(enabledButtons[0]);
  }
  if (key === 'End') {
    return readOverlayTabId(enabledButtons.at(-1) ?? null);
  }
  if (key !== 'ArrowLeft' && key !== 'ArrowRight') {
    return null;
  }

  const direction = key === 'ArrowRight' ? 1 : -1;
  const nextIndex =
    (currentIndex + direction + enabledButtons.length) % enabledButtons.length;
  return readOverlayTabId(enabledButtons[nextIndex]);
}

export function readOverlayTabId(
  button: HTMLButtonElement | null
): OverlayTabId | null {
  const tabId = button?.dataset.tabId;
  return tabId === 'workspace' || tabId === 'gemini' ? tabId : null;
}
