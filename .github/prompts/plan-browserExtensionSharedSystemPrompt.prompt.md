## Plan: Shared System Prompt

browser-extension の popup に共通 system prompt 設定を追加し、その値を `translation` / `translation_with_explanation` / `custom_prompt` の全分析リクエストへ流します。あわせて、browser API は desktop の `AppConfig` を直接共有するのをやめ、browser-extension 向けの専用設定型 `BrowserApiConfig` を導入します。設定の読み込み元は当面 desktop 側の保存値を写像して再利用できますが、browser API 内部では `BrowserApiConfig` だけを扱う形へ切り替えます。

system prompt の transport は extension から独立した `system_prompt` フィールドとして送信し、backend では `system_instruction` ではなく prompt の `contents` ヘッダへ差し込んで適用します。これにより article cache 制約を壊さず、translation 系と custom prompt 系で責務を分けたまま共通 prompt を適用できます。

**Steps**
1. Phase 0: browser API 専用設定 `BrowserApiConfig` を切り出す。*以降の前提*
   browser API は desktop の `AppConfig` を直接保持しない。browser API 用の専用 dataclass か Protocol を新設し、少なくとも default model、fallback model list（`selected_models: list[str]`）、output language、default translation system prompt、cache TTL をそこへ閉じ込める。
   [src/browser_api/adapters/config_gateway.py](src/browser_api/adapters/config_gateway.py) の `load_runtime_config()` は desktop 側の `load_config()` を直接返すのではなく、`AppConfig` から `BrowserApiConfig` への写像を返す。
   [src/browser_api/api/dependencies.py](src/browser_api/api/dependencies.py) と [src/browser_api/application/services/analyze_service.py](src/browser_api/application/services/analyze_service.py) は `BrowserApiConfig` を受け取るように変更し、browser API 内で desktop 固有設定を参照できない境界を作る。
   [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) は `AppConfig` 全体ではなく、AI 実行に必要な最小設定面だけを受け取れるように調整する。継承よりも専用型 + 写像を優先する。
   なお、`AIModel.update_config()` は [src/pdf_epub_reader/interfaces/model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py) の `IAIModel` Protocol で `config: AppConfig` として定義されており、[src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) が desktop 側から直接呼び出す。`AIModel` 本体の `_config` 型と `update_config()` のシグネチャは desktop との互換を維持するため `AppConfig` のまま残す。browser API 境界の分離は `AnalyzeService` が `BrowserApiConfig` を受け取る形にとどめ、`AIModel` 自体は変更しない。
2. Phase 1: extension 設定契約を拡張する。*Phase 0 と独立・並行実施可能（TypeScript 側のみ変更）*
   [browser-extension/src/shared/config/phase0.ts](browser-extension/src/shared/config/phase0.ts) に `sharedSystemPrompt` を追加し、default は空文字列、旧保存値は既存 merge パターンで自動補完にする。
3. Phase 2: popup に編集 UI を追加する。*depends on 2*
   [browser-extension/src/popup/ui/renderPopup.ts](browser-extension/src/popup/ui/renderPopup.ts) に textarea と説明文を追加し、初期表示・保存・再同期に組み込む。UI は textarea + 説明文のみで、専用リセットや文字数カウンタは付けない。
4. Phase 3: extension の分析リクエスト経路へ system prompt を通す。*depends on 2*
   [browser-extension/src/shared/contracts/messages.ts](browser-extension/src/shared/contracts/messages.ts)、[browser-extension/src/background/usecases/runSelectionAnalysis.ts](browser-extension/src/background/usecases/runSelectionAnalysis.ts)、[browser-extension/src/shared/gateways/localApiGateway.ts](browser-extension/src/shared/gateways/localApiGateway.ts) を更新し、空欄でなければ `system_prompt` を 3 アクションすべてへ付与する。
   具体的には `runSelectionAnalysis.ts` 内の `resolveAnalyzeRequestOptions()` 関数で `settings.sharedSystemPrompt` を取り出し、空欄でなければ `systemPrompt` フィールドとして返すように変更する。`localApiGateway.ts` の `AnalyzeTranslateRequestBody` と `SendAnalyzeRequestOptions` にも `system_prompt` を追加し、`buildAnalyzeRequestBody()` で組み込む。
   extension 内では `translation` / `translation_with_explanation` / `custom_prompt` の区別を引き続き `AnalysisAction` として保持し、settings とは混ぜない。
