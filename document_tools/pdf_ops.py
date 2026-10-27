"""Local PDF and image operations used by the desktop interface."""

from __future__ import annotations

import os
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
SUPPORTED_OUTPUT_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}
ALPHA_MODES = {"RGBA", "LA", "PA"}


def parse_page_ranges(
    specification: str,
    page_count: int,
    *,
    allow_duplicates: bool = False,
) -> list[int]:
    """Convert page numbers and ranges to zero-based indexes in the supplied order."""
    if page_count < 1:
        raise ValueError("O PDF não possui páginas.")
    if not specification or not specification.strip():
        raise ValueError("Informe páginas, por exemplo: 1-3, 5, 8-10.")

    indexes: list[int] = []
    seen: set[int] = set()
    segments = [part.strip() for part in specification.split(",")]
    if any(not part for part in segments):
        raise ValueError("Há um item vazio na lista de páginas.")

    for segment in segments:
        pieces = [part.strip() for part in segment.split("-")]
        if len(pieces) not in (1, 2) or not all(piece.isdecimal() for piece in pieces):
            raise ValueError(f"Intervalo de páginas inválido: '{segment}'.")
        start = int(pieces[0])
        end = int(pieces[-1])
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"O intervalo '{segment}' precisa estar entre 1 e {page_count}.")

        for page_number in range(start, end + 1):
            if page_number in seen and not allow_duplicates:
                raise ValueError(f"A página {page_number} foi informada mais de uma vez.")
            seen.add(page_number)
            indexes.append(page_number - 1)

    return indexes


def _normalise_pdf_paths(
    source_paths: Sequence[str | Path],
    output_path: str | Path,
) -> tuple[list[Path], Path]:
    if not source_paths:
        raise ValueError("Selecione pelo menos um arquivo de origem.")
    sources = [Path(path).expanduser().resolve() for path in source_paths]
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de saída precisa ter a extensão .pdf.")
    if not output.parent.is_dir():
        raise FileNotFoundError("A pasta de destino não existe.")
    if output in sources:
        raise ValueError("O arquivo de saída não pode substituir um arquivo de origem.")
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Arquivo não encontrado: {missing[0]}")
    return sources, output


def _validate_file_mode(file_mode: int) -> None:
    if file_mode not in (0o600, 0o644):
        raise ValueError("As permissões de saída devem ser 0600 (somente usuário) ou 0644 (compartilhadas).")


def _atomic_pdf_save(
    output: Path,
    write_document: Callable[[Path], None],
    *,
    overwrite: bool = True,
    file_mode: int = 0o600,
) -> None:
    _validate_file_mode(file_mode)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pdf-hub-", suffix=".pdf", dir=str(output.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        write_document(temporary)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise OSError("O arquivo PDF temporário ficou vazio.")
        if os.name != "nt":
            os.chmod(temporary, file_mode)
        if overwrite:
            os.replace(temporary, output)
        else:
            os.link(temporary, output)
            temporary.unlink()
    finally:
        temporary.unlink(missing_ok=True)


def _open_reader(path: Path, stream, password: str | None = None):
    reader = PdfReader(stream, strict=False)
    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt(password if password is not None else "")
        except Exception as error:
            if password is not None:
                raise ValueError(f"A senha informada para o PDF '{path.name}' está incorreta ou não pôde ser usada.") from error
            raise ValueError(f"O PDF '{path.name}' exige uma senha. Informe-a para continuar.") from error
        if not decrypted:
            if password is not None:
                raise ValueError(f"A senha informada para o PDF '{path.name}' está incorreta.")
            raise ValueError(f"O PDF '{path.name}' exige uma senha. Informe-a para continuar.")
    if len(reader.pages) < 1:
        raise ValueError(f"O PDF '{path.name}' não contém páginas.")
    return reader


def pdf_requires_user_password(path: str | Path) -> bool:
    """Return whether an encrypted PDF cannot be opened with an empty password."""
    source = Path(path).expanduser().resolve()
    with source.open("rb") as stream:
        reader = PdfReader(stream, strict=False)
        if not reader.is_encrypted:
            return False
        try:
            return not bool(reader.decrypt(""))
        except Exception:
            return True


