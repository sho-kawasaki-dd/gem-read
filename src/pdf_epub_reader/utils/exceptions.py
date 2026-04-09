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
