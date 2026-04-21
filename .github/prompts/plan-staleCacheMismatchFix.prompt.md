## Plan: Stale Cache Mismatch Fix

既存 cache は再利用する現行仕様を維持しつつ、remote 側で article cache が失われたのに extension が active cache として扱い続ける不整合を解消する。推奨方針は、Python/browser_api が「cache 付き実行は失敗し uncached fallback で成功した」事実を応答メタデータとして返し、browser-extension 側でその cache を `remote-missing` として local state から invalidated に落とすこと。これにより PowerShell 上の 403 fallback ログと overlay 表示を一致させ、同じ stale cache を次回以降も再送しないようにする。

**Steps**

1. Phase 1: Python の analyze 経路で cache fallback 成功を観測可能にする。src/pdf_epub_reader/models/ai_model.py の `AIModel.analyze()` で、`cached_content` を付けた実行を試みたか、失敗後に cache なしで fallback したか、その理由が何かを local 変数として保持し、結果 DTO（src/pdf_epub_reader/dto/ai_dto.py の `AnalysisResult`）へ流せる形にする。既存の「fallback で成功させる」挙動自体は変えない。なお `use_explicit_cache=True`（ブラウザ拡張の通常パス）の fallback 時は `self._cache_name` / `self._cache_model` をクリアしない現行実装は意図的なものであり変更しない。
2. Phase 1: browser_api の application DTO と HTTP schema を拡張する。src/browser_api/application/dto.py の `AnalyzeTranslateResult` と src/browser_api/api/schemas/analyze.py の `AnalyzeTranslateResponse` に、少なくとも `cache_request_attempted`、`cache_request_failed`、`cache_fallback_reason` 相当の optional metadata を追加し、既存クライアント互換を保ったままシリアライズする。Step 1 に依存。
3. Phase 1: browser_api service が新メタデータを応答へ載せるようにする。src/browser_api/application/services/analyze_service.py の `analyze_translate()` と関連変換処理で、AIModel から来た cache fallback metadata を `AnalyzeTranslateResult` に詰める。既存の `used_mock` / `degraded_reason` とは意味を混ぜない。Step 1-2 に依存。
4. Phase 2: extension の共有 contract と gateway で metadata を受け取る。browser-extension/src/shared/contracts/messages.ts の `AnalyzeApiResponse` と browser-extension/src/shared/gateways/localApiGateway.ts のレスポンス変換に、browser_api から来た cache fallback metadata を追加する。snake_case → camelCase 変換もここで吸収する。Step 2-3 に依存。
5. Phase 2: background で stale cache を local invalidated に落とす。browser-extension/src/background/usecases/runSelectionAnalysis.ts で `sendAnalyzeTranslateRequest()` の戻り値を見て、`cacheRequestFailed=true` かつ fallback success の場合は `invalidateArticleCache()` を呼び session の `articleCacheState` を `remote-missing` 理由で invalidated に更新する。更新後の session オブジェクトを `setAnalysisSession` と後続の `renderOverlay` 両方に渡すこと（更新前の session を上書きせずに渡すと overlay が古い active 表示のまま残る）。次回リクエストで stale `cacheName` が再送されない点は `resolveExplicitCacheName()` が `status !== 'active'` なら `undefined` を返す既存ロジックで自動的に達成されるため、追加ロジックは不要。Step 4 に依存。
6. Phase 2: article cache service の invalidation reason と notice を整える。browser-extension/src/background/services/articleCacheService.ts の `invalidateTrackedState()` は現状 `cacheName` があると必ず `deleteContextCache()` を呼ぶが、`remote-missing` の場合は Gemini 側にキャッシュが存在しないためリモート削除呼び出しは 404 等で失敗し `status: 'degraded'` に落ちる。`reason === 'remote-missing'` の場合はリモート削除をスキップしてローカル state だけを `invalidated` に更新するパスを新設すること。notice は「サーバー側で article cache が見つからなかったため、今回のリクエストは cache なしで完了した」方向へ統一し、既存の `Article cache created automatically for the current tab.` が stale state のまま残らないようにする。Step 5 に依存。
7. Phase 3: overlay 表示を state に合わせて調整する。browser-extension/src/content/overlay/renderOverlay.ts の `buildBannerText()`、`formatArticleCacheStatus()`、`buildCacheImpactValue()`、`buildCacheImpactNote()` で、`invalidated + remote-missing` の場合に実挙動に合う文言へ切り替える。active cache が本当に使われた場合の表示は維持し、fallback 成功時だけ「cache は今回使われなかった」と分かるようにする。Step 6 に依存。
8. Phase 4: Python 側テストを追加する。tests/test_models/test_ai_model.py で cache request failure → uncached fallback success のケースに metadata が立つことを検証し、tests/test_browser_api/test_application/test_analyze_service.py と tests/test_browser_api/test_api/test_analyze_router.py で browser_api 経由の応答 JSON に新フィールドが載ることを確認する。Step 1-3 に依存。
9. Phase 4: extension 側テストを追加する。browser-extension/**tests**/unit/shared/localApiGateway.test.ts に metadata 変換（snake_case → camelCase）のケースを追加し、browser-extension/**tests**/unit/background/runSelectionAnalysis.test.ts で fallback success 後に local cache state が `remote-missing` invalidated へ落ち、更新後の state が overlay へ反映されることを確認する。browser-extension/**tests**/unit/background/articleCacheService.test.ts で `remote-missing` reason 時にリモート削除が呼ばれずローカル state だけが `invalidated` になることを確認し、browser-extension/**tests**/unit/content/renderOverlay.test.ts で notice / status 表示が新状態に一致することを固定する。Step 4-7 に依存。
10. Phase 5: ドキュメントを更新する。docs/user/settings-and-cache.md で「既存 cache は再利用するが、server 側で cache が失われた場合はローカル state を無効化し、今回のリクエストは cache なしで完了した旨を示す」ことを追記し、必要なら docs/developer/runtime-flows.md に fallback metadata → invalidation の流れを補足する。Step 7 に依存。

