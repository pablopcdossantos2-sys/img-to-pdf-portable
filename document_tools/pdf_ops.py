"""Local PDF and image operations used by the desktop interface."""

from __future__ import annotations

import math
import os
import re
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfbase.pdfmetrics import stringWidth
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
        if len(pieces) == 1 and pieces[0].isdecimal():
            start = end = int(pieces[0])
        elif (
            len(pieces) == 2
            and pieces[0].isdecimal()
            and (pieces[1].isdecimal() or pieces[1] == "")
        ):
            start = int(pieces[0])
            end = int(pieces[1]) if pieces[1] else page_count
        else:
            raise ValueError(f"Intervalo de páginas inválido: '{segment}'.")
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"O intervalo '{segment}' precisa estar entre 1 e {page_count}.")

        for page_number in range(start, end + 1):
            if page_number in seen and not allow_duplicates:
                raise ValueError(f"A página {page_number} foi informada mais de uma vez.")
            seen.add(page_number)
            indexes.append(page_number - 1)

    return indexes


def _same_existing_file(first: Path, second: Path) -> bool:
    """Detect aliases of the same existing file, including case-insensitive volumes."""
    if first == second:
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False


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
    if any(_same_existing_file(output, source) for source in sources):
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
            try:
                os.link(temporary, output)
            except FileExistsError:
                raise
            except OSError:
                # Hard links are unavailable on some removable/network filesystems.
                # O_EXCL keeps the no-overwrite guarantee when falling back to a copy.
                descriptor = os.open(
                    output,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    file_mode,
                )
                try:
                    with os.fdopen(descriptor, "wb") as destination_stream:
                        with temporary.open("rb") as source_stream:
                            shutil.copyfileobj(source_stream, destination_stream)
                        destination_stream.flush()
                        os.fsync(destination_stream.fileno())
                    if os.name != "nt":
                        os.chmod(output, file_mode)
                except Exception:
                    output.unlink(missing_ok=True)
                    raise
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
        except Exception as error:
            raise ValueError(
                "Não foi possível verificar se o PDF exige senha. O arquivo pode estar danificado."
            ) from error


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


