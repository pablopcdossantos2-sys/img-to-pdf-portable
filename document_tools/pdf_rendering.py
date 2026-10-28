"""PDF page rendering helpers powered by Qt PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from document_tools.pdf_ops import parse_page_ranges


def export_pdf_pages_to_images(
    source_path: str | Path,
    output_directory: str | Path,
    *,
    image_format: str = "PNG",
    dpi: int = 150,
    quality: int = 90,
    pages: str = "",
    password: str | None = None,
) -> list[Path]:
    """Render selected PDF pages to PNG or JPEG files without overwriting outputs."""
    source = Path(source_path).expanduser().resolve()
    output = Path(output_directory).expanduser().resolve()
    selected_format = image_format.strip().upper()
    if selected_format not in {"PNG", "JPEG", "JPG"}:
        raise ValueError("Escolha PNG ou JPEG para exportar as páginas.")
    if not source.is_file() or source.suffix.casefold() != ".pdf":
        raise FileNotFoundError("Escolha um arquivo PDF existente.")
    if not output.is_dir():
        raise FileNotFoundError("Escolha uma pasta de saída existente.")
    if not 72 <= int(dpi) <= 600:
        raise ValueError("A resolução precisa ficar entre 72 e 600 DPI.")
    if not 1 <= int(quality) <= 100:
        raise ValueError("A qualidade JPEG precisa ficar entre 1 e 100.")

    document = QPdfDocument()
    created: list[Path] = []
    try:
        if password:
            document.setPassword(password)
        document.load(str(source))
        page_count = document.pageCount()
        if page_count < 1:
            raise ValueError(
                "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta."
            )
        indexes = (
            parse_page_ranges(pages, page_count)
            if pages.strip()
            else list(range(page_count))
        )
        suffix = ".png" if selected_format == "PNG" else ".jpg"
        encoder = "PNG" if selected_format == "PNG" else "JPEG"
        scale = int(dpi) / 72.0

        for page_index in indexes:
            point_size = document.pagePointSize(page_index)
            width = float(point_size.width())
            height = float(point_size.height())
            if width <= 0 or height <= 0:
                raise ValueError(f"Não foi possível obter o tamanho da página {page_index + 1}.")
            image_size = QSize(max(1, round(width * scale)), max(1, round(height * scale)))
            rendered = document.render(page_index, image_size)
            if rendered.isNull():
                raise ValueError(f"Não foi possível renderizar a página {page_index + 1}.")

            base_name = f"{source.stem}-pagina-{page_index + 1:03d}"
            destination = output / f"{base_name}{suffix}"
            duplicate_number = 2
            while destination.exists():
                destination = output / f"{base_name}-{duplicate_number}{suffix}"
                duplicate_number += 1

            image = rendered
            if encoder == "JPEG":
                # JPEG does not support alpha; composite over white instead of
                # allowing transparent pixels to turn black in the exported file.
                image = QImage(image_size, QImage.Format.Format_RGB32)
                image.fill(Qt.GlobalColor.white)
                painter = QPainter(image)
                painter.drawImage(0, 0, rendered)
                painter.end()
            if not image.save(str(destination), encoder, int(quality) if encoder == "JPEG" else -1):
                raise OSError(f"Não foi possível salvar a imagem da página {page_index + 1}.")
            created.append(destination)
        return created
    except Exception:
        # Keep successful earlier outputs; report the error without silently deleting
        # files the user may already have inspected.
        raise
    finally:
        document.close()
