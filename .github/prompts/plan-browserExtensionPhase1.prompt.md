## Plan: Phase 1 Browser Extension MVP+

Phase 0 の選択→クロップ→翻訳の流れはすでにあるので、Phase 1 はそれを作り直すのではなく、popup 設定、overlay 実行 UI、backend のモデル取得と action 拡張を足して MVP 化する方針が妥当です。今回の決定を反映すると、単一選択は維持しつつ、overlay から「翻訳」「解説付き翻訳」「カスタムプロンプト」を実行でき、popup では localhost 接続先・既定モデル・接続状態を扱う構成になります。

**Steps**
1. Phase A: 契約と境界を先に固めます。  
[browser-extension/src/shared/contracts/messages.ts](browser-extension/src/shared/contracts/messages.ts) を拡張して、action 種別、custom prompt、model override、popup status、mock/degraded 状態を型として追加します。合わせて [browser-extension/manifest.json](browser-extension/manifest.json) の host permissions を `localhost` / `127.0.0.1` の任意ポート対応に広げ、popup 設定値は `chrome.storage.local` に集約します。ここが後続全体の前提です。

2. Phase B: browser API を Phase 1 契約へ広げます。  
[ src/browser_api/api/schemas/analyze.py ](src/browser_api/api/schemas/analyze.py)、[ src/browser_api/api/routers/analyze.py ](src/browser_api/api/routers/analyze.py)、[ src/browser_api/application/services/analyze_service.py ](src/browser_api/application/services/analyze_service.py) を中心に、`translation`、`translation_with_explanation`、`custom_prompt` を明示的に扱えるようにします。  
既存の [src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py) にある `AnalysisMode.CUSTOM_PROMPT` と `AnalysisRequest.custom_prompt`、および [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) の `list_available_models()` を再利用し、`GET /models` を追加します。モデル一覧は live 取得を優先し、失敗時は config fallback を返す設計にして、popup が `reachable / mock mode / unreachable` を判定できるようにします。`/health` は疎通確認専用のままにします。

3. Phase C: popup を設定・状態画面へ置き換えます。  
[browser-extension/src/popup/ui/renderPopup.ts](browser-extension/src/popup/ui/renderPopup.ts) と [browser-extension/src/popup/entry.ts](browser-extension/src/popup/entry.ts) を差し替え、API base URL 入力、接続状態、モデル一覧の取得と更新、既定モデル保存、overlay を開く導線を追加します。入力は localhost 系だけ許可し、`http://127.0.0.1:PORT` / `http://localhost:PORT` に正規化します。popup の状態判定は `/health` と `/models` の組み合わせで行います。  
この工程は backend のレスポンス形が固まれば、Phase B と並行できます。

4. Phase D: background の実行パスを汎用化します。  
[browser-extension/src/background/usecases/runPhase0TranslationTest.ts](browser-extension/src/background/usecases/runPhase0TranslationTest.ts) は責務が Phase 1 に合わなくなるので、保存済み設定の読込、選択取得、スクリーンショット取得、crop、API 呼び出し、overlay 更新を action 別に処理できる汎用 usecase に再編します。  
[browser-extension/src/background/gateways/localApiGateway.ts](browser-extension/src/background/gateways/localApiGateway.ts) では hardcoded な base URL を撤去し、runtime 設定から base URL・model・custom prompt を解決するようにします。  
[browser-extension/src/background/entry.ts](browser-extension/src/background/entry.ts) と [browser-extension/src/background/menus/phase0ContextMenu.ts](browser-extension/src/background/menus/phase0ContextMenu.ts) では、context menu は単一 entry のまま維持し、overlay 内で action を分岐させます。

5. Phase E: overlay を「結果表示専用」から「実行 UI」へ拡張します。  
[browser-extension/src/content/overlay/renderOverlay.ts](browser-extension/src/content/overlay/renderOverlay.ts) を、選択プレビュー、crop preview、翻訳ボタン、解説付き翻訳ボタン、custom prompt の multiline 入力、model override セレクタ、status badge、mock banner、最小化/再表示導線を持つ Phase 1 overlay にします。  
ここでは固定右上の Shadow DOM パネルを維持します。選択近傍配置、自由矩形、複数選択、記事全文抽出は Phase 1 の対象外です。

