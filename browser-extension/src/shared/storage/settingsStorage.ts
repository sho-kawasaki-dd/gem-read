import {
  DEFAULT_EXTENSION_SETTINGS,
  EXTENSION_SETTINGS_STORAGE_KEY,
  mergeExtensionSettings,
  type ExtensionSettings,
} from '../config/phase0';

export async function loadExtensionSettings(): Promise<ExtensionSettings> {
  const storedValue = await getFromStorage<Partial<ExtensionSettings>>(
    EXTENSION_SETTINGS_STORAGE_KEY,
  );
  return mergeExtensionSettings(storedValue);
}

export async function saveExtensionSettings(
  settings: Partial<ExtensionSettings>,
): Promise<ExtensionSettings> {
  const normalizedSettings = mergeExtensionSettings(settings);
  await setInStorage(EXTENSION_SETTINGS_STORAGE_KEY, normalizedSettings);
  return normalizedSettings;
}

export async function patchExtensionSettings(
  patch: Partial<ExtensionSettings>,
): Promise<ExtensionSettings> {
  const current = await loadExtensionSettings();
  const next = mergeExtensionSettings({
    ...current,
    ...patch,
  });
  await setInStorage(EXTENSION_SETTINGS_STORAGE_KEY, next);
  return next;
}

export function getDefaultExtensionSettings(): ExtensionSettings {
  return {
    ...DEFAULT_EXTENSION_SETTINGS,
    lastKnownModels: [...DEFAULT_EXTENSION_SETTINGS.lastKnownModels],
  };
}

function getFromStorage<T>(key: string): Promise<T | undefined> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.get(key, (result) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }

      resolve(result[key] as T | undefined);
    });
  });
}

function setInStorage<T>(key: string, value: T): Promise<void> {
  return new Promise((resolve, reject) => {
    chrome.storage.local.set({ [key]: value }, () => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }

      resolve();
    });
  });
}