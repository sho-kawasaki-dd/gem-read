"""文書操作で層をまたいで受け渡すデータ型を定義するモジュール。

Phase 1 では Presenter と Model、Presenter と View の間で
PySide6 依存のオブジェクトを直接渡さない方針を取っている。
そのため、描画結果や選択情報はすべて Python 標準の型と
dataclass で表現し、このモジュールに集約する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass


SelectionReadState = Literal["pending", "ready", "error"]


@dataclass(frozen=True)
class RectCoords:
    """PDF ページ上の矩形領域を表す座標。

    なぜ専用の型を作るのか:
    - `(x0, y0, x1, y1)` の裸のタプルだと意味が読み取りづらい
    - View と Model で同じ座標系を共有していることを明示したい
    - 後からバリデーションや補助メソッドを追加しやすい

    座標系は PDF のページ座標を採用する。
    これは画面のピクセル座標ではなく、72dpi 基準の point 単位であり、
    ズーム率や表示 DPI が変わっても Model 側の解釈がぶれにくい。
    """

    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class PageData:
    """1ページ分の描画結果を表すデータ。

    `image_data` は View がそのまま描画に使えるバイト列を想定する。
    Presenter は画像の中身を解釈せず、Model が生成した結果を
    View に受け渡すだけに徹する。

    `width` と `height` を持たせている理由は、View が画像デコード前でも
    レイアウト計算やスクロール領域の見積もりを行えるようにするため。
    """

    page_number: int
    image_data: bytes
    width: int
    height: int


@dataclass(frozen=True)
class TextSelection:
    """矩形選択から抽出されたテキストを表すデータ。

    選択結果として文字列だけでなくページ番号と選択矩形を残すことで、
    後から「どこを選んだ結果なのか」を Presenter や View が参照できる。
    たとえば再ハイライト、再解析、履歴保存などに流用しやすくなる。
    """

    page_number: int
    rect: RectCoords
    extracted_text: str


@dataclass(frozen=True)
class ToCEntry:
    """目次 (Table of Contents) の 1 エントリを表すデータ。

    PDF/EPUB が持つ階層型の目次をフラットリストで表現する。
    `level` が階層の深さ（1 が最上位）を示し、View 側でインデント等の
    表示を調整できるようにする。

    PyMuPDF の ``doc.get_toc()`` が返す ``[level, title, page]`` を
    そのままマッピングする設計とした。page_number は 0-indexed に変換して格納する。
    """

    title: str
    page_number: int
    level: int


@dataclass(frozen=True)
class DocumentInfo:
    """開いた文書の基本メタデータ。

    ファイルパス・総ページ数・タイトルを切り出して保持することで、
    Presenter は Model の内部実装を知らずに UI 更新に必要な情報だけを扱える。
    `title` は PDF/EPUB に埋め込まれていない可能性があるため optional とする。
    `toc` は目次情報。目次を持たない文書では空リストとなる。
    `page_sizes` は各ページの PDF ポイント単位 (72dpi 基準) のサイズリスト。
    Presenter が DPI 換算してページごとに正確なプレースホルダーを生成するために使う。
    """

    file_path: str
    total_pages: int
    title: str | None = None
    toc: list[ToCEntry] = field(default_factory=list)
    page_sizes: list[tuple[float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class SelectionContent:
    """矩形選択から抽出されたマルチモーダルコンテンツ。

    Phase 4 で導入。テキストだけでなく、数式や埋め込み画像を含む
    選択領域の全情報をまとめて Presenter に返すためのデータ型。

    既存の ``TextSelection`` はテキスト専用で後方互換のため残すが、
    新規のマルチモーダルフローではこちらを使用する。

    Attributes:
        page_number: 0-indexed のページ番号。
        rect: 選択矩形の PDF ポイント座標。
        extracted_text: 選択矩形内のプレーンテキスト（常に抽出される）。
        cropped_image: 選択矩形をページ画像からクロップした PNG バイト列。
            自動検出またはユーザートグルにより付与される。不要時は None。
        embedded_images: PDF 内にオブジェクトとして埋め込まれた画像を
            個別に抽出したバイト列リスト。埋め込み画像検出時のみ使用。
        detection_reason: 自動検出でクロップ画像を付与した理由。
            ``"embedded_image"`` / ``"math_font"`` / ``None``。
            ユーザーがトグルで強制した場合は ``None``。
    """

    page_number: int
    rect: RectCoords
    extracted_text: str
    cropped_image: bytes | None = None
    embedded_images: list[bytes] = field(default_factory=list)
    detection_reason: str | None = None


@dataclass(frozen=True)
class SelectionSlot:
    """複数選択の 1 スロット分を表す DTO。

    1 回の矩形ドラッグごとに 1 スロットを払い出し、
    Presenter はこの DTO を順序付きで管理する。

    `selection_id` は削除や非同期完了差し込みの照合に使う内部安定 ID、
    `display_number` は UI 上に見せる 1 始まりの番号である。
    後者は削除後に詰め直されるが、前者は不変とする。

    `content` は SelectionContent をそのまま保持する後方互換用の入れ物で、
    テキストや画像バイト列を後続 Phase で再利用できるようにする。
    一方で View が一覧描画に必要な最小情報だけで扱えるよう、
    `extracted_text` と `has_thumbnail` も冗長に持たせている。
    """

    selection_id: str
    display_number: int
    page_number: int
    rect: RectCoords
    read_state: SelectionReadState
    extracted_text: str = ""
    has_thumbnail: bool = False
    content: SelectionContent | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class SelectionSnapshot:
    """現在の複数選択状態を順序付きで表すスナップショット。"""

    slots: tuple[SelectionSlot, ...] = ()

    @property
    def is_empty(self) -> bool:
        """選択スロットを 1 件も持たないかを返す。"""
        return not self.slots

    @property
    def combined_extracted_text(self) -> str:
        """抽出済みテキストを選択順で連結した文字列を返す。

        Phase 5 で明示的な区切り付きフォーマットに差し替える前段として、
        ここでは空文字を除いて単純改行連結する。
        """
        parts = [slot.extracted_text for slot in self.slots if slot.extracted_text]
        return "\n\n".join(parts)
