"""Launch the desktop application or run a packaged-build smoke test."""

from __future__ import annotations

import os
import sys


def selftest() -> int:
    """Instantiate the UI and required libraries without showing the main window."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    from PySide6.QtWidgets import QApplication
    from document_tools.gui import DocumentToolsWindow

    del Image, PdfReader, PdfWriter
    application = QApplication([])
    window = DocumentToolsWindow()
    window.close()
    application.processEvents()
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    from document_tools.gui import main as run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
