import {
  OUTPUT_IMAGE_QUALITY,
  OUTPUT_IMAGE_TYPE,
  OUTPUT_MAX_LONG_EDGE,
} from '../../shared/config/phase0';
import type { SelectionCapturePayload } from '../../shared/contracts/messages';

export async function cropSelectionImage(
  screenshotDataUrl: string,
  selection: SelectionCapturePayload,
): Promise<{ imageDataUrl: string; durationMs: number }> {
  const startedAt = performance.now();
  const imageBlob = await fetch(screenshotDataUrl).then((response) => response.blob());
  const bitmap = await createImageBitmap(imageBlob);

  const scaleX = bitmap.width / selection.viewportWidth;
  const scaleY = bitmap.height / selection.viewportHeight;
  const sourceX = clamp(selection.rect.left * scaleX, 0, bitmap.width - 1);
  const sourceY = clamp(selection.rect.top * scaleY, 0, bitmap.height - 1);
  const sourceWidth = clamp(selection.rect.width * scaleX, 1, bitmap.width - sourceX);
  const sourceHeight = clamp(selection.rect.height * scaleY, 1, bitmap.height - sourceY);

  if (sourceWidth <= 0 || sourceHeight <= 0) {
    throw new Error('選択範囲の crop 座標が無効です。');
  }

  const { outputWidth, outputHeight } = getOutputSize(sourceWidth, sourceHeight);
  const canvas = new OffscreenCanvas(outputWidth, outputHeight);
  const context = canvas.getContext('2d');
  if (!context) {
    throw new Error('OffscreenCanvas の 2D コンテキストを取得できませんでした。');
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
  context.drawImage(
    bitmap,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    outputWidth,
    outputHeight,
  );

  const outputBlob = await canvas.convertToBlob({
    type: OUTPUT_IMAGE_TYPE,
    quality: OUTPUT_IMAGE_QUALITY,
  });
  const outputBytes = new Uint8Array(await outputBlob.arrayBuffer());
  const imageDataUrl = `${OUTPUT_IMAGE_TYPE};base64,${bytesToBase64(outputBytes)}`;
  const durationMs = performance.now() - startedAt;
  console.log(`Gem Read crop completed in ${durationMs.toFixed(1)}ms`);
  return {
    imageDataUrl: `data:${imageDataUrl}`,
    durationMs,
  };
}

function getOutputSize(sourceWidth: number, sourceHeight: number): {
  outputWidth: number;
  outputHeight: number;
} {
  const longEdge = Math.max(sourceWidth, sourceHeight);
  const resizeRatio = longEdge > OUTPUT_MAX_LONG_EDGE ? OUTPUT_MAX_LONG_EDGE / longEdge : 1;
  return {
    outputWidth: Math.max(1, Math.round(sourceWidth * resizeRatio)),
    outputHeight: Math.max(1, Math.round(sourceHeight * resizeRatio)),
  };
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}