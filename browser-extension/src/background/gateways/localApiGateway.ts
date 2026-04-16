import { PHASE0_API_BASE_URL } from '../../shared/config/phase0';
import type { AnalyzeApiResponse, SelectionCapturePayload } from '../../shared/contracts/messages';

export async function sendAnalyzeTranslateRequest(
  selection: SelectionCapturePayload,
  imageDataUrl: string,
): Promise<AnalyzeApiResponse> {
  const response = await fetch(`${PHASE0_API_BASE_URL}/analyze/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: selection.text,
      images: [imageDataUrl],
      mode: 'translation',
      selection_metadata: {
        url: selection.url,
        page_title: selection.pageTitle,
        viewport_width: selection.viewportWidth,
        viewport_height: selection.viewportHeight,
        device_pixel_ratio: selection.devicePixelRatio,
        rect: selection.rect,
      },
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Local API request failed (${response.status}): ${errorText}`);
  }

  return response.json() as Promise<AnalyzeApiResponse>;
}