"""DocumentModel の統合テスト。

実際の PyMuPDF を使ってフィクスチャファイルを操作し、
DocumentModel の全公開メソッドが仕様どおりに動くことを検証する。

テストカテゴリ:
- open_document: PDF/EPUB 正常オープン、存在しないファイル、パスワード保護
- render_page: PNG/JPEG レンダリング、キャッシュヒット、範囲外ページ
- extract_text: 既知テキスト領域の抽出
- extract_all_text: ページ区切りフォーマット
- close_document: クローズ後の状態
- LRU キャッシュ: 上限超過エビクション、DPI 別独立性
"""

from __future__ import annotations

import pytest

from pdf_epub_reader.dto import RectCoords
from pdf_epub_reader.models.document_model import DocumentModel
from pdf_epub_reader.utils.config import AppConfig
from pdf_epub_reader.utils.exceptions import (
    DocumentOpenError,
    DocumentPasswordRequired,
)


@pytest.fixture
def doc_model() -> DocumentModel:
    """テスト用デフォルト設定の DocumentModel を返す。"""
    config = AppConfig(page_cache_max_size=50)
    return DocumentModel(config=config)


@pytest.fixture
def small_cache_model() -> DocumentModel:
    """キャッシュ上限を 2 に絞った DocumentModel を返す。LRU テスト用。"""
    config = AppConfig(page_cache_max_size=2)
    return DocumentModel(config=config)


# =====================================================================
# open_document
# =====================================================================