def _normalise_high_bit_depth(image: Image.Image) -> Image.Image:
    """Convert high-bit-depth grayscale data to 8-bit without saturating it to white."""
    if image.mode.startswith("I;16"):
        grayscale = image.convert("I")
        try:
            return grayscale.point(lambda value: value / 257).convert("L")
        finally:
            grayscale.close()
    if image.mode in {"I", "F"}:
        low, high = image.getextrema()
        if not (float(low) == float(low) and float(high) == float(high)):
            return Image.new("L", image.size, 0)
        if high > low:
            # Normalize by this image's dynamic range. This preserves ordinary
            # 0..255 values in Pillow's "I" mode instead of crushing them to black.
            scale = 255.0 / float(high - low)
            return image.point(lambda value: (value - low) * scale).convert("L")
        if image.mode == "I" and 0 <= low <= 65535:
            return Image.new("L", image.size, round(float(low) / 257))
        return Image.new("L", image.size, 0)
    return image


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Composite transparency over white and return an independent RGB image."""
    normalized = _normalise_high_bit_depth(image)
    rgba = normalized.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, "white")
    try:
        flattened.paste(rgba, (0, 0), rgba.getchannel("A"))
    except Exception:
        flattened.close()
        raise
    finally:
        rgba.close()
        if normalized is not image:
            normalized.close()
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
    if any(_same_existing_file(output, source) for source in sources):
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
    page_ranges: Sequence[str | None] | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Join PDFs in order, optionally selecting a page range and password for every input."""
    if len(pdf_paths) < 2:
        raise ValueError("Selecione pelo menos dois PDFs para unir.")
    if passwords is not None and len(passwords) != len(pdf_paths):
        raise ValueError("Informe uma senha por PDF ou deixe a senha como None.")
    if page_ranges is not None and len(page_ranges) != len(pdf_paths):
        raise ValueError("Informe um intervalo de páginas por PDF ou deixe None para usar todas.")
    _validate_file_mode(file_mode)
    sources, output = _normalise_pdf_paths(pdf_paths, output_path)

    def write(temporary: Path) -> None:
        writer = PdfWriter()
        for index, source in enumerate(sources):
            password = passwords[index] if passwords is not None else None
            with source.open("rb") as stream:
                reader = _open_reader(source, stream, password=password)
                selected_ranges = page_ranges[index] if page_ranges is not None else None
                if selected_ranges and selected_ranges.strip():
                    indexes = parse_page_ranges(selected_ranges, len(reader.pages))
                    writer.append(reader, pages=indexes, import_outline=True)
                else:
                    writer.append(reader, import_outline=True)
                if index == 0:
                    _copy_metadata(reader, writer)
        writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def mix_pdfs(
    first_path: str | Path,
    second_path: str | Path,
    output_path: str | Path,
    *,
    first_page_ranges: str | None = None,
    second_page_ranges: str | None = None,
    reverse_second: bool = False,
    first_pace: int = 1,
    second_pace: int = 1,
    first_password: str | None = None,
    second_password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Interleave pages from two PDFs in blocks, optionally reversing the second selection."""
    if first_pace < 1 or second_pace < 1:
        raise ValueError("O número de páginas por bloco deve ser positivo.")
    _validate_file_mode(file_mode)
    sources, output = _normalise_pdf_paths([first_path, second_path], output_path)
    first, second = sources

    def write(temporary: Path) -> None:
        with first.open("rb") as first_stream, second.open("rb") as second_stream:
            first_reader = _open_reader(first, first_stream, password=first_password)
            second_reader = _open_reader(second, second_stream, password=second_password)
            first_indexes = (
                list(range(len(first_reader.pages)))
                if not first_page_ranges or not first_page_ranges.strip()
                else parse_page_ranges(first_page_ranges, len(first_reader.pages))
            )
            second_indexes = (
                list(range(len(second_reader.pages)))
                if not second_page_ranges or not second_page_ranges.strip()
                else parse_page_ranges(second_page_ranges, len(second_reader.pages))
            )
            if reverse_second:
                second_indexes.reverse()

            writer = PdfWriter()
            _copy_metadata(first_reader, writer)
            first_pos = 0
            second_pos = 0
            while first_pos < len(first_indexes) or second_pos < len(second_indexes):
                for _ in range(first_pace):
                    if first_pos >= len(first_indexes):
                        break
                    writer.add_page(first_reader.pages[first_indexes[first_pos]])
                    first_pos += 1
                for _ in range(second_pace):
                    if second_pos >= len(second_indexes):
                        break
                    writer.add_page(second_reader.pages[second_indexes[second_pos]])
                    second_pos += 1
            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def insert_pages_repeatedly(
    target_path: str | Path,
    insert_path: str | Path,
    output_path: str | Path,
    *,
    every_n_pages: int = 1,
    insert_page_ranges: str | None = None,
    target_password: str | None = None,
    insert_password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Insert selected pages from one PDF after every N pages of another PDF."""
    if every_n_pages < 1:
        raise ValueError("O intervalo entre inserções deve ser positivo.")
    _validate_file_mode(file_mode)
    sources, output = _normalise_pdf_paths([target_path, insert_path], output_path)
    target, insertion = sources

    def write(temporary: Path) -> None:
        with target.open("rb") as target_stream, insertion.open("rb") as insert_stream:
            target_reader = _open_reader(target, target_stream, password=target_password)
            insert_reader = _open_reader(insertion, insert_stream, password=insert_password)
            if every_n_pages > len(target_reader.pages):
                raise ValueError("O intervalo entre inserções não pode exceder o número de páginas do PDF de destino.")
            insert_indexes = (
                list(range(len(insert_reader.pages)))
                if not insert_page_ranges or not insert_page_ranges.strip()
                else parse_page_ranges(insert_page_ranges, len(insert_reader.pages))
            )

            writer = PdfWriter()
            _copy_metadata(target_reader, writer)
            for page_index, page in enumerate(target_reader.pages, start=1):
                writer.add_page(page)
                if page_index % every_n_pages == 0:
                    for insert_index in insert_indexes:
                        writer.add_page(insert_reader.pages[insert_index])
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


def delete_pages(
    input_path: str | Path,
    page_ranges: str,
    output_path: str | Path,
    *,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Remove selected pages while retaining the remaining pages and compatible structures."""
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)

    def write(temporary: Path) -> None:
        with source.open("rb") as stream:
            reader = _open_reader(source, stream, password=password)
            remove_indexes = set(parse_page_ranges(page_ranges, len(reader.pages)))
            keep_indexes = [
                index for index in range(len(reader.pages))
                if index not in remove_indexes
            ]
            if not keep_indexes:
                raise ValueError("A exclusão precisa manter pelo menos uma página no PDF.")
            writer = PdfWriter()
            writer.append(reader, pages=keep_indexes, import_outline=True)
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
    mode: str = "each_page",
    pages_per_file: int = 1,
    split_after_pages: str | None = None,
    target_size_mb: float = 10.0,
    bookmark_level: int = 1,
    bookmark_pattern: str | None = None,
    password: str | None = None,
    file_mode: int = 0o600,
) -> list[Path]:
    """Split a PDF by page, page groups, boundaries, estimated size or bookmark level."""
    valid_modes = {
        "each_page", "every_n_pages", "after_pages", "after_even_pages",
        "after_odd_pages", "by_size", "by_bookmarks",
    }
    if mode not in valid_modes:
        raise ValueError("Modo de divisão inválido.")
    if mode == "every_n_pages" and pages_per_file < 1:
        raise ValueError("O número de páginas por arquivo deve ser positivo.")
    if mode == "by_size" and target_size_mb <= 0:
        raise ValueError("O tamanho alvo precisa ser maior que zero.")
    if mode == "by_bookmarks" and bookmark_level < 1:
        raise ValueError("O nível do marcador precisa ser um inteiro positivo.")

    pattern = None
    if mode == "by_bookmarks" and bookmark_pattern and bookmark_pattern.strip():
        try:
            pattern = re.compile(bookmark_pattern, re.IGNORECASE)
        except re.error as error:
            raise ValueError("A expressão regular para filtrar marcadores é inválida.") from error

    source = Path(input_path).expanduser().resolve()
    directory = Path(output_directory).expanduser().resolve()
    _validate_file_mode(file_mode)
    if not source.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {source}")
    if source.suffix.lower() != ".pdf":
        raise ValueError("O arquivo de origem precisa ser PDF.")
    created: list[Path] = []
    with source.open("rb") as stream:
        reader = _open_reader(source, stream, password=password)
        page_count = len(reader.pages)
        groups: list[list[int]] = []
        group_titles: list[str | None] = []

        if mode == "each_page":
            groups = [[i] for i in range(page_count)]
        elif mode == "every_n_pages":
            groups = [
                list(range(start, min(start + pages_per_file, page_count)))
                for start in range(0, page_count, pages_per_file)
            ]
        elif mode in {"after_pages", "after_even_pages", "after_odd_pages"}:
            if mode == "after_pages":
                if not split_after_pages or not split_after_pages.strip():
                    raise ValueError(
                        "Informe páginas após as quais dividir, por exemplo: 2, 5, 8."
                    )
                # Page-range parser is 0-based; the end of a split is 1-based.
                boundaries = sorted({
                    index + 1 for index in parse_page_ranges(split_after_pages, page_count)
                })
            elif mode == "after_even_pages":
                boundaries = list(range(2, page_count + 1, 2))
            else:
                boundaries = list(range(1, page_count + 1, 2))
            start = 0
            for end in boundaries:
                if end > start:
                    groups.append(list(range(start, end)))
                    start = end
            if start < page_count:
                groups.append(list(range(start, page_count)))
        elif mode == "by_size":
            # This is deliberately an estimate: serialized output size also depends on
            # shared resources, compression, metadata and page-tree overhead.
            target_bytes = max(1, int(target_size_mb * 1024 * 1024))
            estimates: list[int] = []
            for page in reader.pages:
                estimate = 0
                try:
                    contents = page.get_contents()
                    if contents is not None:
                        estimate += len(contents.get_data())
                except Exception:
                    pass
                try:
                    estimate += sum(len(image.data) for image in page.images if not image.is_inline)
                except Exception:
                    pass
                estimates.append(max(1, estimate))
            current_group: list[int] = []
            current_size = 0
            for index, estimate in enumerate(estimates):
                if current_group and current_size + estimate > target_bytes:
                    groups.append(current_group)
                    current_group, current_size = [], 0
                current_group.append(index)
                current_size += estimate
            if current_group:
                groups.append(current_group)
        else:  # by_bookmarks
            bookmarks: list[tuple[int, str]] = []

            def collect_bookmarks(entries, level: int = 1) -> None:
                for entry in entries:
                    if isinstance(entry, list):
                        collect_bookmarks(entry, level + 1)
                        continue
                    if level != bookmark_level:
                        continue
                    title = str(getattr(entry, "title", "") or "").strip()
                    if pattern is not None and not pattern.search(title):
                        continue
                    try:
                        page_index = reader.get_destination_page_number(entry)
                    except Exception:
                        continue
                    if 0 <= page_index < page_count:
                        bookmarks.append((page_index, title or "Marcador"))

            collect_bookmarks(reader.outline)
            if not bookmarks:
                raise ValueError(
                    "O PDF não contém marcadores no nível solicitado (ou nenhum corresponde ao filtro)."
                )
            bookmarks.sort(key=lambda item: item[0])
            unique_bookmarks: list[tuple[int, str]] = []
            used_pages: set[int] = set()
            for page_index, title in bookmarks:
                if page_index not in used_pages:
                    used_pages.add(page_index)
                    unique_bookmarks.append((page_index, title))
            if unique_bookmarks[0][0] > 0:
                unique_bookmarks.insert(0, (0, "Início"))
            for index, (start, title) in enumerate(unique_bookmarks):
                end = unique_bookmarks[index + 1][0] if index + 1 < len(unique_bookmarks) else page_count
                if start < end:
                    groups.append(list(range(start, end)))
                    group_titles.append(title)

        if not groups:
            raise ValueError("Não foi possível gerar divisões a partir das opções informadas.")

        width = max(3, len(str(len(groups))))
        outputs: list[Path] = []
        for index, page_indexes in enumerate(groups, start=1):
            if mode == "each_page":
                filename = f"{source.stem}-pagina-{page_indexes[0] + 1:0{width}d}.pdf"
            elif mode == "by_bookmarks":
                title = group_titles[index - 1] if index - 1 < len(group_titles) else "Marcador"
                safe_title = re.sub(r"[^\w.-]+", "-", title, flags=re.UNICODE).strip(" .-_")
                filename = f"{source.stem}-{index:0{width}d}-{(safe_title or 'marcador')[:60]}.pdf"
            else:
                filename = f"{source.stem}-parte-{index:0{width}d}.pdf"
            outputs.append(directory / filename)

        # Create the destination only after all input/password/options validation succeeds.
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise FileNotFoundError("Não foi possível criar a pasta de destino.")
        conflicts = [path.name for path in outputs if path.exists()]
        if conflicts:
            raise FileExistsError(
                f"A pasta já contém '{conflicts[0]}'. Escolha outra pasta ou remova os arquivos conflitantes."
            )
        try:
            for indexes, target in zip(groups, outputs):
                writer = PdfWriter()
                writer.append(reader, pages=indexes, import_outline=True)
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
    normalized = _normalise_high_bit_depth(image)
    if normalized is not image:
        try:
            return _format_image_for_output(normalized, image_format)
        finally:
            normalized.close()
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
    if _same_existing_file(source, output):
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
            normalized = _normalise_high_bit_depth(image)
            if normalized is not image:
                if image is not opened:
                    image.close()
                image = normalized
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
            elif image_format == "TIFF":
                # Lossless compression reduces file size without changing image pixels.
                save_options["compression"] = "tiff_lzw"

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
            # pypdf's documented image replacement flow uses a writer cloned from the reader.
            writer = PdfWriter(clone_from=reader)
            for page in writer.pages:
                page.compress_content_streams(level=9)
                if mode != "balanced":
                    continue
                try:
                    images = list(page.images)
                except Exception:
                    # Image extraction is optional for optimization; a broken or unusual
                    # XObject must not make the entire document fail.
                    continue
                for image_file in images:
                    try:
                        if image_file.is_inline or not image_file.is_displayed:
                            continue
                        image = image_file.image
                        if image is None:
                            continue
                        # Do not rasterize alpha images; pypdf preserves supported source modes.
                        if image.mode in {"RGBA", "LA", "PA"} or "transparency" in image.info:
                            continue
                        before_size = len(image_file.data)
                        replacement = BytesIO()
                        image.save(replacement, format="JPEG", quality=quality, optimize=True)
                        replacement_size = replacement.tell()
                        replacement.close()
                        if replacement_size >= before_size:
                            continue
                        image_file.replace(image, quality=quality, optimize=True)
                    except Exception:
                        # Keep the original resource when pypdf/Pillow cannot process it.
                        continue
            writer.compress_identical_objects(
                remove_duplicates=True,
                remove_unreferenced=True,
            )
            writer.write(temporary)
        # Optimization is optional: never replace a document with a larger one.
        if temporary.stat().st_size > source.stat().st_size:
            shutil.copyfile(source, temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def stamp_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    watermark_text: str | None = None,
    page_numbering: bool = False,
    page_ranges: str | None = None,
    watermark_position: str = "diagonal",
    page_number_position: str = "bottom-right",
    font_size: int = 34,
    opacity: float = 0.22,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Overlay a text watermark and/or page numbers without rasterizing the source pages."""
    watermark = (watermark_text or "").strip()
    if watermark:
        try:
            watermark.encode("cp1252")
        except UnicodeEncodeError as error:
            raise ValueError(
                "A marca d'água contém caracteres não suportados pela fonte padrão. Use caracteres latinos e símbolos compatíveis."
            ) from error
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
            selected_indexes = (
                set(range(total_pages))
                if page_ranges is None or not page_ranges.strip()
                else set(parse_page_ranges(page_ranges, total_pages))
            )

            for index, page in enumerate(writer.pages, start=1):
                if index - 1 not in selected_indexes:
                    continue
                # Resolve /Rotate into the content before laying out the overlay.
                # This makes text upright and lets the visible crop box determine placement.
                if int(page.rotation or 0) % 360:
                    page.transfer_rotation_to_content()
                visible_box = page.cropbox
                width = float(visible_box.width)
                height = float(visible_box.height)
                origin_x = float(visible_box.left)
                origin_y = float(visible_box.bottom)
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
                    font_name = "Helvetica-Bold"
                    margin = min(18.0, max(3.0, width * 0.04), max(3.0, height * 0.04))
                    if watermark_position == "diagonal":
                        angle = 35
                        max_text_width = min(
                            max(1.0, (width - 2 * margin) / abs(math.cos(math.radians(angle)))),
                            max(1.0, (height - 2 * margin) / abs(math.sin(math.radians(angle)))),
                        )
                    else:
                        max_text_width = max(1.0, width - 2 * margin)
                    requested_width = stringWidth(watermark, font_name, font_size)
                    fitted_size = float(font_size)
                    if requested_width > max_text_width:
                        fitted_size = font_size * max_text_width / requested_width
                    if fitted_size < 8:
                        raise ValueError(
                            "O texto da marca d'água é longo demais para caber na página. Reduza o texto ou use uma posição central."
                        )
                    overlay_canvas.setFont(font_name, fitted_size)
                    if watermark_position == "diagonal":
                        overlay_canvas.translate(width / 2, height / 2)
                        overlay_canvas.rotate(35)
                        overlay_canvas.drawCentredString(0, 0, watermark)
                    elif watermark_position == "center":
                        overlay_canvas.drawCentredString(width / 2, height / 2, watermark)
                    else:
                        overlay_canvas.drawCentredString(width / 2, min(32.0, max(8.0, height * 0.04)), watermark)

                if page_numbering:
                    overlay_canvas.setFillAlpha(1)
                    page_label = f"{index} / {total_pages}"
                    label_font_size = float(max(9, min(16, font_size // 2)))
                    label_width = stringWidth(page_label, "Helvetica", label_font_size)
                    available_label_width = max(1.0, width - 2 * min(28.0, width * 0.08))
                    if label_width > available_label_width:
                        label_font_size *= available_label_width / label_width
                    overlay_canvas.setFont("Helvetica", label_font_size)
                    bottom_margin = min(18.0, max(4.0, height * 0.04))
                    if page_number_position == "bottom-center":
                        overlay_canvas.drawCentredString(width / 2, bottom_margin, page_label)
                    else:
                        overlay_canvas.drawRightString(width - min(28.0, width * 0.08), bottom_margin, page_label)

                overlay_canvas.restoreState()
                overlay_canvas.showPage()
                overlay_canvas.save()
                overlay_stream.seek(0)
                overlay_reader = PdfReader(overlay_stream, strict=False)
                page.merge_transformed_page(
                    overlay_reader.pages[0],
                    Transformation().translate(tx=origin_x, ty=origin_y),
                    over=True,
                    expand=False,
                )
                overlay_stream.close()

            writer.write(temporary)

    _atomic_pdf_save(output, write, file_mode=file_mode)
    return output


def process_pdf_pipeline(
    input_path: str | Path,
    output_path: str | Path,
    *,
    rotate_angle: int | None = None,
    rotate_ranges: str | None = None,
    watermark_text: str | None = None,
    page_numbering: bool = False,
    stamp_ranges: str | None = None,
    optimize_mode: str | None = None,
    quality: int = 82,
    password: str | None = None,
    file_mode: int = 0o600,
) -> Path:
    """Run selected PDF transformations in a fixed order with atomic final output.

    The sequence is rotation, watermark/page numbering, then optimization. Intermediate
    documents are temporary files in the destination folder and are removed automatically.
    The original source is never modified, and the final destination is only replaced after
    the last selected operation has completed successfully.
    """
    sources, output = _normalise_pdf_paths([input_path], output_path)
    source = sources[0]
    _validate_file_mode(file_mode)
    if rotate_angle is not None and rotate_angle not in (90, 180, 270):
        raise ValueError("Escolha uma rotação de 90, 180 ou 270 graus.")
    if optimize_mode not in (None, "lossless", "balanced"):
        raise ValueError("Escolha otimização sem perdas ou equilibrada.")

    operations: list[Callable[[Path, Path], Path]] = []
    if rotate_angle is not None:
        operations.append(
            lambda current, target: rotate_pdf(
                current, target, rotate_angle, rotate_ranges,
                password=password, file_mode=file_mode,
            )
        )
    if (watermark_text or "").strip() or page_numbering:
        operations.append(
            lambda current, target: stamp_pdf(
                current, target,
                watermark_text=watermark_text,
                page_numbering=page_numbering,
                page_ranges=stamp_ranges,
                password=password,
                file_mode=file_mode,
            )
        )
    if optimize_mode is not None:
        operations.append(
            lambda current, target: optimize_pdf(
                current, target,
                mode=optimize_mode,
                quality=quality,
                password=password,
                file_mode=file_mode,
            )
        )
    if not operations:
        raise ValueError("Selecione pelo menos uma etapa para executar o fluxo em lote.")

    with tempfile.TemporaryDirectory(prefix="pdf-hub-pipeline-", dir=str(output.parent)) as temp_dir:
        current = source
        for index, operation in enumerate(operations):
            is_last = index == len(operations) - 1
            target = output if is_last else Path(temp_dir) / f"stage-{index + 1}.pdf"
            operation(current, target)
            current = target

    return output
