"""Launch the desktop application or run a packaged-build smoke test."""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path


def _write_selftest_log(message: str) -> None:
    """Preserve diagnostics in windowed builds where stderr may be unavailable."""
    try:
        (Path(tempfile.gettempdir()) / "pdf-hub-selftest.log").write_text(
            message.rstrip() + "\n", encoding="utf-8"
        )
    except OSError:
        pass
    if sys.stderr is not None:
        print(message, file=sys.stderr)


def _selftest_failure(code: int, stage: str) -> int:
    _write_selftest_log(f"PDF Hub selftest failed ({code}): {stage}")
    return code


def selftest() -> int:
    """Instantiate the UI and verify bundled PDF, crypto and image dependencies."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    from PySide6.QtCore import QCoreApplication, QEvent, QSettings
    from PySide6.QtWidgets import QApplication
    from document_tools.gui import DocumentToolsWindow, PageThumbnailWorker
    from document_tools.pdf_ops import (
        convert_image,
        extract_pages,
        images_to_pdf,
        optimize_pdf,
        process_pdf_pipeline,
        reorder_pdf_pages,
        stamp_pdf,
    )
    from document_tools.pdf_rendering import export_pdf_pages_to_images

    # The packaged smoke test must not alter the real user's preferences.
    settings_directory = tempfile.TemporaryDirectory(prefix="pdf-hub-selftest-settings-")
    atexit.register(settings_directory.cleanup)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        settings_directory.name,
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
        thumbnail_pages: list[int] = []
        thumbnail_worker = PageThumbnailWorker(str(image_pdf))
        thumbnail_worker.thumbnail_ready.connect(
            lambda page_number, _image: thumbnail_pages.append(page_number)
        )
        thumbnail_worker.run()
        if thumbnail_pages != [1]:
            return _selftest_failure(6, "page thumbnail rendering")
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
                return _selftest_failure(2, "page extraction")
        with image_pdf.open("rb") as stream:
            result = PdfReader(stream)
            if len(result.pages) != 1:
                return _selftest_failure(3, "image-to-PDF conversion")
        for generated in (reordered_pdf, stamped_pdf, optimized_pdf, pipeline_pdf):
            with generated.open("rb") as stream:
                result = PdfReader(stream)
                if len(result.pages) != 1:
                    return _selftest_failure(4, "PDF document operations")
        with optimized_pdf.open("rb") as stream:
            if "PDF Hub" not in PdfReader(stream).pages[0].extract_text():
                return _selftest_failure(5, "optimized PDF text integrity")

        for image_format, extension in (("JPEG", ".jpg"), ("WEBP", ".webp"), ("TIFF", ".tif")):
            converted = convert_image(image_path, root / f"converted{extension}", image_format, quality=80)
            with Image.open(converted) as check:
                check.load()
                if check.width < 1 or check.height < 1:
                    return _selftest_failure(8, f"image conversion ({image_format})")

        rendered_dir = root / "rendered-pages"
        rendered_dir.mkdir()
        for image_format in ("PNG", "JPEG"):
            rendered = export_pdf_pages_to_images(image_pdf, rendered_dir, image_format=image_format, dpi=72, quality=80)
            if len(rendered) != 1 or not rendered[0].is_file() or rendered[0].stat().st_size == 0:
                return _selftest_failure(7, f"PDF page export ({image_format})")

    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        try:
            log_path = Path(tempfile.gettempdir()) / "pdf-hub-selftest.log"
            log_path.unlink(missing_ok=True)
            return selftest()
        except BaseException:
            import traceback
            _write_selftest_log(traceback.format_exc())
            return 1

    from document_tools.gui import main as run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
