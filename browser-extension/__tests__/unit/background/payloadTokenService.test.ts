import { beforeEach, describe, expect, it, vi } from 'vitest';

const countTokensMock = vi.hoisted(() => vi.fn());

vi.mock('../../../src/shared/gateways/localApiGateway', () => ({
  buildAnalyzeTextFromSessionItems: (
    items: Array<{ selection: { text: string } }>
  ) =>
    items
      .map((item) => item.selection.text.trim())
      .filter((text) => text.length > 0)
      .map((text, index) => `${index + 1}. ${text}`)
      .join('\n\n'),
  countTokens: countTokensMock,
}));

import { syncPayloadTokenEstimate } from '../../../src/background/services/payloadTokenService';

describe('payloadTokenService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('counts tokens for the current text batch', async () => {
    countTokensMock.mockResolvedValue({
      ok: true,
      tokenCount: 42,
      modelName: 'gemini-2.5-flash',
    });

    const session = await syncPayloadTokenEstimate(
      {
        items: [
          {
            id: 'selection-1',
            source: 'text-selection',
            includeImage: false,
            selection: {
              text: 'First paragraph',
              rect: { left: 1, top: 2, width: 3, height: 4 },
              viewportWidth: 100,
              viewportHeight: 100,
              devicePixelRatio: 1,
              url: 'https://example.com',
              pageTitle: 'Example',
            },
          },
          {
            id: 'selection-2',
            source: 'text-selection',
            includeImage: false,
            selection: {
              text: 'Second paragraph',
              rect: { left: 1, top: 2, width: 3, height: 4 },
              viewportWidth: 100,
              viewportHeight: 100,
              devicePixelRatio: 1,
              url: 'https://example.com',
              pageTitle: 'Example',
            },
          },
        ],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
      }
    );

    expect(countTokensMock).toHaveBeenCalledWith(
      '1. First paragraph\n\n2. Second paragraph',
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
      }
    );
    expect(session.payloadTokenEstimate).toBe(42);
    expect(session.payloadTokenModelName).toBe('gemini-2.5-flash');
    expect(session.payloadTokenError).toBeUndefined();
  });

  it('keeps the overlay usable when token counting fails', async () => {
    countTokensMock.mockRejectedValue(new Error('token endpoint unavailable'));

    const session = await syncPayloadTokenEstimate(
      {
        items: [
          {
            id: 'selection-1',
            source: 'text-selection',
            includeImage: false,
            selection: {
              text: 'Only paragraph',
              rect: { left: 1, top: 2, width: 3, height: 4 },
              viewportWidth: 100,
              viewportHeight: 100,
              devicePixelRatio: 1,
              url: 'https://example.com',
              pageTitle: 'Example',
            },
          },
        ],
        modelOptions: [],
        lastAction: 'translation',
        lastModelName: 'gemini-2.5-flash',
      },
      {
        apiBaseUrl: 'http://127.0.0.1:9000',
        modelName: 'gemini-2.5-flash',
      }
    );

    expect(session.payloadTokenEstimate).toBeUndefined();
    expect(session.payloadTokenError).toContain('token endpoint unavailable');
  });
});