6. Phase F: テストを機能増分に合わせて拡張します。  
browser-extension 側は [browser-extension/__tests__/unit/background/runPhase0TranslationTest.test.ts](browser-extension/__tests__/unit/background/runPhase0TranslationTest.test.ts) を起点に、settings storage、popup rendering、汎用 analysis usecase、API gateway、overlay action の単体テストを追加します。  
browser API 側は [tests/test_browser_api/test_api/test_analyze_router.py](tests/test_browser_api/test_api/test_analyze_router.py) と [tests/test_browser_api/test_application/test_analyze_service.py](tests/test_browser_api/test_application/test_analyze_service.py) に `/models`、custom prompt、fallback source、エラーマッピングのテストを足します。  
Playwright smoke は popup 設定保存と、translation に加えて explanation か custom の少なくとも 1 経路まで広げます。

7. Phase G: ドキュメントと起動導線を整えます。  
[docs/developer/testing.md](docs/developer/testing.md) と user/developer 向け文書に、Local API の起動手順、popup での接続先変更、mock mode の見え方、Phase 1 の対象外機能を追記します。必要なら [src/browser_api/main.py](src/browser_api/main.py) の実行導線も整理して、`uv run python -m browser_api` か `uv run uvicorn browser_api.main:app` のどちらかを正式手順として固定します。

**Relevant files**
- [browser-extension/manifest.json](browser-extension/manifest.json)
- [browser-extension/src/shared/contracts/messages.ts](browser-extension/src/shared/contracts/messages.ts)
- [browser-extension/src/shared/config/phase0.ts](browser-extension/src/shared/config/phase0.ts)
- [browser-extension/src/background/entry.ts](browser-extension/src/background/entry.ts)
- [browser-extension/src/background/usecases/runPhase0TranslationTest.ts](browser-extension/src/background/usecases/runPhase0TranslationTest.ts)
- [browser-extension/src/background/gateways/localApiGateway.ts](browser-extension/src/background/gateways/localApiGateway.ts)
- [browser-extension/src/background/menus/phase0ContextMenu.ts](browser-extension/src/background/menus/phase0ContextMenu.ts)
- [browser-extension/src/popup/entry.ts](browser-extension/src/popup/entry.ts)
- [browser-extension/src/popup/ui/renderPopup.ts](browser-extension/src/popup/ui/renderPopup.ts)
- [browser-extension/src/content/overlay/renderOverlay.ts](browser-extension/src/content/overlay/renderOverlay.ts)
- [src/browser_api/api/app.py](src/browser_api/api/app.py)
- [src/browser_api/api/dependencies.py](src/browser_api/api/dependencies.py)
- [src/browser_api/api/routers/analyze.py](src/browser_api/api/routers/analyze.py)
- [src/browser_api/api/schemas/analyze.py](src/browser_api/api/schemas/analyze.py)
- [src/browser_api/application/services/analyze_service.py](src/browser_api/application/services/analyze_service.py)
- [src/browser_api/adapters/ai_gateway.py](src/browser_api/adapters/ai_gateway.py)
- [src/browser_api/main.py](src/browser_api/main.py)
- [src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py)
- [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py)
- [tests/test_browser_api/test_api/test_analyze_router.py](tests/test_browser_api/test_api/test_analyze_router.py)
- [tests/test_browser_api/test_application/test_analyze_service.py](tests/test_browser_api/test_application/test_analyze_service.py)
- [browser-extension/__tests__/unit/background/runPhase0TranslationTest.test.ts](browser-extension/__tests__/unit/background/runPhase0TranslationTest.test.ts)

**Verification**
1. `browser-extension/` で `npm run test`
2. `browser-extension/` で `npm run test:e2e`
3. ルートで `uv run pytest tests/test_browser_api/ -q`
4. 手動で、`8000` 以外の localhost port に API を立てて popup から接続先変更→保存→翻訳成功まで確認
5. `GEMINI_API_KEY` 未設定時に popup が `mock mode`、overlay が明示バナー付き結果を出すことを確認
6. 回帰確認として `npm run build` と `uv run pytest tests/ -q`

**Decisions**
- Phase 1 に解説付き翻訳とカスタムプロンプトを前倒しで含める
- 設定の主導線は popup、overlay からは shortcut のみ置く
- モデルは popup で既定値を保存し、overlay で都度 override 可能にする
- 接続先は localhost 系任意ポートのみ
- モデル一覧は backend live list 優先、失敗時は config fallback
- 状態表示は `reachable / mock mode / unreachable`
- API キー未設定時の mock 応答は維持し、明示表示する
- context menu は単一 entry を維持し、overlay 内 action で分岐する
- custom prompt は overlay の単一 multiline 入力で扱う

**Scope boundary**
- 含む: 単一選択、popup 設定、接続状態、モデル一覧、overlay action UI、explanation、custom prompt
- 含まない: 複数選択、自由矩形、記事全文抽出、Context Cache、options page、remote host 設定