5. Phase 4: browser API の受け口と DTO を拡張する。*depends on 3*
   [src/browser_api/api/schemas/analyze.py](src/browser_api/api/schemas/analyze.py)、[src/browser_api/application/dto.py](src/browser_api/application/dto.py)、[src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py) に `system_prompt` を追加し、HTTP 境界で制御文字チェックを入れる。`system_prompt` は 10,000 文字を上限とし、超過時は 422 を返す。制御文字チェックは改行・タブ・復帰を除く制御文字のみ拒否する（Decisions に記載のとおり）。
   browser API の公開 contract では 3 アクションを `mode` として保持しつつ、application 層では `AnalysisMode + include_explanation + custom_prompt + system_prompt` という内部正規形へ写像する。
6. Phase 5: backend の prompt 組み立てを request 優先へ変更する。*depends on 5*
   [src/browser_api/application/services/analyze_service.py](src/browser_api/application/services/analyze_service.py) で `translation_with_explanation` を独立 mode に増やさず、`AnalysisMode.TRANSLATION` + `include_explanation=True` として正規化する。
   [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) の `_build_contents()` は `AnalysisMode` と `include_explanation` をもとに prompt header を生成し、request の `system_prompt` があれば `BrowserApiConfig` の既定 translation prompt より優先する。
   `translation` 系では共有 system prompt を翻訳タスク本文として使い、`custom_prompt` では `USER_TASK` の前段に `USER_CONTEXT` 相当の節として差し込む。client 側で文字列連結はしない。
   `custom_prompt` + `system_prompt` の組み立てテンプレートは以下のとおり。
   ```
   Respond in {output_language}.

   USER_CONTEXT:
   {system_prompt}

   USER_TASK:
   {custom_prompt}

   Apply the task only to the text enclosed in <selection> tags below.
   ```
7. Phase 6: テストを追加・更新する。*各フェーズ完了後に並行で進められる*
   extension 側は settings storage・popup・gateway、backend 側は config mapping・router・service・AI model の各テストを更新し、空欄時フォールバックと 3 アクションへの反映を確認する。
8. Phase 7: 必要最小限のドキュメントを更新する。*depends on 3-6*
   popup に新設定が増えるため、必要なら [docs/user/settings-and-cache.md](docs/user/settings-and-cache.md) か [docs/user/operations.md](docs/user/operations.md) に説明を追記する。browser API の責務変更が大きければ [docs/developer/architecture.md](docs/developer/architecture.md) の境界説明も更新する。

**Internal Flow After Phase 0**
1. browser-extension background は `AnalysisAction` として `translation` / `translation_with_explanation` / `custom_prompt` を解決し、model・custom prompt・shared system prompt をまとめて local API request を組み立てる。
2. browser API schema はこの 3 アクションを `mode` として受け取るが、そのまま core へ持ち込まず、application service で内部正規形へ落とす。
3. internal DTO では `translation` と `translation_with_explanation` をどちらも `AnalysisMode.TRANSLATION` とし、解説有無は `include_explanation` で表現する。`custom_prompt` は `AnalysisMode.CUSTOM_PROMPT` と `custom_prompt` 本文で表現する。
4. `system_prompt` は 3 アクション共通の独立フィールドとして保持し、task mode の識別には使わない。設定値と実行 mode を結合させない。
5. `AIModel` は `AnalysisMode` と `include_explanation` を見て prompt header と response parsing を決める。browser-extension UI 上の 3 アクション区別は transport 層で保持し、core では 2 系統の実行モードへ正規化する。

