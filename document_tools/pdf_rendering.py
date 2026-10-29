"""PDF page rendering helpers powered by Qt PDF."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from document_tools.pdf_ops import parse_page_ranges


MAX_RENDER_PIXELS = 40_000_000


def export_pdf_pages_to_images(
    source_path: str | Path,
    output_directory: str | Path,
    *,
    image_format: str = "PNG",
    dpi: int = 150,
    quality: int = 90,
    pages: str = "",
    password: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
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
        load_error = document.load(str(source))
        error_name = str(getattr(load_error, "name", load_error)).rsplit(".", 1)[-1].casefold()
        if load_error is not None and error_name not in {"none", "none_", "noerror"}:
            if "password" in error_name:
                raise ValueError("A senha do PDF está incorreta ou não foi informada.")
            raise ValueError(
                "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta."
            )
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

        # Validate every selected page before creating any output files.
        render_plan: list[tuple[int, QSize]] = []
        for page_index in indexes:
            point_size = document.pagePointSize(page_index)
            width = float(point_size.width())
            height = float(point_size.height())
            if width <= 0 or height <= 0:
                raise ValueError(f"Não foi possível obter o tamanho da página {page_index + 1}.")
            pixel_width = max(1, round(width * scale))
            pixel_height = max(1, round(height * scale))
            if pixel_width * pixel_height > MAX_RENDER_PIXELS:
                raise ValueError(
                    "A página ultrapassa o limite seguro de pixels. Reduza a resolução de saída."
                )
            render_plan.append((page_index, QSize(pixel_width, pixel_height)))

        for completed, (page_index, image_size) in enumerate(render_plan, start=1):
            if should_cancel is not None and should_cancel():
                raise RuntimeError("A exportação de páginas foi cancelada.")
            rendered = document.render(page_index, image_size)
            if rendered.isNull():
                raise MemoryError(
                    f"Não foi possível alocar memória para renderizar a página {page_index + 1}."
                )

            base_name = f"{source.stem}-pagina-{page_index + 1:03d}"
            image = rendered
            try:
                # Use an opaque white background for PNG and JPEG whenever Qt
                # returns alpha; JPEG always needs an opaque RGB image.
                if encoder == "JPEG" or rendered.hasAlphaChannel():
                    image = QImage(image_size, QImage.Format.Format_RGB32)
                    if image.isNull():
                        raise MemoryError(
                            f"Não há memória suficiente para preparar a página {page_index + 1}."
                        )
                    image.fill(Qt.GlobalColor.white)
                    painter = QPainter(image)
                    painter.drawImage(0, 0, rendered)
                    painter.end()
                    rendered = QImage()

                descriptor, temporary_name = tempfile.mkstemp(
                    prefix=".pdf-hub-", suffix=suffix, dir=str(output)
                )
                os.close(descriptor)
                temporary = Path(temporary_name)
                try:
                    quality_value = int(quality) if encoder == "JPEG" else -1
                    if not image.save(str(temporary), encoder, quality_value):
                        raise OSError(
                            f"Não foi possível salvar a imagem da página {page_index + 1}."
                        )
                    duplicate_number = 1
                    while True:
                        filename = (
                            f"{base_name}{suffix}"
                            if duplicate_number == 1
                            else f"{base_name}-{duplicate_number}{suffix}"
                        )
                        destination = output / filename
                        try:
                            os.link(temporary, destination)
                            break
                        except FileExistsError:
                            duplicate_number += 1
                        except OSError:
                            # Filesystems without hard-link support still use an
                            # exclusive create, so a concurrent run cannot overwrite.
                            try:
                                file_descriptor = os.open(
                                    destination,
                                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                                    0o600,
                                )
                            except FileExistsError:
                                duplicate_number += 1
                                continue
                            try:
                                with os.fdopen(file_descriptor, "wb") as target, temporary.open("rb") as source_stream:
                                    shutil.copyfileobj(source_stream, target)
                            except Exception:
                                destination.unlink(missing_ok=True)
                                raise
                            break
                    created.append(destination)
                finally:
                    temporary.unlink(missing_ok=True)
            finally:
                if image is not rendered:
                    image = QImage()
            if progress_callback is not None:
                progress_callback(completed, len(render_plan))
        return created
    except Exception:
        # The operation owns every file in created; remove these outputs on failure
        # so the destination folder never looks like a complete export when it is not.
        for path in created:
            path.unlink(missing_ok=True)
        raise
    finally:
        document.close()
