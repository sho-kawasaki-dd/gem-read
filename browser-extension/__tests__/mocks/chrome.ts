import { vi } from 'vitest';

function createEventHook() {
  return {
    addListener: vi.fn(),
    removeListener: vi.fn(),
    hasListener: vi.fn(),
  };
}

export function createChromeMock(): typeof chrome {
  return {
    tabs: {
      captureVisibleTab: vi.fn(),
      query: vi.fn(),
      sendMessage: vi.fn(),
    },
    runtime: {
      onInstalled: createEventHook(),
      onMessage: createEventHook(),
      onStartup: createEventHook(),
    },
    contextMenus: {
      create: vi.fn(),
      removeAll: vi.fn(),
      onClicked: createEventHook(),
    },
  } as unknown as typeof chrome;
}

export function getChromeMock(): ReturnType<typeof createChromeMock> {
  return globalThis.chrome as unknown as ReturnType<typeof createChromeMock>;
}