class TestOpenDocument:
    """open_document メソッドの正常系・異常系を検証する。"""

    async def test_open_pdf(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """通常の PDF を正常にオープンできることを確認する。"""
        info = await doc_model.open_document(sample_pdf_path)
        assert info.total_pages == 3
        assert info.file_path == sample_pdf_path
        doc_model.close_document()

    async def test_open_epub(
        self, doc_model: DocumentModel, sample_epub_path: str
    ) -> None:
        """EPUB (PDF ベースフィクスチャ) を正常にオープンできることを確認する。"""
        info = await doc_model.open_document(sample_epub_path)
        assert info.total_pages == 3
        doc_model.close_document()

    async def test_open_pdf_extracts_toc(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """PDF の目次 (ToC) が正しく ToCEntry リストとして返されることを確認する。"""
        info = await doc_model.open_document(sample_pdf_path)
        assert len(info.toc) == 3
        assert info.toc[0].title == "Chapter 1"
        assert info.toc[0].page_number == 0  # 0-indexed
        assert info.toc[0].level == 1
        assert info.toc[2].title == "Section 2.1"
        assert info.toc[2].page_number == 2
        assert info.toc[2].level == 2
        doc_model.close_document()

    async def test_open_nonexistent_file(
        self, doc_model: DocumentModel
    ) -> None:
        """存在しないファイルを開くと DocumentOpenError が発生する。"""
        with pytest.raises(DocumentOpenError):
            await doc_model.open_document("/nonexistent/file.pdf")

    async def test_open_password_pdf_without_password(
        self, doc_model: DocumentModel, protected_pdf_path: str
    ) -> None:
        """パスワード保護 PDF を password=None で開くと DocumentPasswordRequired。"""
        with pytest.raises(DocumentPasswordRequired) as exc_info:
            await doc_model.open_document(protected_pdf_path)
        assert exc_info.value.file_path == protected_pdf_path

    async def test_open_password_pdf_with_correct_password(
        self, doc_model: DocumentModel, protected_pdf_path: str
    ) -> None:
        """正しいパスワードでパスワード保護 PDF を開けることを確認する。"""
        info = await doc_model.open_document(
            protected_pdf_path, password="test123"
        )
        assert info.total_pages == 2
        doc_model.close_document()

    async def test_open_password_pdf_with_wrong_password(
        self, doc_model: DocumentModel, protected_pdf_path: str
    ) -> None:
        """間違ったパスワードでは DocumentOpenError が発生する。"""
        with pytest.raises(DocumentOpenError):
            await doc_model.open_document(
                protected_pdf_path, password="wrong"
            )

    async def test_open_new_document_closes_previous(
        self, doc_model: DocumentModel, sample_pdf_path: str, protected_pdf_path: str
    ) -> None:
        """新しい文書を開くと前の文書が自動的にクローズされる。"""
        await doc_model.open_document(sample_pdf_path)
        info = await doc_model.open_document(
            protected_pdf_path, password="test123"
        )
        assert info.total_pages == 2
        doc_model.close_document()


# =====================================================================
# render_page
# =====================================================================


class TestRenderPage:
    """render_page メソッドのレンダリング結果を検証する。"""

    async def test_render_page_png(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """PNG フォーマットでレンダリングした画像が PNG ヘッダを持つ。"""
        await doc_model.open_document(sample_pdf_path)
        page = await doc_model.render_page(0, 72)
        assert page.page_number == 0
        assert page.image_data[:8] == b"\x89PNG\r\n\x1a\n"
        assert page.width > 0
        assert page.height > 0
        doc_model.close_document()

    async def test_render_page_jpeg(
        self, sample_pdf_path: str
    ) -> None:
        """JPEG フォーマットでレンダリングした画像が JPEG ヘッダを持つ。"""
        config = AppConfig(render_format="jpeg", jpeg_quality=85)
        model = DocumentModel(config=config)
        await model.open_document(sample_pdf_path)
        page = await model.render_page(0, 72)
        # JPEG ファイルは FFD8 で始まる。
        assert page.image_data[:2] == b"\xff\xd8"
        model.close_document()

    async def test_render_dpi_affects_size(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """DPI を倍にするとピクセルサイズも概ね倍になる。"""
        await doc_model.open_document(sample_pdf_path)
        page_72 = await doc_model.render_page(0, 72)
        page_144 = await doc_model.render_page(0, 144)
        # 幅・高さが概ね 2 倍 (整数丸めで完全一致しない可能性がある)。
        assert abs(page_144.width - page_72.width * 2) <= 2
        assert abs(page_144.height - page_72.height * 2) <= 2
        doc_model.close_document()

    async def test_render_out_of_range_returns_error_image(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """範囲外ページ番号ではエラーページ画像が返る (例外ではない)。"""
        await doc_model.open_document(sample_pdf_path)
        page = await doc_model.render_page(999, 72)
        # エラー画像は PNG として返される。
        assert page.image_data[:8] == b"\x89PNG\r\n\x1a\n"
        assert page.page_number == 999
        doc_model.close_document()

    async def test_cache_hit(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """同一 (page, dpi) を 2 回呼ぶとキャッシュヒットする。"""
        await doc_model.open_document(sample_pdf_path)
        page1 = await doc_model.render_page(0, 72)
        page2 = await doc_model.render_page(0, 72)
        # キャッシュヒット時は同一の bytes オブジェクトが返る。
        assert page1.image_data == page2.image_data
        doc_model.close_document()


# =====================================================================
# extract_text
# =====================================================================


class TestExtractText:
    """テキスト抽出メソッドの検証。"""

    async def test_extract_known_text(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """既知テキストが埋め込まれた領域から正しく抽出される。"""
        await doc_model.open_document(sample_pdf_path)
        # ページ全体をカバーする矩形で抽出する。
        rect = RectCoords(x0=0, y0=0, x1=612, y1=792)
        selection = await doc_model.extract_text(0, rect)
        assert "quick brown fox" in selection.extracted_text
        assert selection.page_number == 0
        doc_model.close_document()

    async def test_extract_empty_area(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """テキストのない領域からの抽出は空文字列になる。"""
        await doc_model.open_document(sample_pdf_path)
        # ページ下端のテキスト非存在域。
        rect = RectCoords(x0=0, y0=700, x1=100, y1=792)
        selection = await doc_model.extract_text(0, rect)
        assert selection.extracted_text.strip() == ""
        doc_model.close_document()


# =====================================================================
# extract_all_text
# =====================================================================


class TestExtractAllText:
    """全文抽出メソッドの検証。"""

    async def test_all_text_contains_page_separators(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """全文抽出結果が --- Page N --- 区切りで連結される。"""
        await doc_model.open_document(sample_pdf_path)
        text = await doc_model.extract_all_text()
        assert "--- Page 1 ---" in text
        assert "--- Page 2 ---" in text
        assert "--- Page 3 ---" in text
        doc_model.close_document()

    async def test_all_text_contains_known_content(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """全文抽出結果に各ページのテキストが含まれる。"""
        await doc_model.open_document(sample_pdf_path)
        text = await doc_model.extract_all_text()
        assert "quick brown fox" in text
        assert "Lorem ipsum" in text
        assert "Python" in text
        doc_model.close_document()


# =====================================================================
# close_document
# =====================================================================


class TestCloseDocument:
    """close_document の後処理を検証する。"""

    async def test_close_clears_info(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """クローズ後は get_document_info が None を返す。"""
        await doc_model.open_document(sample_pdf_path)
        assert doc_model.get_document_info() is not None
        doc_model.close_document()
        assert doc_model.get_document_info() is None

    async def test_close_clears_cache(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """クローズ後はページキャッシュが空になる。"""
        await doc_model.open_document(sample_pdf_path)
        await doc_model.render_page(0, 72)
        assert len(doc_model._page_cache) > 0
        doc_model.close_document()
        assert len(doc_model._page_cache) == 0


# =====================================================================
# LRU キャッシュ
# =====================================================================


class TestLRUCache:
    """LRU キャッシュの上限超過エビクションと DPI 別独立性を検証する。"""

    async def test_eviction_on_overflow(
        self, small_cache_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """キャッシュ上限 (2) を超えると最古エントリが除去される。"""
        model = small_cache_model
        await model.open_document(sample_pdf_path)

        await model.render_page(0, 72)
        await model.render_page(1, 72)
        assert len(model._page_cache) == 2

        # 3 ページ目をレンダリングすると最古 (page 0) がエビクトされる。
        await model.render_page(2, 72)
        assert len(model._page_cache) == 2
        assert (0, 72) not in model._page_cache
        assert (1, 72) in model._page_cache
        assert (2, 72) in model._page_cache
        model.close_document()

    async def test_different_dpi_cached_independently(
        self, doc_model: DocumentModel, sample_pdf_path: str
    ) -> None:
        """同一ページでも DPI が異なれば別キャッシュエントリになる。"""
        await doc_model.open_document(sample_pdf_path)
        await doc_model.render_page(0, 72)
        await doc_model.render_page(0, 144)
        assert (0, 72) in doc_model._page_cache
        assert (0, 144) in doc_model._page_cache
        doc_model.close_document()
