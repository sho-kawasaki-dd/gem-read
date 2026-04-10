"""Model 層の独自例外クラス。

Model が送出する例外はすべてここに定義し、Presenter が catch する。
View 層や外部ライブラリの例外をそのまま Presenter に漏らさないことで、
Model 内部の実装詳細（PyMuPDF 等）への依存を防ぐ。
"""

from __future__ import annotations


class DocumentError(Exception):
    """文書処理に関する基底例外。

    すべての文書関連エラーの親クラスとして機能し、
    Presenter が ``except DocumentError`` で一括 catch できるようにする。
    """


class DocumentOpenError(DocumentError):
    """文書ファイルのオープンに失敗した場合の例外。

    ファイルが存在しない、破損している、未対応形式など
    ファイルを開けないあらゆるケースで送出する。
    PyMuPDF 固有のエラーメッセージはここでラップして隠蔽する。
    """


class DocumentPasswordRequired(DocumentError):
    """パスワード保護された文書を無認証で開こうとした場合の例外。

    Presenter はこの例外を受け取ったら View にパスワード入力ダイアログを
    表示させ、ユーザーが入力したパスワードで再度 open_document() を呼ぶ。

    Attributes:
        file_path: パスワード保護が検出されたファイルのパス。
                   再試行時に Presenter が同じファイルを指定できるよう保持する。
    """

    def __init__(self, file_path: str, message: str = "Password required") -> None:
        super().__init__(message)
        self.file_path = file_path


class DocumentRenderError(DocumentError):
    """ページのレンダリングに失敗した場合の例外。

    破損ページや予期しない内部エラーで画像生成ができなかったときに送出する。
    DocumentModel 内部ではこの例外を catch してエラーページ画像を返すため、
    通常 Presenter まで到達しないが、致命的な場合に備えて定義しておく。

    Attributes:
        page_number: レンダリングに失敗したページ番号 (0-indexed)。
    """

    def __init__(self, page_number: int, message: str = "Render failed") -> None:
        super().__init__(message)
        self.page_number = page_number


# ---------------------------------------------------------------------------
# AI 関連例外
# ---------------------------------------------------------------------------


class AIError(Exception):
    """AI 系の基底例外。

    すべての AI 関連エラーの親クラスとして機能し、
    Presenter が ``except AIError`` で一括 catch できるようにする。
    """


class AIKeyMissingError(AIError):
    """API キーが未設定のまま API 呼び出しを試みた場合の例外。

    AIModel はキー未設定でもインスタンス化を許可する（ドキュメント閲覧専用
    利用を妨げないため）。実際の API 呼び出し時にこの例外を送出する。
    """


class AIAPIError(AIError):
    """Gemini API 通信エラーの汎用例外。

    google-genai SDK が返すエラーをラップし、Model 内部の SDK 依存を
    Presenter に漏らさないようにする。

    Attributes:
        status_code: HTTP ステータスコード (不明な場合は None)。
        message: エラーの詳細メッセージ。
    """

    def __init__(
        self,
        message: str = "API error",
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class AIRateLimitError(AIAPIError):
    """429 レート制限エラー（リトライ上限超過後に送出）。

    AIModel 内部で指数バックオフリトライを最大3回行い、
    それでも 429 が返る場合にこの例外を Presenter へ伝播させる。
    """

    def __init__(self, message: str = "API rate limit exceeded") -> None:
        super().__init__(message, status_code=429)
