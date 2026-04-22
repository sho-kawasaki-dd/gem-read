# Browser Extension Commenting Plan

## 目的

本計画は、`browser-extension/` 配下の TypeScript コードに、
新規参加のジュニアエンジニアが読んで構造と設計意図を追える程度の
Docstring と inline comment を段階的に追加するための実施方針をまとめる。

今回の目的は、コードをコメントで埋めることではない。
runtime 境界、canonical state の owner、background への委譲理由、
overlay 再描画や cache 無効化の判断理由のような
「名前だけでは伝わりにくい設計意図」を局所的に読めるようにする。

## 背景

browser-extension は Phase 2 以降の責務分割が明確で、
既存ドキュメントにも Background / Content / Popup / Shared の境界説明がある。
ただし、日常的にコードへ入る開発者にとっては、
ドキュメントを読んでからコードへ戻る往復が必要な箇所がまだ多い。

現状の傾向は次の通りである。

- thin entry には短い日本語 Docstring があり、責務の薄さと分離理由が説明されている
- service / usecase / store / overlay の多くは命名で意味を表しているが、設計判断の理由はコードから即座に読み取りにくい
- runtime flow は [docs/developer/runtime-flows.md](docs/developer/runtime-flows.md) にまとまっているが、局所コードの判断根拠としては少し遠い

そのため、外部ドキュメントを置き換えるのではなく、
コードの入口と重要な判断点にだけ補助線を引く方針を採る。

## 完了像

次の状態を完了像とする。

- 新規参加者が `background.ts` から読み始めて、runtime ごとの責務をコード内コメントだけで大まかに説明できる
- `runSelectionAnalysis`、`openOverlaySession`、`updateSelectionSession` を読んで、background が canonical session を持つ理由を説明できる
- `renderOverlay`、`snapshotStore`、`rectangleSelectionController` を読んで、content が DOM owner だが canonical state owner ではないことを説明できる
- `shared/contracts/messages.ts` を読んで、shared が単なる型置き場ではなく runtime 間契約であると分かる
- コメントが処理手順の言い換えではなく、設計意図と非自明な状態遷移の理解支援になっている

## コメント方針

### 基本原則

- 日本語の短い Docstring を基本とする
- API カタログ的な TSDoc は導入しない
- `@param` や `@returns` で型情報を言い換えない
- 何をしているかより、なぜその責務分割や状態管理をしているかを優先して書く
- 既存の [docs/developer/architecture.md](docs/developer/architecture.md) と [docs/developer/runtime-flows.md](docs/developer/runtime-flows.md) を補完し、重複しすぎない

### Docstring を入れる場所

- module の先頭: そのファイルがどの runtime に属し、何を owner とするか
- export function / export const: その関数が守る責務境界や canonical state
- type / interface: 意味が実装依存ではなく契約依存で重要なものだけ

### Inline comment を入れる場所

- async 境界で状態が失われやすい箇所
- DOM selection や screenshot 座標変換のような、ブラウザ事情に依存する箇所
- cache invalidation や fallback 判定のような、分岐理由が重要な箇所
- overlay の再描画や draft 保持のような、再レンダリング前提の UI 状態管理箇所

### 避けること

- 1 行ごとの逐語的説明
- 型や変数名をそのまま日本語に言い換えたコメント
- Phase 名の乱用
- endpoint、SDK 挙動、token 数など変化しやすい詳細の固定化
- テストが担うべき仕様説明の代替

## 優先度別対象

### Priority A: 構造の地図になるファイル

最初に着手する。新規参加者が読み始める起点であり、以降の探索コストを下げる。

- `browser-extension/src/background.ts`
- `browser-extension/src/content.ts`
- `browser-extension/src/popup.ts`
- `browser-extension/src/background/entry.ts`
- `browser-extension/src/content/entry.ts`
- `browser-extension/src/popup/entry.ts`
- `browser-extension/src/shared/contracts/messages.ts`
- `browser-extension/src/shared/config/phase0.ts`

### Priority B: Background の正準状態と orchestration

background が privileged coordinator である理由を明文化する。

- `browser-extension/src/background/usecases/runSelectionAnalysis.ts`
- `browser-extension/src/background/usecases/openOverlaySession.ts`
- `browser-extension/src/background/usecases/updateSelectionSession.ts`
- `browser-extension/src/background/services/analysisSessionStore.ts`
- `browser-extension/src/background/services/articleCacheService.ts`
- `browser-extension/src/background/services/cropSelectionImage.ts`
- `browser-extension/src/background/services/payloadTokenService.ts`
- `browser-extension/src/background/gateways/tabMessagingGateway.ts`

### Priority C: Content の DOM owner と overlay lifecycle

content が page DOM に近い一方で、正準 session は持たないことをコード上で分かるようにする。

