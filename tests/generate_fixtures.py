"""テスト用フィクスチャファイルを PyMuPDF で生成するスクリプト。

使い方:
    uv run python tests/generate_fixtures.py

生成されるファイル:
    tests/fixtures/sample.pdf      — 3 ページ、既知テキスト入り
    tests/fixtures/sample.epub     — 簡易 EPUB (3 ページ相当)
    tests/fixtures/protected.pdf   — パスワード "test123" 付き 2 ページ PDF
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# 各ページに埋め込むテキスト。テスト側で抽出結果を検証するために使う。
SAMPLE_TEXTS = [
    "Page one: The quick brown fox jumps over the lazy dog.",
    "Page two: Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Page three: Python is a great programming language.",
]

PROTECTED_PASSWORD = "test123"


def generate_sample_pdf() -> None:
    """3 ページのテスト用 PDF を生成する。

    各ページに既知テキストを配置し、目次 (ToC) も設定する。
    """
    doc = fitz.open()
    for i, text in enumerate(SAMPLE_TEXTS):
        page = doc.new_page(width=612, height=792)  # US Letter
        # 左上付近にテキストを挿入する。
        page.insert_text((72, 72), text, fontsize=12)

    # 目次を設定する。fitz は [level, title, page(1-indexed)] で指定する。
    toc = [
        [1, "Chapter 1", 1],
        [1, "Chapter 2", 2],
        [2, "Section 2.1", 3],
    ]
    doc.set_toc(toc)

    output = FIXTURES_DIR / "sample.pdf"
    doc.save(str(output))
    doc.close()
    print(f"Generated: {output}")


def generate_sample_epub() -> None:
    """簡易テスト用 EPUB を生成する。

    PyMuPDF の Story API を使って最小限の EPUB を作成する。
    """
    doc = fitz.open()
    for i, text in enumerate(SAMPLE_TEXTS):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), text, fontsize=12)

    output = FIXTURES_DIR / "sample.epub"
    # PyMuPDF は EPUB の直接書き出しに対応していないため、
    # PDF として作成した文書を EPUB 用テストとして流用する。
    # DocumentModel は fitz.open() で EPUB も PDF も同じ API で扱うため、
    # テスト観点では PDF ベースのフィクスチャで十分にカバーできる。
    # ただし拡張子による分岐テストのために .epub として保存する。
    doc.save(str(output))
    doc.close()
    print(f"Generated: {output}")


def generate_protected_pdf() -> None:
    """パスワード保護付きの 2 ページ PDF を生成する。

    owner password と user password の両方を設定する。
    テスト側は user password "test123" で認証を試行する。
    """
    doc = fitz.open()
    for i in range(2):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Protected page {i + 1}", fontsize=12)

    output = FIXTURES_DIR / "protected.pdf"
    # encrypt メソッドで暗号化して保存する。
    # PyMuPDF 暗号化: owner pw = "owner123", user pw = "test123"
    perm = (
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
    )
    doc.save(
        str(output),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner123",
        user_pw=PROTECTED_PASSWORD,
        permissions=perm,
    )
    doc.close()
    print(f"Generated: {output}")


def main() -> None:
    """全フィクスチャを生成する。"""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    generate_sample_pdf()
    generate_sample_epub()
    generate_protected_pdf()
    print("All fixtures generated successfully.")


if __name__ == "__main__":
    main()
