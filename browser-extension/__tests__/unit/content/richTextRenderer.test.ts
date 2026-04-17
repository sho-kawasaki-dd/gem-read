import { describe, expect, it, vi } from 'vitest';

import { renderRichText } from '../../../src/content/overlay/richTextRenderer';

describe('richTextRenderer', () => {
  it('sanitizes markdown-derived html and renders math', () => {
    const container = document.createElement('div');

    renderRichText(
      container,
      'Paragraph with $x+y$ and <img src=x onerror="alert(1)">'
    );

    expect(container.dataset.renderMode).toBe('rich');
    expect(container.querySelector('.katex')).not.toBeNull();
    expect(container.innerHTML.includes('onerror')).toBe(false);
  });

  it('keeps math delimiters literal inside code blocks', () => {
    const container = document.createElement('div');

    renderRichText(container, '```txt\n$literal_math$\n```\n\n$live_math$');

    expect(container.querySelector('code')?.textContent).toContain('$literal_math$');
    expect(container.querySelectorAll('.katex').length).toBeGreaterThan(0);
  });

  it('falls back to plain text when math rendering throws', async () => {
    vi.resetModules();
    vi.doMock('katex/contrib/auto-render', () => ({
      default: () => {
        throw new Error('render failed');
      },
    }));

    const { renderRichText: renderWithFailure } = await import(
      '../../../src/content/overlay/richTextRenderer'
    );
    const container = document.createElement('div');

    renderWithFailure(container, 'Math $x$');

    expect(container.dataset.renderMode).toBe('plain');
    expect(container.textContent).toBe('Math $x$');
    vi.doUnmock('katex/contrib/auto-render');
  });
});