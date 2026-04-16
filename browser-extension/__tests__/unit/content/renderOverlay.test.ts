import { describe, expect, it } from 'vitest';

import { renderOverlay } from '../../../src/content/overlay/renderOverlay';
import { getChromeMock } from '../../mocks/chrome';

function getShadowRoot(): ShadowRoot {
  const host = document.getElementById('gem-read-phase0-overlay-host');
  if (!host?.shadowRoot) {
    throw new Error('Overlay host was not rendered.');
  }
  return host.shadowRoot;
}

describe('renderOverlay', () => {
  it('renders a loading overlay with action controls and selection text', () => {
    renderOverlay({
      status: 'loading',
      action: 'translation',
      modelName: 'gemini-2.5-flash',
      modelOptions: [
        {
          modelId: 'gemini-2.5-flash',
          displayName: 'Gemini 2.5 Flash',
        },
      ],
      selectedText: 'Selected paragraph',
    });

    const root = getShadowRoot();
    expect(root.querySelector('.badge')?.textContent).toContain('Running');
    expect(root.querySelector('.selection-box')?.textContent).toBe('Selected paragraph');
    expect(root.querySelector('.meta-box')?.textContent).toContain('Background workflow is running.');
    expect((root.querySelector('.action-translation') as HTMLButtonElement).disabled).toBe(true);
    expect((root.querySelector('.model-input') as HTMLInputElement).value).toBe('gemini-2.5-flash');
    expect((root.querySelector('.result-section') as HTMLElement).hidden).toBe(true);
    expect((root.querySelector('.error-section') as HTMLElement).hidden).toBe(true);
  });

  it('renders success details, shows runtime banner, and reuses the same host element', () => {
    renderOverlay({
      status: 'success',
      action: 'translation_with_explanation',
      modelName: 'gemini-2.5-flash',
      modelOptions: [
        {
          modelId: 'gemini-2.5-flash',
          displayName: 'Gemini 2.5 Flash',
        },
      ],
      sessionReady: true,
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      explanation: '補足説明',
      previewImageUrl: 'data:image/webp;base64,preview',
      rawResponse: '翻訳結果\n\n---\n\n補足説明',
      imageCount: 1,
      timingMs: 12.3,
      usedMock: true,
      availability: 'mock',
      degradedReason: 'mock-response',
    });
    renderOverlay({
      status: 'success',
      action: 'translation_with_explanation',
      modelName: 'gemini-2.5-flash',
      modelOptions: [
        {
          modelId: 'gemini-2.5-flash',
          displayName: 'Gemini 2.5 Flash',
        },
      ],
      sessionReady: true,
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      explanation: '補足説明',
      previewImageUrl: 'data:image/webp;base64,preview',
      rawResponse: '翻訳結果\n\n---\n\n補足説明',
      imageCount: 1,
      timingMs: 12.3,
      usedMock: true,
      availability: 'mock',
      degradedReason: 'mock-response',
    });

    const root = getShadowRoot();
    expect(document.querySelectorAll('#gem-read-phase0-overlay-host')).toHaveLength(1);
    expect(root.querySelector('.badge')?.textContent).toContain('Mock Result');
    expect(root.querySelector('.banner-box')?.textContent).toContain('Mock mode is active');
    expect(root.querySelector('.result-box')?.textContent).toBe('翻訳結果');
    expect(root.querySelector('.explanation-box')?.textContent).toBe('補足説明');
    expect(root.querySelector('.raw-box')?.textContent).toContain('---');
    expect((root.querySelector('.preview-section') as HTMLElement).hidden).toBe(false);
    expect((root.querySelector('.preview-image') as HTMLImageElement).src).toBe(
      'data:image/webp;base64,preview',
    );
    expect((root.querySelector('.action-translation') as HTMLButtonElement).disabled).toBe(false);
    expect(root.querySelector('.meta-box')?.textContent).toContain('images=1');
    expect(root.querySelector('.meta-box')?.textContent).toContain('crop=12.3ms');
    expect(root.querySelector('.meta-box')?.textContent).toContain('mock-response');
  });

  it('sends overlay action messages to the background runtime', async () => {
    const chromeMock = getChromeMock();
    chromeMock.runtime.sendMessage.mockResolvedValue({ ok: true });

    renderOverlay({
      status: 'success',
      action: 'translation',
      modelName: 'gemini-2.5-flash',
      modelOptions: [
        {
          modelId: 'gemini-2.5-flash',
          displayName: 'Gemini 2.5 Flash',
        },
      ],
      customPrompt: 'Summarize this',
      sessionReady: true,
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      rawResponse: '翻訳結果',
    });

    const root = getShadowRoot();
    const modelInput = root.querySelector('.model-input') as HTMLInputElement;
    const customPromptInput = root.querySelector('.custom-prompt-input') as HTMLTextAreaElement;
    modelInput.value = 'gemini-2.5-pro';
    customPromptInput.value = 'Explain the terminology';
    modelInput.dispatchEvent(new Event('input', { bubbles: true }));
    customPromptInput.dispatchEvent(new Event('input', { bubbles: true }));

    (root.querySelector('.action-custom') as HTMLButtonElement).click();
    await Promise.resolve();

    expect(chromeMock.runtime.sendMessage).toHaveBeenCalledWith({
      type: 'phase1.runOverlayAction',
      payload: {
        action: 'custom_prompt',
        modelName: 'gemini-2.5-pro',
        customPrompt: 'Explain the terminology',
      },
    });
  });

  it('minimizes to a launcher and reopens from the launcher button', () => {
    renderOverlay({
      status: 'success',
      action: 'translation',
      sessionReady: true,
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      rawResponse: '翻訳結果',
    });

    let root = getShadowRoot();
    (root.querySelector('.minimize') as HTMLButtonElement).click();

    root = getShadowRoot();
    expect(root.querySelector('.launcher-button')?.textContent).toContain('Gem Read');

    (root.querySelector('.launcher-button') as HTMLButtonElement).click();
    root = getShadowRoot();
    expect(root.querySelector('.panel')).not.toBeNull();
  });

  it('removes the overlay when the close button is clicked', () => {
    renderOverlay({
      status: 'error',
      sessionReady: false,
      selectedText: 'Selected paragraph',
      error: 'Something failed',
    });

    const root = getShadowRoot();
    (root.querySelector('.close') as HTMLButtonElement).click();

    expect(document.getElementById('gem-read-phase0-overlay-host')).toBeNull();
  });
});