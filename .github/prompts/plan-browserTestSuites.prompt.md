## Plan: Browser Test Suites

browser-extension は Vitest + jsdom を単体テストの基盤、Playwright を Chromium 向け E2E の基盤として採用する。src/browser_api は既存 pytest 基盤に乗せ、application/service と FastAPI router を主対象にする。Windows を主対象 OS とし、CI 実行コマンド・失敗条件・coverage 方針まで含めて整備する。

**Steps**
1. Phase 1: Python test suite baseline を整備する。
   - 既存 pytest 構成を拡張し、browser_api 向けテストを `tests/test_browser_api/` 配下に追加する。
   - `application/services/analyze_service.py` を最優先の単体テスト対象とし、モデル解決、画像 decode、AIKeyMissingError 時の mock fallback、translation / translation_with_explanation の応答整形を検証する。
   - FastAPI router は TestClient ベースで `/health` と `/analyze/translate` の 200/400/AI error mapping を検証する。
   - *depends on 1a*: 依存差し替え用 fixture を作成し、実 Gemini 通信なしで安定実行できるようにする。
2. Phase 2: browser-extension unit test baseline を整備する。
   - extension root に Vitest 設定を追加し、`test`, `test:coverage`, 必要なら `test:watch` script を package.json に追加する。
   - Chrome API mock と DOM setup を共有 fixture に集約し、Background/Content/Popup の runtime entry ではなく usecase/service/overlay/selection モジュールを単体テストする。
   - `background/usecases/runPhase0TranslationTest`、`background/services/cropSelectionImage`、`content/selection/snapshotStore`、`content/overlay/renderOverlay` を最初の対象にする。
   - *parallel with step 1*: Python 側と独立に進められる。
3. Phase 3: browser-extension E2E baseline を整備する。
   - Playwright を Chromium only で導入し、unpacked extension 読み込み前提の最小 E2E を作る。
   - 最初のシナリオは「テキスト選択 → context menu 起動導線 → overlay 表示/エラー表示確認」とする。
   - E2E はローカル API 実通信に依存しすぎないよう、必要に応じて response を固定化した test mode を検討する。
   - *depends on 2*: unit test 基盤と extension build が先。
4. Phase 4: 実行コマンドと CI 方針を固定する。
   - Windows primary 前提で、Python と extension の test command を README or developer docs に追記する。
   - CI gate は少なくとも「pytest browser_api subset」「Vitest」「Playwright smoke」を分けて実行可能な形にする。
   - Coverage は最初から厳格なしきい値を置かず、レポート出力を先に整えてから threshold を後追いで設定する。
5. Phase 5: テスト対象外と保守ルールを明文化する。
   - thin entry file は原則直接テストせず、下位の usecase/service を対象にする。
   - 実 Gemini API 依存のテストは CI gate に含めず、手動 smoke か別ジョブ扱いにする。
   - 自由矩形機能追加時は `content/` 側の独立 feature として unit/E2E を増設する前提を文書化する。

**Relevant files**
- `c:\Users\tohbo\python_programs\gem-read\pyproject.toml` — 既存 pytest 基盤、dev dependency、testpaths の確認起点
- `c:\Users\tohbo\python_programs\gem-read\tests\conftest.py` — 既存 fixture と mock パターンの再利用候補
- `c:\Users\tohbo\python_programs\gem-read\docs\developer\testing.md` — 既存 repo の testing philosophy と smoke launch の整合確認
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\package.json` — Vitest / Playwright 導入先、test scripts 追加対象
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\tsconfig.json` — extension テスト時の型解決と DOM/chrome types の整合確認
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\vite.config.ts` — Vitest 設定統合時の基点
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\src\background\usecases\runPhase0TranslationTest.ts` — extension unit test の優先対象
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\src\background\services\cropSelectionImage.ts` — extension unit test の優先対象
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\src\content\selection\snapshotStore.ts` — selection 寿命問題の回帰防止対象
- `c:\Users\tohbo\python_programs\gem-read\browser-extension\src\content\overlay\renderOverlay.ts` — DOM 描画テストの優先対象
- `c:\Users\tohbo\python_programs\gem-read\src\browser_api\api\routers\analyze.py` — FastAPI router test の対象
- `c:\Users\tohbo\python_programs\gem-read\src\browser_api\application\services\analyze_service.py` — browser_api service test の最優先対象
- `c:\Users\tohbo\python_programs\gem-read\src\browser_api\api\dependencies.py` — dependency override / app state 差し替え方針の確認対象

**Verification**
1. Python: `uv run pytest tests/test_browser_api/ -q` で browser_api 専用テストが安定実行できること。
2. Extension unit: `npm run test` で Vitest が Background/Content/Popup の対象モジュールを実行できること。
3. Extension coverage: `npm run test:coverage` で coverage レポートが生成できること。
4. Extension E2E: Chromium only の Playwright smoke が unpacked extension を読み込み、overlay 表示または想定エラー表示まで到達すること。
5. Regression check: `npm run build` と `uv run pytest tests/ -q` の既存フローが壊れていないこと。

**Decisions**
- browser-extension 単体テスト基盤は Vitest + jsdom を採用する。
- browser-extension E2E は Playwright まで計画に含める。
- 拡張の自動テスト対象ブラウザはまず Chromium only とする。
- src/browser_api の主対象は service + router とし、adapter は必要最小限の補助対象とする。
- CI 方針と失敗条件は計画に含める。
- 主対象 OS は Windows としつつ、Python テストは将来的な cross-platform 互換を阻害しない書き方を維持する。

**Further Considerations**
1. Playwright E2E で local API を本当に起動して叩くか、test mode/stub を用意するかは、実装前に最終決定する。推奨は Phase 1 では stub、Phase 2 以降で実 API smoke を追加。
2. Coverage threshold は初回導入時に hard gate にせず、まず現状値を観測してから段階的に設定する。
3. browser-extension の自由矩形 feature 追加時は `content/rect-selection/` 系の専用 unit/E2E を別枠で足す。