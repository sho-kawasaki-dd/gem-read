## Plan: Phase 1 Retro Documentation

Phase 1 までに実装済みの browser-extension と src/browser_api、それに対応するテストコードを対象に、日本語の Docstring と Why を補う inline comment を後付けする計画です。方針は、薄い entry には責務境界だけを短く書き、複雑な orchestration、座標変換、runtime message、依存注入、degraded fallback にだけ説明を厚く入れます。自明な代入や型どおりの処理にはコメントを増やしません。

**Steps**

1. コメント規約を先に固定します。TypeScript は module と exported function を中心に短い説明を入れ、inline comment は複数段の処理や設計判断に限定します。Python は module docstring と public method docstring を基本にし、adapter と fallback 分岐だけ補助コメントを足します。テストは fixture、stub、mock の存在理由と、そのテストが固定したい契約だけを書きます。
2. 対象マトリクスを作ります。browser-extension/src、src/browser_api、browser-extension/**tests**、tests/test_browser_api を対象にし、各ファイルを「薄く書く」「厚く書く」「対象外」に分類します。manifest や build 設定、docs 更新、pdf_epub_reader 本体は今回の主対象から外します。
3. browser-extension の entry と contract 層を先に文書化します。background.ts、content.ts、popup.ts、background/entry.ts、content/entry.ts、messages.ts、shared/contracts/messages.ts に、thin entry を守る理由、message contract を shared に集約する理由、Local API を background 経由で呼ぶ理由を短く入れます。
4. browser-extension の複雑ロジック層を重点的に文書化します。background/usecases/runSelectionAnalysis.ts では loading → selection/capture or cache reuse → API call → success or error の流れを説明し、cached session を使う理由を書きます。background/services/cropSelectionImage.ts では viewport 座標を screenshot bitmap 座標へ変換する理由と長辺制限の意図を書きます。content/selection/snapshotStore.ts では snapshot を保持する理由と union rect の意味を書きます。content/overlay/renderOverlay.ts では overlay state を module 側で持つ理由と action を background に委譲する理由を書きます。
5. browser-extension の gateway と popup も補強します。shared/gateways/localApiGateway.ts に localhost 制約と degraded fallback の意図を入れ、shared/storage/settingsStorage.ts に設定永続化の責務境界を補います。popup/ui/renderPopup.ts には、Phase 1 の popup が本格 UI ではなく設定と疎通確認を担う理由を書きます。
6. src/browser_api の HTTP boundary を文書化します。main.py、**main**.py、api/app.py、api/dependencies.py、api/error_handlers.py、api/routers/analyze.py、api/routers/models.py、api/routers/health.py に、app factory を薄く保つ理由、lifespan で依存を一度だけ束ねる理由、router が service に委譲する理由、HTTP error mapping を一箇所に寄せる理由を書きます。
7. src/browser_api の application と adapter を重点的に文書化します。application/services/analyze_service.py を最優先にし、既存の AIModel を router から直接呼ばず service 経由にしている理由、model resolution fallback、Base64 image decode、mock response で extension 側の導線確認を可能にしている理由を明記します。adapters/ai_gateway.py と adapters/config_gateway.py には、pdf_epub_reader 側資産との結合点を adapter に閉じ込める理由を書きます。application/dto.py と api/schemas/analyze.py には、HTTP schema と application DTO を分ける理由を短く補います。
8. テストコードは「仕様の意図が読める最小限の補助コメント」で整えます。browser-extension/**tests**/setup.ts と mocks/chrome.ts に共通 fixture 化の理由を書きます。unit/background/runSelectionAnalysis.test.ts、unit/background/cropSelectionImage.test.ts、unit/content/snapshotStore.test.ts、unit/content/renderOverlay.test.ts、unit/popup/renderPopup.test.ts、unit/shared/localApiGateway.test.ts、unit/shared/settingsStorage.test.ts に、どの runtime contract を固定しているテストかを書きます。Python 側は tests/test_browser_api/conftest.py、test_application/test_analyze_service.py、test_api/test_analyze_router.py、test_api/test_models_router.py、test_api/test_health.py に、dependency override、stub gateway、fallback 検証の切り分け意図を補います。
9. 最後にコメント品質レビューを行います。観点は「What の言い換えになっていないか」「責務境界か設計判断を説明しているか」「同じ説明を複数ファイルへ重複させていないか」「日本語だが識別子や外部 API 名は原語のままで検索しやすいか」です。

**Verification**

1. browser-extension の unit test を実行して、コメント追加中の accidental edit がないことを確認します。
2. uv run pytest tests/test_browser_api/ -q を実行して、browser_api 側の accidental edit がないことを確認します。
3. spot review として runSelectionAnalysis.ts、cropSelectionImage.ts、renderOverlay.ts、analyze_service.py、tests/test_browser_api/conftest.py を初見で読み、「なぜ background 経由なのか」「なぜ mock fallback があるのか」「なぜ snapshot を保持するのか」がコメントだけで追えるかを確認します。

**Decisions**

- コメント言語は日本語で進めます。
- 本番コードだけでなく、Phase 1 を支えるテストコードも対象に含めます。
- docs 更新は今回の主対象外です。必要なら別タスクで開発者向け文書へ反映します。
- browser-extension 側と src/browser_api 側は、コメント規約を固めたあと並列で進められます。
