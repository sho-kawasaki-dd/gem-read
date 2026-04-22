import {
  buildAnalyzeTextFromSessionItems,
  countTokens,
} from '../../shared/gateways/localApiGateway';
import type { SelectionAnalysisSession } from './analysisSessionStore';

export interface SyncPayloadTokenOptions {
  apiBaseUrl: string;
  modelName?: string;
}

/**
 * 現在の selection batch から analyze request の概算 token 数を付与する。
 * これは UX 用の補助情報であり、見積り失敗で解析フロー全体を止めない。
 */
export async function syncPayloadTokenEstimate(
  session: SelectionAnalysisSession,
  options: SyncPayloadTokenOptions
): Promise<SelectionAnalysisSession> {
  const resolvedModelName = normalizeModelName(
    options.modelName ?? session.lastModelName
  );
  const batchText = buildAnalyzeTextFromSessionItems(session.items);

  if (!batchText) {
    // image-only batch など text 本体が空のときは estimate を消し、誤解を招く 0 件表示を避ける。
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
