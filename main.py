"""Launch the desktop application or run a packaged-build smoke test."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def selftest() -> int:
    """Instantiate the UI and verify bundled PDF, crypto and image dependencies."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    from document_tools.gui import DocumentToolsWindow
    from document_tools.pdf_ops import (
        extract_pages,
        images_to_pdf,
        optimize_pdf,
        process_pdf_pipeline,
        reorder_pdf_pages,
        stamp_pdf,
    )

    application = QApplication([])
    window = DocumentToolsWindow()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()

    with tempfile.TemporaryDirectory(prefix="document-tools-selftest-") as directory:
        root = Path(directory)
        image_path = root / "smoke.png"
        image_pdf = root / "image-result.pdf"
        reordered_pdf = root / "reordered.pdf"
        stamped_pdf = root / "stamped.pdf"
        optimized_pdf = root / "optimized.pdf"
        pipeline_pdf = root / "pipeline.pdf"
        with Image.new("RGBA", (24, 16), (60, 120, 200, 180)) as image:
            image.save(image_path)
        images_to_pdf([image_path], image_pdf)
        reorder_pdf_pages(image_pdf, [1], reordered_pdf)
        stamp_pdf(image_pdf, stamped_pdf, watermark_text="PDF Hub", page_numbering=True)
        optimize_pdf(stamped_pdf, optimized_pdf, mode="lossless")
        process_pdf_pipeline(
            image_pdf, pipeline_pdf,
            watermark_text="PDF Hub",
            page_numbering=True,
            optimize_mode="lossless",
        )

        encrypted_path = root / "encrypted.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=120, height=300)
        writer.encrypt(user_password="", owner_password="smoke-test", algorithm="AES-256")
        with encrypted_path.open("wb") as stream:
            writer.write(stream)

        extracted_path = root / "extracted.pdf"
        extract_pages(encrypted_path, "1", extracted_path)
        with extracted_path.open("rb") as stream:
            result = PdfReader(stream)
            if len(result.pages) != 1:
                return 2
        with image_pdf.open("rb") as stream:
            result = PdfReader(stream)
            if len(result.pages) != 1:
                return 3
        for generated in (reordered_pdf, stamped_pdf, optimized_pdf, pipeline_pdf):
            with generated.open("rb") as stream:
                result = PdfReader(stream)
                if len(result.pages) != 1:
                    return 4
        with optimized_pdf.open("rb") as stream:
            if "PDF Hub" not in PdfReader(stream).pages[0].extract_text():
                return 5

    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    from document_tools.gui import main as run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
