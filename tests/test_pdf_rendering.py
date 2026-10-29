from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from document_tools.pdf_rendering import MAX_RENDER_PIXELS, export_pdf_pages_to_images


def test_pdf_rendering_reports_invalid_document(tmp_path: Path) -> None:
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a valid PDF")
    output = tmp_path / "images"
    output.mkdir()

    with pytest.raises(ValueError, match="Não foi possível abrir o PDF"):
        export_pdf_pages_to_images(source, output)


def test_pdf_rendering_refuses_excessive_pixel_dimensions(tmp_path: Path) -> None:
    source = tmp_path / "huge-page.pdf"
    output = tmp_path / "images"
    output.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=60000, height=60000)
    with source.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(ValueError, match="limite seguro de pixels"):
        export_pdf_pages_to_images(source, output, dpi=72)

    assert not list(output.iterdir())
    assert MAX_RENDER_PIXELS > 0


def test_rendering_preflights_all_pages_before_creating_outputs(tmp_path: Path) -> None:
    source = tmp_path / "mixed-pages.pdf"
    output = tmp_path / "images"
    output.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=60000, height=60000)
    with source.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(ValueError, match="limite seguro de pixels"):
        export_pdf_pages_to_images(source, output, dpi=72)

    assert list(output.iterdir()) == []


def test_png_export_has_opaque_white_background(tmp_path: Path) -> None:
    from PySide6.QtGui import QImage

    source = tmp_path / "blank.pdf"
    output = tmp_path / "images"
    output.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with source.open("wb") as stream:
        writer.write(stream)

    images = export_pdf_pages_to_images(source, output, image_format="PNG", dpi=72)
    assert len(images) == 1
    image = QImage(str(images[0]))
    assert not image.isNull()
    assert image.pixelColor(0, 0).alpha() == 255
    assert image.pixelColor(0, 0).red() >= 250


def test_rendering_can_be_cancelled_before_creating_outputs(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "images"
    output.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with source.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(RuntimeError, match="cancelada"):
        export_pdf_pages_to_images(source, output, should_cancel=lambda: True)
    assert list(output.iterdir()) == []
