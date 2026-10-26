from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from document_tools.pdf_ops import (
    convert_image,
    extract_pages,
    images_to_pdf,
    merge_pdfs,
    parse_page_ranges,
    rotate_pdf,
    split_pdf,
)


def create_pdf(path: Path, widths: list[float]) -> Path:
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=300)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def test_parse_page_ranges_expands_ranges_and_preserves_order() -> None:
    assert parse_page_ranges("3, 1-2, 5, 8-9", 9) == [2, 0, 1, 4, 7, 8]


@pytest.mark.parametrize(
    ("specification", "page_count", "message"),
    [
        ("", 5, "Informe páginas"),
        ("1,,2", 5, "item vazio"),
        ("1-0", 5, "precisa estar"),
        ("2-6", 5, "precisa estar"),
        ("1, 1-2", 5, "informada mais de uma vez"),
        ("1-a", 5, "inválido"),
    ],
)
def test_parse_page_ranges_rejects_invalid_input(
    specification: str, page_count: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_page_ranges(specification, page_count)


def test_images_to_pdf_creates_one_a4_page_per_image(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    landscape = tmp_path / "landscape.png"
    output = tmp_path / "images.pdf"
    Image.new("RGB", (400, 800), "red").save(portrait)
    Image.new("RGB", (800, 400), "blue").save(landscape)

    result = images_to_pdf([portrait, landscape], output)

    assert result == output.resolve()
    reader = PdfReader(str(output))
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.height) > float(reader.pages[0].mediabox.width)
    assert float(reader.pages[1].mediabox.width) > float(reader.pages[1].mediabox.height)


def test_merge_pdfs_preserves_document_order(tmp_path: Path) -> None:
    first = create_pdf(tmp_path / "first.pdf", [120, 130])
    second = create_pdf(tmp_path / "second.pdf", [220, 230, 240])
    output = tmp_path / "merged.pdf"

    merge_pdfs([first, second], output)

    reader = PdfReader(str(output))
    assert len(reader.pages) == 5
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [
        120, 130, 220, 230, 240
    ]


def test_extract_pages_keeps_requested_order(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140, 150])
    output = tmp_path / "extracted.pdf"

    extract_pages(source, "5, 2-3", output)

    reader = PdfReader(str(output))
    assert len(reader.pages) == 3
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [
        150, 120, 130
    ]


def test_rotate_pdf_rotates_only_requested_pages(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120, 130, 140])
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, output, 90, "2")

    reader = PdfReader(str(output))
    assert [int(page.get("/Rotate", 0)) for page in reader.pages] == [0, 90, 0]


def test_split_pdf_creates_one_file_per_page_and_refuses_overwrite(
    tmp_path: Path,
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120, 130, 140])
    output_dir = tmp_path / "split"
    output_dir.mkdir()

    outputs = split_pdf(source, output_dir)

    assert [path.name for path in outputs] == [
        "source-pagina-001.pdf",
        "source-pagina-002.pdf",
        "source-pagina-003.pdf",
    ]
    assert all(len(PdfReader(str(path)).pages) == 1 for path in outputs)
    with pytest.raises(FileExistsError, match="já contém"):
        split_pdf(source, output_dir)


def test_convert_image_resizes_and_converts_to_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "converted.jpg"
    Image.new("RGBA", (800, 400), (50, 150, 230, 120)).save(source)

    convert_image(
        source,
        output,
        "JPEG",
        max_width=300,
        max_height=300,
        quality=85,
    )

    with Image.open(output) as converted:
        assert converted.format == "JPEG"
        assert converted.size == (300, 150)


def test_operations_never_overwrite_their_source(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120])
    with pytest.raises(ValueError, match="não pode substituir"):
        extract_pages(source, "1", source)
