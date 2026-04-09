"""文書処理 Model のスタブ実装。

Phase 3 で PyMuPDF ベースの本実装に差し替える。
Phase 2 では GUI の起動・操作確認用にダミーデータを返す。
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from pdf_epub_reader.dto import (
    DocumentInfo,
    PageData,
    RectCoords,
    TextSelection,
)


def _generate_stub_png(width: int, height: int, page_number: int) -> bytes:
    """指定サイズの灰色 PNG バイト列を生成する。

    PySide6 を Model にインポートできないため、Python 標準ライブラリの
    struct と zlib で最小限の PNG を組み立てる。
    ページ番号テキストの描画は行わず、単純な灰色の画像を返す。
    """

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        """PNG チャンクを構築する (length + type + data + CRC)。"""
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    # 灰色の RGB 値 (224, 224, 224) を全ピクセルに割り当てる。
    # 各行の先頭にフィルタバイト 0 (None) を付加する。
    gray = b"\xe0\xe0\xe0"
    raw_data = b""
    for _ in range(height):
        raw_data += b"\x00" + gray * width

    # PNG シグネチャ
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR: width, height, bit_depth=8, color_type=2 (RGB)
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b"IHDR", ihdr_data)

    # IDAT: deflate 圧縮した画像データ
    idat = _chunk(b"IDAT", zlib.compress(raw_data))

    # IEND
    iend = _chunk(b"IEND", b"")

    return signature + ihdr + idat + iend


class DocumentModel:
    """IDocumentModel のスタブ実装。Phase 3 で PyMuPDF に差し替える。"""

    def __init__(self) -> None:
        self._document_info: DocumentInfo | None = None

    async def open_document(self, file_path: str) -> DocumentInfo:
        """固定 5 ページの文書情報を返すスタブ。"""
        self._document_info = DocumentInfo(
            file_path=file_path,
            total_pages=5,
            title=Path(file_path).stem,
        )
        return self._document_info

    async def render_page(self, page_number: int, dpi: int) -> PageData:
        """灰色の PNG 画像バイト列を動的生成して PageData を返すスタブ。

        サイズは US Letter (612×792pt) を指定 DPI でスケーリングした値。
        """
        width = int(612 * dpi / 72)
        height = int(792 * dpi / 72)
        image_data = _generate_stub_png(width, height, page_number)
        return PageData(
            page_number=page_number,
            image_data=image_data,
            width=width,
            height=height,
        )

    async def render_page_range(
        self, start: int, end: int, dpi: int
    ) -> list[PageData]:
        """render_page を range で呼び出すだけのスタブ。"""
        return [
            await self.render_page(i, dpi) for i in range(start, end + 1)
        ]

    async def extract_text(
        self, page_number: int, rect: RectCoords
    ) -> TextSelection:
        """固定のスタブテキストを返す。"""
        return TextSelection(
            page_number=page_number,
            rect=rect,
            extracted_text=f"[Stub] Selected text from page {page_number + 1}",
        )

    async def extract_all_text(self) -> str:
        """固定の全文テキストを返すスタブ。"""
        return "[Stub] Full document text content for caching."

    def close_document(self) -> None:
        """内部状態を None にリセットする。"""
        self._document_info = None

    def get_document_info(self) -> DocumentInfo | None:
        """保持中の DocumentInfo を返す。"""
        return self._document_info
