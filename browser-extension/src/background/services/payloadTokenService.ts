import {
  buildAnalyzeTextFromSessionItems,
  countTokens,
} from '../../shared/gateways/localApiGateway';
import type { SelectionAnalysisSession } from './analysisSessionStore';

export interface SyncPayloadTokenOptions {
  apiBaseUrl: string;
  modelName?: string;
}

export async function syncPayloadTokenEstimate(
  session: SelectionAnalysisSession,
  options: SyncPayloadTokenOptions
): Promise<SelectionAnalysisSession> {
  const resolvedModelName = normalizeModelName(
    options.modelName ?? session.lastModelName
  );
  const batchText = buildAnalyzeTextFromSessionItems(session.items);

  if (!batchText) {
    return {
      ...session,
      payloadTokenEstimate: undefined,
      payloadTokenModelName: resolvedModelName,
      payloadTokenError: undefined,
    };
  }

  if (!resolvedModelName) {
    return {
      ...session,
      payloadTokenEstimate: undefined,
      payloadTokenModelName: undefined,
      payloadTokenError: 'Choose a Gemini model to estimate request tokens.',
    };
  }

  try {
    const result = await countTokens(batchText, {
      apiBaseUrl: options.apiBaseUrl,
      modelName: resolvedModelName,
    });

    return {
      ...session,
      payloadTokenEstimate: result.tokenCount,
      payloadTokenModelName: result.modelName,
      payloadTokenError: undefined,
    };
  } catch (error) {
    return {
      ...session,
      payloadTokenEstimate: undefined,
      payloadTokenModelName: resolvedModelName,
      payloadTokenError: `Request token estimate is unavailable: ${toErrorMessage(error)}`,
    };
  }
}

function normalizeModelName(modelName: string | undefined): string | undefined {
  const normalized = modelName?.trim();
  return normalized ? normalized : undefined;
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Unexpected token estimate error.';
}
