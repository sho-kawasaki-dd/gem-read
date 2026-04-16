import { describe, expect, it, vi } from 'vitest';

function createRect(left: number, top: number, right: number, bottom: number) {
  return {
    left,
    top,
    right,
    bottom,
    width: right - left,
    height: bottom - top,
  };
}

function createRange(rects: Array<ReturnType<typeof createRect>>): Range {
  const baseRect = rects[0];
  return {
    getClientRects: () => rects,
    getBoundingClientRect: () => baseRect,
  } as unknown as Range;
}

describe('snapshotStore', () => {
  it('collects and normalizes the current selection snapshot', async () => {
    vi.resetModules();
    const range = createRange([
      createRect(10, 20, 40, 30),
      createRect(35, 25, 65, 50),
    ]);
    vi.spyOn(window, 'getSelection').mockReturnValue({
      rangeCount: 1,
      toString: () => '  Hello\nworld  ',
      getRangeAt: () => range,
    } as unknown as Selection);
    document.title = 'Article';

    const { collectSelection } = await import('../../../src/content/selection/snapshotStore');
    const result = collectSelection();

    expect(result).toEqual({
      ok: true,
      payload: {
        text: 'Hello world',
        rect: {
          left: 10,
          top: 20,
          width: 55,
          height: 30,
        },
        viewportWidth: 1280,
        viewportHeight: 720,
        devicePixelRatio: 2,
        url: 'http://localhost:3000/',
        pageTitle: 'Article',
      },
    });
  });

  it('reuses the last stored snapshot when the live selection is gone', async () => {
    vi.resetModules();
    const range = createRange([createRect(10, 20, 40, 30)]);
    const getSelectionMock = vi.spyOn(window, 'getSelection');
    getSelectionMock.mockReturnValue({
      rangeCount: 1,
      toString: () => 'Selected text',
      getRangeAt: () => range,
    } as unknown as Selection);

    const { collectSelection, startSelectionTracking } = await import(
      '../../../src/content/selection/snapshotStore'
    );
    startSelectionTracking();
    document.dispatchEvent(new Event('selectionchange'));

    getSelectionMock.mockReturnValue({ rangeCount: 0 } as Selection);
    const result = collectSelection('  fallback text  ');

    expect(result).toEqual({
      ok: true,
      payload: expect.objectContaining({
        text: 'fallback text',
        rect: { left: 10, top: 20, width: 30, height: 10 },
      }),
    });
  });

  it('returns a guidance error when no snapshot can be recovered', async () => {
    vi.resetModules();
    vi.spyOn(window, 'getSelection').mockReturnValue({ rangeCount: 0 } as Selection);

    const { collectSelection } = await import('../../../src/content/selection/snapshotStore');

    expect(collectSelection('fallback')).toEqual({
      ok: false,
      error: '選択テキストの座標を保持できていません。選択し直してから再度実行してください。',
    });
    expect(collectSelection()).toEqual({
      ok: false,
      error: 'ページ上でテキストを選択してから実行してください。',
    });
  });
});