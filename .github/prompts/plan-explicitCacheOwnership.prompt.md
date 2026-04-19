---
name: explicit-cache-ownership
description: Implement the gem-read explicit article cache ownership change across browser_api and browser-extension.
argument-hint: Optional scope, constraints, or follow-up details
agent: agent
---

# Implement Explicit Cache Ownership

gem-read の browser-extension article cache を backend の implicit active-cache 依存から切り離し、extension が明示的に cache 名を送った時だけ browser_api / AIModel が cached_content を使う構成へ移してください。同時に extension 側では session 終了時と article extraction failure 時に remote cache を delete し、stale cache の残存時間を短くしてください。navigation 時の即 delete は引き続き行わないでください。

追加のユーザー指示があれば優先してください。

${input:request:Optional scope, constraints, or extra acceptance criteria}

## Goal

- backend を explicit cache opt-in 対応へ移しつつ desktop app の後方互換を維持する。
- browser-extension が再利用すべき cache を明示的に指定するようにする。
- session teardown と article extraction failure で remote cache cleanup を行う。
- stale cache 判定のために extension が backend の cache status endpoint へ依存しないようにする。

## Non-Negotiable Requirements

- `cache_name` は optional とし、未指定時は従来どおり desktop app 向け implicit active cache fallback を維持する。
- extension から `cache_name` が指定された場合は、その cache 名だけを explicit に使う。
- explicit cache path で cache 消失、TTL 切れ、モデル不一致などが起きても、non-cached retry は維持する。
- explicit cache path の失敗時に `AIModel._cache_name` / `AIModel._cache_model` を変更しない。desktop app の internal cache state を壊してはいけない。
- `messages.ts` の `AnalyzeRequestOptions` 型には `cache_name` を追加しない。`sendAnalyzeTranslateRequest` の呼び出し側で session から抽出して渡す。
- cleanup trigger は tab close、overlay clear / close、article extraction failure を含める。
- navigation 時の即 delete は行わない。
- last item removal による auto delete は今回のスコープ外とする。
- browser_api の `GET /cache/status` HTTP endpoint は削除する。
- `AIModel.get_cache_status()` 自体は desktop app presenter 用として維持する。

## Work Order

1. まず関連実装を調べ、現在の analyze request shaping、cache lifecycle、cleanup 導線、browser_api schema/service/test の構造を確認する。
2. backend で analyze request の schema / DTO / service mapping / AI request DTO に optional `cache_name` を追加する。
3. `AIModel` の cached_content 適用条件を見直し、explicit `cache_name` 指定時はその cache だけを使い、未指定時のみ internal active cache fallback を使うようにする。
4. browser_api の unit / API tests を更新し、以下を固定する。
   - `cache_name` 未指定で旧挙動が保たれること
   - `cache_name` 指定時だけ explicit cache が使われること
   - invalid / expired cache 指定時に degrade せず non-cached retry に落ちること
5. browser-extension の analyze request shaping を更新し、active article cache があり model 一致で再利用可能な場合だけ `cache_name` を送る。
6. browser-extension の session teardown cleanup を追加し、tab close、overlay clear / close、article extraction failure で remote delete を試みる。
7. article extraction failure 時は local invalidated 表示だけで済ませず、active cache があれば remote delete を試み、その結果を degraded / invalidated に反映する。
8. extension tests を更新し、cache_name 送信条件、tab close cleanup、overlay clear cleanup、extraction failure cleanup、navigation non-delete を固定する。
9. developer docs を更新し、explicit cache ownership と session cleanup policy を反映する。
10. 実装後に build / test を実行し、結果を簡潔に報告する。

## Relevant Files

- `browser-extension/src/shared/gateways/localApiGateway.ts`
  - analyze request body に optional cache 名を追加する。
  - `AnalyzeTranslateRequestBody` に `cache_name?: string` を追加する。
  - `buildAnalyzeRequestBody` が session 由来の cache 名を受け取れるようにする。
  - `fetchContextCacheStatus` と `GET /cache/status` 呼び出しを削除する。
- `browser-extension/src/background/usecases/runSelectionAnalysis.ts`
  - active article cache を request 送信時に explicit に選択する中心箇所。
- `browser-extension/src/background/entry.ts`
  - tab close、overlay clear runtime message、manual delete など session teardown の入り口。
- `browser-extension/src/background/services/articleCacheService.ts`
  - extraction failure と invalidation / degrade の整合を取る。
  - `syncArticleCacheState` 内の remote status 確認を削除し、生死確認は analyze 時の backend lazy validation に委ねる。
  - TTL 表示は `expireTime` から算出する形へ寄せる。
- `browser-extension/src/background/usecases/updateSelectionSession.ts`
  - overlay clear / item removal 系の cleanup 導線。
- `src/browser_api/api/schemas/analyze.py`
  - HTTP request schema に optional `cache_name` を追加する。
- `src/browser_api/application/dto.py`
  - `AnalyzeTranslateCommand` に `cache_name` を追加する。
- `src/browser_api/application/services/analyze_service.py`
  - command から `AnalysisRequest` への mapping を更新する。
  - `GET /cache/status` ルートと extension 専用の status 経由処理を削除する。
- `src/pdf_epub_reader/dto/ai_dto.py`
  - `AnalysisRequest` に optional `cache_name` を追加する。
- `src/pdf_epub_reader/models/ai_model.py`
  - cached_content の auto-apply / retry / TTL behavior を explicit cache opt-in に合わせて調整する。
- `tests/test_browser_api/**`
  - browser_api 側の schema / service / router 回帰確認。
- `browser-extension/__tests__/unit/background/**`
  - extension 側の cache lifecycle 回帰確認。
- `docs/developer/testing.md`
  - verification policy の更新先。
- `docs/developer/packt-cache-notes.md`
  - stale-cache 混入対策の status update 先。

## Guardrails

- 関連ファイルを読んで既存スタイルに合わせ、最小限の差分で実装する。
- 既存の public API や desktop app の挙動を不要に壊さない。
- backend と extension の変更を片側だけで終わらせず、契約変更を end-to-end で通す。
- テストが壊れる場合は root cause を直す。無関係な失敗までは直さない。
- docs と tests を必要に応じて更新する。

## Verification

- `browser-extension` で `npm run test`
- `browser-extension` で `npm run build`
- repository root で `uv run pytest tests/test_browser_api/ -q`
- 可能なら smoke path で tab close、overlay clear、manual delete 後に remote cache が消えていることを確認する。
- extraction failure で local state だけでなく remote cache も残らないことを確認する。
- navigation only では delete が走らず、rerun まで cache が維持されることを確認する。

## Expected Final Response

- 変更の要点を短くまとめる。
- 重要な設計判断や互換性上の注意点があれば記す。
- 実行した verification と未実行項目を分けて示す。
- 未解決リスクや follow-up があれば最後に短く挙げる。