**Relevant files**

- d:\programming\py_apps\gem-read\src\pdf_epub_reader\models\ai_model.py — `AIModel.analyze()` の cache fallback 成功を観測・記録する起点。
- d:\programming\py_apps\gem-read\src\pdf_epub_reader\dto\ai_dto.py — `AnalysisResult` dataclass に fallback metadata フィールドを追加する変更先。`ai_model.py` から gateway 経由で service まで伝搬する中継 DTO。
- d:\programming\py_apps\gem-read\src\browser_api\application\dto.py — `AnalyzeTranslateResult` の metadata 拡張先。
- d:\programming\py_apps\gem-read\src\browser_api\api\schemas\analyze.py — HTTP response schema の拡張先。
- d:\programming\py_apps\gem-read\src\browser_api\application\services\analyze_service.py — AIModel 結果を browser_api response へマッピングする箇所。
- d:\programming\py_apps\gem-read\browser-extension\src\shared\contracts\messages.ts — `AnalyzeApiResponse` と `ArticleCacheInvalidationReason` の contract 更新先。
- d:\programming\py_apps\gem-read\browser-extension\src\shared\gateways\localApiGateway.ts — API response metadata のデシリアライズ先。
- d:\programming\py_apps\gem-read\browser-extension\src\background\usecases\runSelectionAnalysis.ts — fallback success を受けて local article cache state を無効化する本命。
- d:\programming\py_apps\gem-read\browser-extension\src\background\services\articleCacheService.ts — `remote-missing` notice と invalidation helper の整備先。
- d:\programming\py_apps\gem-read\browser-extension\src\content\overlay\renderOverlay.ts — banner / status / cache impact の文言整合先。
- d:\programming\py_apps\gem-read\tests\test_models\test_ai_model.py — AIModel の fallback metadata 回帰防止。
- d:\programming\py_apps\gem-read\tests\test_browser_api\test_application\test_analyze_service.py — service 層の metadata 回帰防止。
- d:\programming\py_apps\gem-read\tests\test_browser_api\test_api\test_analyze_router.py — HTTP schema の回帰防止。
- d:\programming\py_apps\gem-read\browser-extension\_\_tests\_\_\unit\background\runSelectionAnalysis.test.ts — stale cache invalidation の回帰防止。
- d:\programming\py_apps\gem-read\browser-extension\_\_tests\_\_\unit\background\articleCacheService.test.ts — `remote-missing` state の notice/transition 回帰防止。
- d:\programming\py_apps\gem-read\browser-extension\_\_tests\_\_\unit\content\renderOverlay.test.ts — overlay 表示文言の回帰防止。
- d:\programming\py_apps\gem-read\docs\user\settings-and-cache.md — ユーザー向け仕様の更新先。
- d:\programming\py_apps\gem-read\docs\developer\runtime-flows.md — runtime flow の補足先。

**Verification**

1. Python 側で、cache 付き実行が 403 / 400 等で失敗し uncached fallback で成功したケースの単体テストが通ることを確認する。
2. browser_api のレスポンス JSON に新 metadata が載り、旧クライアント互換を壊していないことを確認する。
3. extension の unit test で、fallback success 後に local article cache state が `remote-missing` invalidated に更新され、次回リクエストでは stale cacheName を送らないことを確認する。
4. overlay で `Article cache created automatically for the current tab.` が stale state のまま残らず、「今回のリクエストは cache なしで完了した」方向の文言へ切り替わることを確認する。
5. popup の article cache toggle を OFF にしていても、正常な既存 cache は再利用される一方、server 側で消えた cache だけは local invalidation されることを手動確認する。
6. 再度同じページで実行したとき、invalidated 済み stale cacheName が再送されず、PowerShell 上の同一 403 fallback ログが毎回繰り返されないことを確認する。

**Decisions**

- popup toggle OFF 後も既存 cache は再利用する現行仕様を維持する。
- cache 付き実行が失敗し uncached fallback が成功した場合、その cache は local state を `remote-missing` 理由で invalidated に落とす。
- stale remote cache は次回も再送しない。`invalidateArticleCache()` で `status` を `invalidated` に落とせば `resolveExplicitCacheName()` の既存ガードにより `cacheName` は自動的に送られなくなる。
- Python/browser_api へは optional response metadata を追加して extension へ事実を伝える。
- overlay 文言は「cache 作成済み」ではなく「server 側で cache が見つからず今回は cache なしで完了した」に寄せる。

**Further Considerations**

1. `cache_fallback_reason` は生の Gemini message 全文ではなく、UI では短い reason code か正規化された説明だけを出す方が stable。詳細ログは Python logger に残す。
2. `remote-missing` invalidation 時に `displayName` や `tokenEstimate` をどこまで残すかは小判断。次回 stale cache を再利用しないことを優先するなら `cacheName` は確実に落とし、表示用メタは必要最低限だけ残すのが安全。