- `browser-extension/src/content/overlay/renderOverlay.ts`
- `browser-extension/src/content/overlay/overlayActions.ts`
- `browser-extension/src/content/overlay/overlayKeyboard.ts`
- `browser-extension/src/content/selection/snapshotStore.ts`
- `browser-extension/src/content/selection/rectangleSelectionController.ts`
- `browser-extension/src/content/selection/selectionBatchController.ts`
- `browser-extension/src/content/selection/articleContext.ts`
- `browser-extension/src/content/overlay/richTextRenderer.ts`

### Priority D: Popup / Shared の補助線

popup と shared gateway の責務を整え、設定保存や疎通確認の意図を読みやすくする。

- `browser-extension/src/popup/ui/renderPopup.ts`
- `browser-extension/src/shared/storage/settingsStorage.ts`
- `browser-extension/src/shared/gateways/localApiGateway.ts`

### Priority E: テスト補助コメント

テストは全面コメント化しない。契約の切り出し意図が読みづらい fixture や stub に限定する。

- `browser-extension/__tests__/mocks/chrome.ts`
- background usecase 系の代表 unit test
- overlay の keyboard / rerender 前提を確認する代表 unit test

## ファイルごとの記述テーマ

### Entry files

- なぜ thin entry を守るのか
- bootstrap だけに責務を絞る理由
- listener 登録先と本体実装の分離意図

### Shared contracts

- runtime 間契約としての意味
- Phase ごとの message 増加が責務分離とどう対応しているか
- rect / selection / overlay payload がどの境界をまたぐか

### Background usecases / services

- tab-scoped session を background が持つ理由
- content でなく background が screenshot / API call / cache を束ねる理由
- cache を再利用・無効化・保持する判断条件
- overlay rerun が live selection に依存しない理由

### Content overlay / selection

- live DOM selection が非安定であること
- mirror state と canonical state の違い
- overlay を payload-driven に再構築する理由
- draft 入力や minimized 状態を module state で維持する理由

### Popup / storage / gateway

- popup を settings と疎通確認に留める理由
- settings merge が backward compatibility を担う理由
- Local API gateway が transport concern を隔離する理由

## 実施順

### Step 1: 構造の導線整備

Priority A を先に実施する。
ここで読む順番と runtime 境界が見える状態を作る。

### Step 2: Background 中核の補強

Priority B を実施する。
canonical session、cache、画像 crop、rerun orchestration の理由を明文化する。

### Step 3: Content 中核の補強

Priority C を実施する。
DOM と overlay の owner としての振る舞いを読みやすくする。

### Step 4: Popup / Shared 補助線

Priority D を実施する。
popup bootstrap、設定保存、gateway の責務境界を揃える。

### Step 5: テスト補助コメント

Priority E を必要最小限で実施する。
fixture と stub の隔離対象だけを明記する。

## 作業単位のルール

- 1 回の変更では 3 から 6 ファイル程度に絞る
- 1 ファイルあたりの新規コメントは最小限に留める
- 既存コメントの表現とトーンをそろえる
- ロジック変更は混ぜない。必要なら別コミット相当の作業に分離する
- コメント追加後は unit test または build で accidental edit を検出する

## レビュー観点

レビューでは次を確認する。

- コメントを消してもコードは依然として読めるか
- コメントが「なぜ」を説明し、「何をしたか」の逐語説明に落ちていないか
- 設計意図が [docs/developer/architecture.md](docs/developer/architecture.md) と矛盾していないか
- コメントが runtime 境界や owner を誤解させていないか
- stale になりやすい具体値を埋め込んでいないか

## 検証方法

- `browser-extension/` で `npm run test`
- `browser-extension/` で `npm run build`
- 必要に応じてコメント追加対象の unit test を重点的に読む

今回の作業は文書化中心だが、コメント追加時に誤ってロジックへ触れていないことを毎回確認する。

## 今回の第一弾推奨範囲

最初の実装バッチは次の 8 から 12 ファイルを推奨する。

- `browser-extension/src/shared/contracts/messages.ts`
- `browser-extension/src/shared/config/phase0.ts`
- `browser-extension/src/background/entry.ts`
- `browser-extension/src/content/entry.ts`
- `browser-extension/src/popup/entry.ts`
- `browser-extension/src/background/usecases/runSelectionAnalysis.ts`
- `browser-extension/src/background/usecases/openOverlaySession.ts`
- `browser-extension/src/content/overlay/renderOverlay.ts`
- `browser-extension/src/content/selection/snapshotStore.ts`
- `browser-extension/src/popup/ui/renderPopup.ts`

これで新規参加者が最初に踏む導線と、もっとも誤解しやすい state ownership が先に説明される。
