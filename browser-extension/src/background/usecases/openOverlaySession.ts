import { loadExtensionSettings } from '../../shared/storage/settingsStorage';
import {
  collectArticleContext,
  renderOverlay,
} from '../gateways/tabMessagingGateway';
import {
  getAnalysisSession,
  setAnalysisSession,
} from '../services/analysisSessionStore';
import {
  mergeCollectedArticleContext,
  syncArticleCacheState,
} from '../services/articleCacheService';
import {
  buildEmptyOverlayPayload,
  buildOverlayPayload,
} from './updateSelectionSession';

export async function openOverlaySession(tabId: number): Promise<void> {
	const settings = await loadExtensionSettings();
	const session = await getAnalysisSession(tabId);
	if (session) {
		const articleContextResult = await collectArticleContext(tabId).catch((error) => ({
			ok: false as const,
			error:
				error instanceof Error
					? error.message
					: 'Article context extraction failed.',
		}));
		const refreshedSession = await syncArticleCacheState(
			mergeCollectedArticleContext(session, articleContextResult),
			{
				apiBaseUrl: settings.apiBaseUrl,
				modelName: session.lastModelName || settings.defaultModel || undefined,
				allowAutoCreate: true,
			}
		);
		await setAnalysisSession(tabId, refreshedSession);

		if (
			refreshedSession.items.length ||
			refreshedSession.articleContext ||
			refreshedSession.articleCacheState
		) {
		await renderOverlay(
			tabId,
			buildOverlayPayload(refreshedSession, {
				launcherOnly: false,
				preserveDrafts: true,
			})
		);
		return;
		}
	}

	await renderOverlay(
		tabId,
		buildEmptyOverlayPayload(settings, {
			launcherOnly: true,
			preserveDrafts: true,
		})
	);
}