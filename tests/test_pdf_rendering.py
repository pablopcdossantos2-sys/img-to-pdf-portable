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