def _copy_metadata(reader: PdfReader, writer: PdfWriter) -> None:
    metadata = reader.metadata
    if metadata:
        safe_metadata = {
            str(key): str(value)
            for key, value in metadata.items()
            if key and value is not None and str(key).startswith("/")
        }
        if safe_metadata:
            writer.add_metadata(safe_metadata)


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Composite transparency over white and return an independent RGB image."""
    rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, "white")
    try:
        flattened.paste(rgba, (0, 0), rgba.getchannel("A"))
    except Exception:
        flattened.close()
        raise
    finally:
        rgba.close()
    return flattened


def _resize_to_a4(image: Image.Image, *, dpi: int, margin_mm: float) -> Image.Image:
    portrait_width = round(210 / 25.4 * dpi)
    portrait_height = round(297 / 25.4 * dpi)
    if image.width > image.height:
        page_width, page_height = portrait_height, portrait_width
    else:
        page_width, page_height = portrait_width, portrait_height
    margin_pixels = round(margin_mm * dpi / 25.4)
    available = (page_width - (2 * margin_pixels), page_height - (2 * margin_pixels))
    if min(available) < 1:
        raise ValueError("As margens não deixam espaço suficiente na página.")
    image.thumbnail(available, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (page_width, page_height), "white")
    canvas.paste(
        image,
        ((page_width - image.width) // 2, (page_height - image.height) // 2),
    )
    return canvas


def images_to_pdf(
    image_paths: Sequence[str | Path],
    output_path: str | Path,
    *,
    dpi: int = 150,
    margin_mm: float = 10,
    all_frames: bool = True,
    file_mode: int = 0o600,
) -> Path:
    """Create an A4 PDF, optionally importing all frames/pages from multipage images."""
    if not image_paths:
        raise ValueError("Adicione pelo menos uma imagem.")
    if dpi < 72 or dpi > 600:
        raise ValueError("A resolução precisa ficar entre 72 e 600 DPI.")
    if margin_mm < 0 or margin_mm > 40:
        raise ValueError("A margem precisa ficar entre 0 e 40 mm.")
    _validate_file_mode(file_mode)
    sources = [Path(path).expanduser().resolve() for path in image_paths]
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de saída precisa ter a extensão .pdf.")
    if not output.parent.is_dir():
        raise FileNotFoundError("A pasta de destino não existe.")
    if output in sources:
        raise ValueError("O arquivo de saída não pode substituir uma imagem de origem.")
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"Imagem não encontrada: {source}")
        if source.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(f"Formato de imagem não suportado: {source.name}")

    def write(temporary: Path) -> None:
        writer = PdfWriter()
        page_number = 0
        with tempfile.TemporaryDirectory(prefix="pdf-hub-pages-") as temp_dir:
            page_directory = Path(temp_dir)
            for source in sources:
                with Image.open(source) as opened:
                    frame_count = max(1, int(getattr(opened, "n_frames", 1)))
                    frame_indexes = range(frame_count) if all_frames else range(1)
                    for frame_index in frame_indexes:
                        opened.seek(frame_index)
                        oriented = ImageOps.exif_transpose(opened)
                        try:
                            image = _flatten_to_rgb(oriented)
                        finally:
                            if oriented is not opened:
                                oriented.close()
                        try:
                            canvas = _resize_to_a4(image, dpi=dpi, margin_mm=margin_mm)
                        finally:
                            image.close()
                        page_number += 1
                        page_pdf = page_directory / f"page-{page_number:06d}.pdf"
                        try:
                            canvas.save(page_pdf, format="PDF", resolution=dpi, quality=95)
                        finally:
                            canvas.close()
                        with page_pdf.open("rb") as page_stream:
                            page_reader = PdfReader(page_stream, strict=False)
                            writer.add_page(page_reader.pages[0])
        writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def merge_pdfs(
    pdf_paths: Sequence[str | Path],
    output_path: str | Path,
    *,
    passwords: Sequence[str | None] | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Join PDFs, optionally using a per-document password, and import bookmarks where possible."""
    if len(pdf_paths) < 2:
        raise ValueError("Selecione pelo menos dois PDFs para unir.")
    if passwords is not None and len(passwords) != len(pdf_paths):
        raise ValueError("Informe uma senha por PDF ou deixe a senha como None.")
    _validate_file_mode(file_mode)
    sources, output = _normalise_pdf_paths(pdf_paths, output_path)

    def write(temporary: Path) -> None:
        writer = PdfWriter()
        for index, source in enumerate(sources):
            password = passwords[index] if passwords is not None else None
            with source.open("rb") as stream:
                reader = _open_reader(source, stream, password=password)
                writer.append(reader, import_outline=True)
                if index == 0:
                    _copy_metadata(reader, writer)
        writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def extract_pages(
    input_path: str | Path,
    page_ranges: str,
    output_path: str | Path,
    *,
    allow_duplicates: bool = False,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Save selected pages and preserve related PDF structures where pypdf supports it."""
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            indexes = parse_page_ranges(
                page_ranges, len(reader.pages), allow_duplicates=allow_duplicates
            )
            writer = PdfWriter()
            writer.append(reader, pages=indexes, import_outline=True)
            _copy_metadata(reader, writer)
            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def rotate_pdf(
    input_path: str | Path,
    output_path: str | Path,
    angle: int,
    page_ranges: str | None = None,
    *,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Rotate pages while retaining document-level structures where pypdf supports it."""
    if angle not in (90, 180, 270):
        raise ValueError("Escolha uma rotação de 90, 180 ou 270 graus.")
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            indexes = (
                set(range(len(reader.pages)))
                if page_ranges is None or not page_ranges.strip()
                else set(parse_page_ranges(page_ranges, len(reader.pages), allow_duplicates=True))
            )
            writer = PdfWriter()
            writer.append(reader, import_outline=True)
            _copy_metadata(reader, writer)
            for index in indexes:
                writer.pages[index].rotate(angle)
            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def split_pdf(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    password: str | None = None,
    file_mode: int = 0o600,
) -> list[Path]:
    """Split a PDF while preserving page annotations/bookmarks where supported."""
    source = Path(input_path).expanduser().resolve()
    directory = Path(output_directory).expanduser().resolve()
    _validate_file_mode(file_mode)
    if not source.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {source}")
    if source.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de origem precisa ser PDF.")
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise FileNotFoundError("Não foi possível criar a pasta de destino.")

    created: list[Path] = []
    with source.open("rb") as stream:
        reader = _open_reader(source, stream, password=password)
        width = max(3, len(str(len(reader.pages))))
        outputs = [
            directory / f"{source.stem}-pagina-{index + 1:0{width}d}.pdf"
            for index in range(len(reader.pages))
        ]
        conflicts = [path.name for path in outputs if path.exists()]
        if conflicts:
            raise FileExistsError(
                f"A pasta já contém '{conflicts[0]}'. Escolha outra pasta ou remova os arquivos conflitantes."
            )
        try:
            for index, target in enumerate(outputs):
                writer = PdfWriter()
                writer.append(reader, pages=[index], import_outline=True)
                _copy_metadata(reader, writer)
                _atomic_pdf_save(
                    target,
                    lambda temporary, current_writer=writer: current_writer.write(temporary),
                    overwrite=False,
                    file_mode=file_mode,
                )
                created.append(target)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return outputs


def _format_image_for_output(image: Image.Image, image_format: str) -> Image.Image:
    """Return a copy with a pixel mode supported by the requested output format."""
    has_transparency = image.mode in ALPHA_MODES or "transparency" in image.info
    if image_format in {"JPEG", "BMP"} and has_transparency:
        return _flatten_to_rgb(image)
    if image_format == "WEBP" and has_transparency:
        return image.copy() if image.mode in {"RGBA", "LA"} else image.convert("RGBA")
    if image_format == "JPEG":
        return image.copy() if image.mode in {"RGB", "L"} else image.convert("RGB")
    if image_format == "BMP":
        return image.copy() if image.mode in {"RGB", "L"} else image.convert("RGB")
    if image_format in {"PNG", "WEBP"}:
        if image.mode == "CMYK" or (image_format == "WEBP" and image.mode not in {"RGB", "RGBA", "L"}):
            return image.convert("RGB")
    return image.copy()


def convert_image(
    input_path: str | Path,
    output_path: str | Path,
    output_format: str,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 90,
    file_mode: int = 0o600,
) -> Path:
    """Convert or resize an image, preserving compatible embedded ICC profiles."""
    source = Path(input_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    image_format = output_format.upper().strip()
    if image_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Formato de saída não suportado: {output_format}")
    expected_suffixes = {
        "JPEG": {".jpg", ".jpeg"},
        "PNG": {".png"},
        "WEBP": {".webp"},
        "BMP": {".bmp"},
        "TIFF": {".tif", ".tiff"},
    }
    if output.suffix.lower() not in expected_suffixes[image_format]:
        raise ValueError(f"A extensão de saída não corresponde ao formato {image_format}.")
    if not source.is_file():
        raise FileNotFoundError(f"Imagem não encontrada: {source}")
    if source == output:
        raise ValueError("O arquivo de saída não pode substituir a imagem de origem.")
    if not output.parent.is_dir():
        raise FileNotFoundError("A pasta de destino não existe.")
    if max_width is not None and max_width < 1:
        raise ValueError("A largura máxima precisa ser maior que zero.")
    if max_height is not None and max_height < 1:
        raise ValueError("A altura máxima precisa ser maior que zero.")
    if not 1 <= quality <= 100:
        raise ValueError("A qualidade precisa ficar entre 1 e 100.")
    _validate_file_mode(file_mode)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".pdf-hub-", suffix=output.suffix or ".tmp", dir=str(output.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    image: Image.Image | None = None
    final_image: Image.Image | None = None
    try:
        with Image.open(source) as opened:
            original_mode = opened.mode
            icc_profile = opened.info.get("icc_profile")
            image = ImageOps.exif_transpose(opened)
            image.load()
            if max_width or max_height:
                bounds = (max_width or image.width, max_height or image.height)
                image.thumbnail(bounds, Image.Resampling.LANCZOS)

            final_image = _format_image_for_output(image, image_format)
            save_options: dict[str, object] = {}
            if image_format in {"JPEG", "WEBP"}:
                save_options["quality"] = quality
                if image_format == "JPEG":
                    save_options["optimize"] = True
                else:
                    save_options["method"] = 6

            profile_compatible = (
                image_format != "BMP"
                and bool(icc_profile)
                and (
                    original_mode == final_image.mode
                    or (original_mode in {"RGB", "RGBA"} and final_image.mode == "RGB")
                )
            )
            if profile_compatible:
                save_options["icc_profile"] = icc_profile

            final_image.save(temporary, format=image_format, **save_options)

        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise OSError("O arquivo de imagem temporário ficou vazio.")
        if os.name != "nt":
            os.chmod(temporary, file_mode)
        os.replace(temporary, output)
        return output
    finally:
        if final_image is not None:
            final_image.close()
        if image is not None and image is not final_image:
            image.close()
        temporary.unlink(missing_ok=True)


def pdf_page_count(input_path: str | Path, *, password: str | None = None) -> int:
    """Return a PDF's page count after validating any required password."""
    source = Path(input_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {source}")
    if source.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de origem precisa ser PDF.")
    with source.open("rb") as stream:
        reader = _open_reader(source, stream, password=password)
        return len(reader.pages)


def reorder_pdf_pages(
    input_path: str | Path,
    page_order: Sequence[int],
    output_path: str | Path,
    *,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Save every page in a user-supplied 1-based order, without dropping or duplicating pages."""
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            count = len(reader.pages)
            if len(page_order) != count or set(page_order) != set(range(1, count + 1)):
                raise ValueError(
                    f"A ordem deve conter cada página uma única vez, de 1 a {count}."
                )
            writer = PdfWriter()
            writer.append(
                reader,
                pages=[page_number - 1 for page_number in page_order],
                import_outline=True,
            )
            _copy_metadata(reader, writer)
            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def optimize_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    mode: str = "lossless",
    quality: int = 82,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Optimize PDF streams and optionally recompress supported raster images as JPEG.

    lossless mode only compresses streams and deduplicates objects. balanced mode also
    recompresses opaque raster images using the requested JPEG quality; images with
    alpha/transparency and inline images are intentionally left unchanged.
    """
    if mode not in {"lossless", "balanced"}:
        raise ValueError("Escolha otimização sem perdas ou equilibrada.")
    if not 50 <= quality <= 95:
        raise ValueError("A qualidade JPEG precisa ficar entre 50 e 95.")
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            writer = PdfWriter()
            writer.append(reader, import_outline=True)
            _copy_metadata(reader, writer)
            for page in writer.pages:
                page.compress_content_streams(level=9)
                if mode != "balanced":
                    continue
                for image_file in list(page.images):
                    if image_file.is_inline or not image_file.is_displayed:
                        continue
                    image = image_file.image
                    if image is None:
                        continue
                    # Retain transparency/soft-mask graphics to avoid changing their appearance.
                    if image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info:
                        continue
                    converted: Image.Image | None = None
                    try:
                        converted = image.convert("RGB")
                        image_file.replace(
                            converted,
                            format="JPEG",
                            quality=quality,
                            optimize=True,
                        )
                    finally:
                        if converted is not None:
                            converted.close()
            writer.compress_identical_objects(
                remove_identicals=True,
                remove_orphans=True,
            )
            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def stamp_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    watermark_text: str | None = None,
    page_numbering: bool = False,
    watermark_position: str = "diagonal",
    page_number_position: str = "bottom-right",
    font_size: int = 34,
    opacity: float = 0.22,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Overlay a text watermark and/or page numbers without rasterizing the source pages."""
    watermark = (watermark_text or "").strip()
    if not watermark and not page_numbering:
        raise ValueError("Informe o texto da marca d'água ou ative a numeração de páginas.")
    if not 8 <= font_size <= 120:
        raise ValueError("O tamanho da fonte precisa ficar entre 8 e 120.")
    if not 0.05 <= opacity <= 1:
        raise ValueError("A opacidade precisa ficar entre 0,05 e 1.")
    if watermark_position not in {"diagonal", "center", "bottom-center"}:
        raise ValueError("Posição de marca d'água inválida.")
    if page_number_position not in {"bottom-right", "bottom-center"}:
        raise ValueError("Posição de numeração inválida.")

    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            writer = PdfWriter()
            writer.append(reader, import_outline=True)
            _copy_metadata(reader, writer)
            total_pages = len(writer.pages)

            for index, page in enumerate(writer.pages, start=1):
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                overlay_stream = BytesIO()
                overlay_canvas = canvas.Canvas(
                    overlay_stream,
                    pagesize=(width, height),
                    pageCompression=1,
                )
                overlay_canvas.saveState()
                overlay_canvas.setFillColorRGB(0.38, 0.42, 0.49)
                overlay_canvas.setFillAlpha(opacity)

                if watermark:
                    overlay_canvas.setFont("Helvetica-Bold", font_size)
                    if watermark_position == "diagonal":
                        overlay_canvas.translate(width / 2, height / 2)
                        overlay_canvas.rotate(35)
                        overlay_canvas.drawCentredString(0, 0, watermark)
                    elif watermark_position == "center":
                        overlay_canvas.drawCentredString(width / 2, height / 2, watermark)
                    else:
                        overlay_canvas.drawCentredString(width / 2, 32, watermark)

                if page_numbering:
                    overlay_canvas.setFillAlpha(1)
                    overlay_canvas.setFont("Helvetica", max(9, min(16, font_size // 2)))
                    page_label = f"{index} / {total_pages}"
                    if page_number_position == "bottom-center":
                        overlay_canvas.drawCentredString(width / 2, 18, page_label)
                    else:
                        overlay_canvas.drawRightString(width - 28, 18, page_label)

                overlay_canvas.restoreState()
                overlay_canvas.showPage()
                overlay_canvas.save()
                overlay_stream.seek(0)
                overlay_reader = PdfReader(overlay_stream, strict=False)
                page.merge_page(overlay_reader.pages[0], over=True, expand=False)
                overlay_stream.close()

            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output
