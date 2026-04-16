import { describe, expect, it } from 'vitest';

import {
  EXTENSION_SETTINGS_STORAGE_KEY,
  type ExtensionSettings,
} from '../../../src/shared/config/phase0';
import {
  loadExtensionSettings,
  patchExtensionSettings,
  saveExtensionSettings,
} from '../../../src/shared/storage/settingsStorage';
import { getChromeMock } from '../../mocks/chrome';

describe('settingsStorage', () => {
  it('returns normalized defaults when storage is empty', async () => {
    const settings = await loadExtensionSettings();

    expect(settings).toEqual({
      apiBaseUrl: 'http://127.0.0.1:8000',
      defaultModel: '',
      lastKnownModels: [],
    });
  });

  it('persists normalized settings to chrome.storage.local', async () => {
    const chromeMock = getChromeMock();
    const settings = await saveExtensionSettings({
      apiBaseUrl: 'http://localhost:8123/',
      defaultModel: ' gemini-2.5-pro ',
      lastKnownModels: ['gemini-2.5-pro', 'gemini-2.5-pro', ' gemini-2.5-flash '],
    });

    expect(settings).toEqual({
      apiBaseUrl: 'http://localhost:8123',
      defaultModel: 'gemini-2.5-pro',
      lastKnownModels: ['gemini-2.5-pro', 'gemini-2.5-flash'],
    });
    expect(chromeMock.storage.local.set).toHaveBeenCalledWith(
      {
        [EXTENSION_SETTINGS_STORAGE_KEY]: settings,
      },
      expect.any(Function),
    );
  });

  it('patches existing settings without losing normalized values', async () => {
    await saveExtensionSettings({
      apiBaseUrl: 'http://127.0.0.1:9000',
      defaultModel: 'gemini-2.5-flash',
      lastKnownModels: ['gemini-2.5-flash'],
    });

    const patched = await patchExtensionSettings({
      lastKnownModels: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    });

    expect(patched).toEqual({
      apiBaseUrl: 'http://127.0.0.1:9000',
      defaultModel: 'gemini-2.5-flash',
      lastKnownModels: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    } satisfies ExtensionSettings);
  });
});