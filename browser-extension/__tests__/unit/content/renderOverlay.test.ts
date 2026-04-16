import { describe, expect, it } from 'vitest';

import { renderOverlay } from '../../../src/content/overlay/renderOverlay';

function getShadowRoot(): ShadowRoot {
  const host = document.getElementById('gem-read-phase0-overlay-host');
  if (!host?.shadowRoot) {
    throw new Error('Overlay host was not rendered.');
  }
  return host.shadowRoot;
}

describe('renderOverlay', () => {
  it('renders a loading overlay with selection text', () => {
    renderOverlay({
      status: 'loading',
      selectedText: 'Selected paragraph',
    });

    const root = getShadowRoot();
    expect(root.querySelector('.badge')?.textContent).toContain('Running');
    expect(root.querySelector('.selection-box')?.textContent).toBe('Selected paragraph');
    expect(root.querySelector('.meta-box')?.textContent).toContain('Background workflow is running.');
    expect((root.querySelector('.result-section') as HTMLElement).hidden).toBe(true);
    expect((root.querySelector('.error-section') as HTMLElement).hidden).toBe(true);
  });

  it('renders success details and reuses the same host element', () => {
    renderOverlay({
      status: 'success',
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      explanation: '補足説明',
      previewImageUrl: 'data:image/webp;base64,preview',
      rawResponse: '翻訳結果\n\n---\n\n補足説明',
      imageCount: 1,
      timingMs: 12.3,
      usedMock: true,
    });
    renderOverlay({
      status: 'success',
      selectedText: 'Selected paragraph',
      translatedText: '翻訳結果',
      explanation: '補足説明',
      previewImageUrl: 'data:image/webp;base64,preview',
      rawResponse: '翻訳結果\n\n---\n\n補足説明',
      imageCount: 1,
      timingMs: 12.3,
      usedMock: true,
    });

    const root = getShadowRoot();
    expect(document.querySelectorAll('#gem-read-phase0-overlay-host')).toHaveLength(1);
    expect(root.querySelector('.badge')?.textContent).toContain('Mock Result');
    expect(root.querySelector('.result-box')?.textContent).toBe('翻訳結果');
    expect(root.querySelector('.explanation-box')?.textContent).toBe('補足説明');
    expect(root.querySelector('.raw-box')?.textContent).toContain('---');
    expect((root.querySelector('.preview-section') as HTMLElement).hidden).toBe(false);
    expect((root.querySelector('.preview-image') as HTMLImageElement).src).toBe(
      'data:image/webp;base64,preview',
    );
    expect(root.querySelector('.meta-box')?.textContent).toContain('images=1');
    expect(root.querySelector('.meta-box')?.textContent).toContain('crop=12.3ms');
    expect(root.querySelector('.meta-box')?.textContent).toContain('mock-response');
  });

  it('removes the overlay when the close button is clicked', () => {
    renderOverlay({
      status: 'error',
      selectedText: 'Selected paragraph',
      error: 'Something failed',
    });

    const root = getShadowRoot();
    (root.querySelector('.close') as HTMLButtonElement).click();

    expect(document.getElementById('gem-read-phase0-overlay-host')).toBeNull();
  });
});