**Relevant files**
- [browser-extension/src/shared/config/phase0.ts](browser-extension/src/shared/config/phase0.ts) — extension 永続設定の shape / default / merge
- [browser-extension/src/shared/storage/settingsStorage.ts](browser-extension/src/shared/storage/settingsStorage.ts) — popup/background 共通の保存経路
- [browser-extension/src/popup/ui/renderPopup.ts](browser-extension/src/popup/ui/renderPopup.ts) — popup フォームと保存処理
- [browser-extension/src/shared/contracts/messages.ts](browser-extension/src/shared/contracts/messages.ts) — extension 内の分析契約
- [browser-extension/src/background/usecases/runSelectionAnalysis.ts](browser-extension/src/background/usecases/runSelectionAnalysis.ts) — settings から analyze request を組み立てる主経路
- [browser-extension/src/shared/gateways/localApiGateway.ts](browser-extension/src/shared/gateways/localApiGateway.ts) — local API への request body 構築
- [src/browser_api/adapters/config_gateway.py](src/browser_api/adapters/config_gateway.py) — desktop 設定から browser API 専用設定への写像入口
- [src/browser_api/api/dependencies.py](src/browser_api/api/dependencies.py) — browser API サービス組み立てと config 注入
- [src/browser_api/api/schemas/analyze.py](src/browser_api/api/schemas/analyze.py) — HTTP schema と入力バリデーション
- [src/browser_api/application/dto.py](src/browser_api/application/dto.py) — application DTO
- [src/browser_api/application/services/analyze_service.py](src/browser_api/application/services/analyze_service.py) — browser API から internal request への正規化
- [src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py) — AI request DTO
- [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) — prompt header / contents / response parse の組み立て

**Verification**
1. browser API の config mapping test を追加し、desktop `AppConfig` から `BrowserApiConfig` へ必要項目だけが写像されることを確認する。
2. extension の unit test で settings default / merge / popup 保存 / gateway request body を確認する。
3. browser API の test で `system_prompt` 受理、制御文字 reject、DTO passthrough、3 アクションから internal DTO への正規化を確認する。
4. AI model の test で `translation` / `translation_with_explanation` / `custom_prompt` が最終的に `AnalysisMode` と `include_explanation` へどう落ちるか、ならびに prompt 組み立て結果を確認する。
5. 手動で popup 保存後に overlay の 3 アクションを実行し、空欄時は既存挙動のまま、入力時は共通 system prompt が反映されることを確認する。

**Decisions**
- browser API は desktop `AppConfig` を直接共有しない。`BrowserApiConfig` を専用型として切り出し、desktop 側保存値から必要項目だけを写像する。
- `BrowserApiConfig` は継承よりも専用型 + 写像を優先し、desktop 固有フィールドを browser API 境界へ持ち込まない。
- popup で編集できる共通 system prompt を追加する。default は空欄。
- 保存値は入力どおり保持し、trim しない。
- 適用対象は 3 アクションすべて。
- transport は `system_prompt` の独立フィールドにする。`custom_prompt` への前置連結はしない。
- browser-extension 内の 3 アクション区別は transport 契約として維持するが、core では `AnalysisMode.TRANSLATION` と `AnalysisMode.CUSTOM_PROMPT` の 2 系統へ正規化し、translation + explanation は `include_explanation` で表現する。
- backend では request の `system_prompt` があれば `BrowserApiConfig` の既定 translation prompt より優先し、未指定時のみ config 既定値へフォールバックする。
- 制御文字対策は API 受信時に行い、改行・タブ・復帰を除く制御文字のみ拒否する。`system_prompt` は 10,000 文字を上限とし、超過時は 422 を返す。
- `system prompt を contents の頭に結合する案` は、この実装では妥当です。ただし client 側で文字列連結するのではなく、backend で独立フィールドを受け取って `_build_contents()` 内で組み立てる前提にします。
- API キー未設定時の mock レスポンス（`_build_mock_response()`）は `system_prompt` を無視する。mock の目的は結線確認であり、prompt 内容の検証は対象外とする。
