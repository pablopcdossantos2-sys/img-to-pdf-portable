"""Local PDF and image operations used by the desktop interface."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SUPPORTED_OUTPUT_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}


def parse_page_ranges(specification: str, page_count: int) -> list[int]:
    """Convert a human-readable page list to zero-based indexes in the requested order."""
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
            if page_number in seen:
                raise ValueError(f"A página {page_number} foi informada mais de uma vez.")
            seen.add(page_number)
            indexes.append(page_number - 1)

    return indexes


def _normalise_pdf_paths(source_paths: Sequence[str | Path], output_path: str | Path) -> tuple[list[Path], Path]:
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


def _atomic_pdf_save(output: Path, write_document: Callable[[Path], None]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".document-tools-", suffix=".pdf", dir=str(output.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        write_document(temporary)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise OSError("O arquivo PDF temporário ficou vazio.")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def _open_reader(path: Path, stream):
    reader = PdfReader(stream, strict=False)
    if reader.is_encrypted:
        raise ValueError(
            f"O PDF '{path.name}' está protegido por senha. Remova a proteção antes de continuar."
        )
    if len(reader.pages) < 1:
        raise ValueError(f"O PDF '{path.name}' não contém páginas.")
    return reader


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


def images_to_pdf(
    image_paths: Sequence[str | Path],
    output_path: str | Path,
    *,
    dpi: int = 150,
    margin_mm: float = 10,
) -> Path:
    """Create an A4 PDF, one image per page, automatically orienting each page."""
    if not image_paths:
        raise ValueError("Adicione pelo menos uma imagem.")
    if dpi < 72 or dpi > 600:
        raise ValueError("A resolução precisa ficar entre 72 e 600 DPI.")
    if margin_mm < 0 or margin_mm > 40:
        raise ValueError("A margem precisa ficar entre 0 e 40 mm.")

    sources = [Path(path).expanduser().resolve() for path in image_paths]
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de saída precisa ter a extensão .pdf.")
    if not output.parent.is_dir():
        raise FileNotFoundError("A pasta de destino não existe.")
    if output in sources:
        raise ValueError("O arquivo de saída não pode substituir uma imagem de origem.")

    pages: list[Image.Image] = []
    try:
        margin_pixels = round(margin_mm * dpi / 25.4)
        for source in sources:
            if not source.is_file():
                raise FileNotFoundError(f"Imagem não encontrada: {source}")
            if source.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                raise ValueError(f"Formato de imagem não suportado: {source.name}")

            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
            portrait_width = round(210 / 25.4 * dpi)
            portrait_height = round(297 / 25.4 * dpi)
            if image.width > image.height:
                page_width, page_height = portrait_height, portrait_width
            else:
                page_width, page_height = portrait_width, portrait_height

            available = (
                page_width - (2 * margin_pixels),
                page_height - (2 * margin_pixels),
            )
            image.thumbnail(available, Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (page_width, page_height), "white")
            canvas.paste(
                image,
                ((page_width - image.width) // 2, (page_height - image.height) // 2),
            )
            pages.append(canvas)

        def write(temporary: Path) -> None:
            pages[0].save(
                temporary,
                format="PDF",
                resolution=dpi,
                save_all=True,
                append_images=pages[1:],
            )

        _atomic_pdf_save(output, write)
        return output
    finally:
        for page in pages:
            page.close()


def merge_pdfs(pdf_paths: Sequence[str | Path], output_path: str | Path) -> Path:
    """Join multiple PDF files in the supplied order."""
    if len(pdf_paths) < 2:
        raise ValueError("Selecione pelo menos dois PDFs para unir.")
    sources, output = _normalise_pdf_paths(pdf_paths, output_path)

    def write(temporary: Path) -> None:
        writer = PdfWriter()
        streams = []
        try:
            for source in sources:
                stream = source.open("rb")
                streams.append(stream)
                reader = _open_reader(source, stream)
                for page in reader.pages:
                    writer.add_page(page)
            writer.write(temporary)
        finally:
            for stream in streams:
                stream.close()

    _atomic_pdf_save(output, write)
    return output


def extract_pages(
    input_path: str | Path,
    page_ranges: str,
    output_path: str | Path,
) -> Path:
    """Save the requested pages in the order supplied by the user."""
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream)
            indexes = parse_page_ranges(page_ranges, len(reader.pages))
            writer = PdfWriter()
            _copy_metadata(reader, writer)
            for index in indexes:
                writer.add_page(reader.pages[index])
            writer.write(temporary)

    _atomic_pdf_save(output, write)
    return output


def rotate_pdf(
    input_path: str | Path,
    output_path: str | Path,
    angle: int,
    page_ranges: str | None = None,
) -> Path:
    """Rotate every page or the selected pages clockwise by 90, 180, or 270 degrees."""
    if angle not in (90, 180, 270):
        raise ValueError("Escolha uma rotação de 90, 180 ou 270 graus.")
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream)
            indexes = (
                set(range(len(reader.pages)))
                if page_ranges is None or not page_ranges.strip()
                else set(parse_page_ranges(page_ranges, len(reader.pages)))
            )
            writer = PdfWriter()
            _copy_metadata(reader, writer)
            for index, page in enumerate(reader.pages):
                copied = writer.add_page(page)
                if index in indexes:
                    copied.rotate(angle)
            writer.write(temporary)

    _atomic_pdf_save(output, write)
    return output


def split_pdf(input_path: str | Path, output_directory: str | Path) -> list[Path]:
    """Split a PDF into one output PDF per page without overwriting existing files."""
    source = Path(input_path).expanduser().resolve()
    directory = Path(output_directory).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {source}")
    if not directory.is_dir():
        raise FileNotFoundError("A pasta de destino não existe.")
    if source.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de origem precisa ser PDF.")

    outputs: list[Path] = []
    created: list[Path] = []
    with source.open("rb") as stream:
        reader = _open_reader(source, stream)
        stem = source.stem
        outputs = [
            directory / f"{stem}-pagina-{index + 1:03d}.pdf"
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
                writer.add_page(reader.pages[index])
                _copy_metadata(reader, writer)
                _atomic_pdf_save(target, lambda temporary, w=writer: w.write(temporary))
                created.append(target)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise

    return outputs


def convert_image(
    input_path: str | Path,
    output_path: str | Path,
    output_format: str,
    *,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int = 90,
) -> Path:
    """Convert or resize a single image and save it without altering its source."""
    source = Path(input_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    image_format = output_format.upper().strip()
    if image_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Formato de saída não suportado: {output_format}")
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

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".document-tools-", suffix=output.suffix or ".tmp", dir=str(output.parent)
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.load()
            if max_width or max_height:
                bounds = (
                    max_width or image.width,
                    max_height or image.height,
                )
                image.thumbnail(bounds, Image.Resampling.LANCZOS)

            save_options: dict[str, object] = {}
            if image_format == "JPEG":
                if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                    rgba = image.convert("RGBA")
                    background = Image.new("RGB", rgba.size, "white")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    rgba.close()
                    image = background
                else:
                    image = image.convert("RGB")
                save_options = {"quality": quality, "optimize": True}
            elif image_format == "WEBP":
                save_options = {"quality": quality, "method": 6}
            elif image_format == "BMP":
                image = image.convert("RGB") if image.mode not in ("RGB", "L") else image
            image.save(temporary, format=image_format, **save_options)

        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise OSError("O arquivo de imagem temporário ficou vazio.")
        os.replace(temporary, output)
        return output
    finally:
        temporary.unlink(missing_ok=True)
