import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getChromeMock } from '../../mocks/chrome';

const collectSelectionMock = vi.hoisted(() => vi.fn());
const renderOverlayMock = vi.hoisted(() => vi.fn());
const sendAnalyzeTranslateRequestMock = vi.hoisted(() => vi.fn());
const cropSelectionImageMock = vi.hoisted(() => vi.fn());

vi.mock('../../../src/background/gateways/tabMessagingGateway', () => ({
  collectSelection: collectSelectionMock,
  renderOverlay: renderOverlayMock,
}));

vi.mock('../../../src/background/gateways/localApiGateway', () => ({
  sendAnalyzeTranslateRequest: sendAnalyzeTranslateRequestMock,
}));

vi.mock('../../../src/background/services/cropSelectionImage', () => ({
  cropSelectionImage: cropSelectionImageMock,
}));

import { runPhase0TranslationTest } from '../../../src/background/usecases/runPhase0TranslationTest';

describe('runPhase0TranslationTest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading then success overlay on the happy path', async () => {
    const chromeMock = getChromeMock();
    chromeMock.tabs.captureVisibleTab.mockResolvedValue('data:image/png;base64,shot');
    collectSelectionMock.mockResolvedValue({
      ok: true,
      payload: {
        text: 'selection from content script',
        rect: { left: 10, top: 20, width: 30, height: 40 },
        viewportWidth: 1440,
        viewportHeight: 900,
        devicePixelRatio: 2,
        url: 'https://example.com/article',
        pageTitle: 'Example page',
      },
    });
    cropSelectionImageMock.mockResolvedValue({
      imageDataUrl: 'data:image/webp;base64,crop',
      durationMs: 12.5,
    });
    sendAnalyzeTranslateRequestMock.mockResolvedValue({
      ok: true,
      mode: 'translation',
      translated_text: '翻訳結果',
      explanation: null,
      raw_response: '翻訳結果',
      used_mock: false,
      image_count: 1,
    });

    await runPhase0TranslationTest(
      { id: 7, windowId: 9 } as chrome.tabs.Tab,
      '  fallback text  ',
    );

    expect(renderOverlayMock).toHaveBeenNthCalledWith(1, 7, {
      status: 'loading',
      selectedText: '  fallback text  ',
    });
    expect(collectSelectionMock).toHaveBeenCalledWith(7, '  fallback text  ');
    expect(chromeMock.tabs.captureVisibleTab).toHaveBeenCalledWith(9, {
      format: 'png',
    });
    expect(cropSelectionImageMock).toHaveBeenCalledWith(
      'data:image/png;base64,shot',
      expect.objectContaining({ text: 'fallback text' }),
    );
    expect(sendAnalyzeTranslateRequestMock).toHaveBeenCalledWith(
      expect.objectContaining({ text: 'fallback text' }),
      'data:image/webp;base64,crop',
    );
    expect(renderOverlayMock).toHaveBeenLastCalledWith(
      7,
      expect.objectContaining({
        status: 'success',
        selectedText: 'fallback text',
        translatedText: '翻訳結果',
        previewImageUrl: 'data:image/webp;base64,crop',
        imageCount: 1,
        timingMs: 12.5,
      }),
    );
  });

  it('renders an error overlay when selection payload is unavailable', async () => {
    const chromeMock = getChromeMock();
    collectSelectionMock.mockResolvedValue({
      ok: false,
      error: '選択テキストを取得できませんでした。',
    });

    await runPhase0TranslationTest(
      { id: 7, windowId: 9 } as chrome.tabs.Tab,
      'fallback',
    );

    expect(chromeMock.tabs.captureVisibleTab).not.toHaveBeenCalled();
    expect(renderOverlayMock).toHaveBeenLastCalledWith(7, {
      status: 'error',
      selectedText: 'fallback',
      error: '選択テキストを取得できませんでした。',
    });
  });

  it('renders an error overlay when downstream work throws', async () => {
    collectSelectionMock.mockResolvedValue({
      ok: true,
      payload: {
        text: 'selection from content script',
        rect: { left: 10, top: 20, width: 30, height: 40 },
        viewportWidth: 1440,
        viewportHeight: 900,
        devicePixelRatio: 2,
        url: 'https://example.com/article',
        pageTitle: 'Example page',
      },
    });
    cropSelectionImageMock.mockRejectedValue(new Error('capture failed'));

    await runPhase0TranslationTest(
      { id: 7, windowId: 9 } as chrome.tabs.Tab,
      'fallback',
    );

    expect(renderOverlayMock).toHaveBeenLastCalledWith(7, {
      status: 'error',
      selectedText: 'fallback',
      error: 'capture failed',
    });
  });
});