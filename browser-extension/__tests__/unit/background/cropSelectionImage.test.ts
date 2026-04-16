import { beforeEach, describe, expect, it, vi } from 'vitest';

import { cropSelectionImage } from '../../../src/background/services/cropSelectionImage';

const drawImageMock = vi.fn();
const convertToBlobMock = vi.fn();

class OffscreenCanvasMock {
  static instances: OffscreenCanvasMock[] = [];

  width: number;
  height: number;

  constructor(width: number, height: number) {
    this.width = width;
    this.height = height;
    OffscreenCanvasMock.instances.push(this);
  }

  getContext = vi.fn(() => ({
    imageSmoothingEnabled: false,
    imageSmoothingQuality: 'low',
    drawImage: drawImageMock,
  }));

  convertToBlob = convertToBlobMock;
}

function createBlobLike(bytes: number[]) {
  return {
    arrayBuffer: vi.fn().mockResolvedValue(Uint8Array.from(bytes).buffer),
  };
}

describe('cropSelectionImage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    OffscreenCanvasMock.instances = [];
    vi.spyOn(performance, 'now').mockReturnValueOnce(100).mockReturnValueOnce(116.4);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        blob: vi.fn().mockResolvedValue(createBlobLike([1, 2, 3])),
      }),
    );
    vi.stubGlobal(
      'createImageBitmap',
      vi.fn().mockResolvedValue({
        width: 2000,
        height: 1000,
      }),
    );
    vi.stubGlobal('OffscreenCanvas', OffscreenCanvasMock as unknown as typeof OffscreenCanvas);
    convertToBlobMock.mockResolvedValue(createBlobLike([65, 66, 67]));
  });

  it('crops, rescales, and returns a data URL', async () => {
    const result = await cropSelectionImage('data:image/png;base64,shot', {
      text: 'selection',
      rect: { left: 100, top: 50, width: 400, height: 100 },
      viewportWidth: 1000,
      viewportHeight: 500,
      devicePixelRatio: 2,
      url: 'https://example.com/article',
      pageTitle: 'Example page',
    });

    expect(OffscreenCanvasMock.instances).toHaveLength(1);
    expect(OffscreenCanvasMock.instances[0]).toMatchObject({
      width: 768,
      height: 192,
    });
    expect(drawImageMock).toHaveBeenCalledWith(
      expect.objectContaining({ width: 2000, height: 1000 }),
      200,
      100,
      800,
      200,
      0,
      0,
      768,
      192,
    );
    expect(result.imageDataUrl).toBe('data:image/webp;base64,QUJD');
    expect(result.durationMs).toBeCloseTo(16.4, 5);
  });

  it('throws when the canvas context is unavailable', async () => {
    class NullCanvasMock {
      constructor(_width: number, _height: number) {}

      getContext() {
        return null;
      }

      convertToBlob = vi.fn();
    }

    vi.stubGlobal('OffscreenCanvas', NullCanvasMock as unknown as typeof OffscreenCanvas);

    await expect(
      cropSelectionImage('data:image/png;base64,shot', {
        text: 'selection',
        rect: { left: 0, top: 0, width: 100, height: 100 },
        viewportWidth: 1000,
        viewportHeight: 500,
        devicePixelRatio: 2,
        url: 'https://example.com/article',
        pageTitle: 'Example page',
      }),
    ).rejects.toThrow('OffscreenCanvas の 2D コンテキストを取得できませんでした。');
  });
});