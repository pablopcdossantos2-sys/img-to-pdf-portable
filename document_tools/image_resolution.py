"""Estimate a suitable raster resolution for images placed on A4 pages."""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from PIL import Image

MIN_DPI = 72
MAX_DPI = 600
MM_PER_INCH = 25.4
_EXIF_ORIENTATION = 0x0112
_SWAPPED_ORIENTATIONS = {5, 6, 7, 8}


@lru_cache(maxsize=2048)
def _cached_oriented_size(path_text: str, mtime_ns: int, file_size: int) -> tuple[int, int]:
    """Cache dimensions and orientation by path and file metadata."""
    del mtime_ns, file_size
    with Image.open(path_text) as opened:
        width, height = opened.size
        try:
            orientation = opened.getexif().get(_EXIF_ORIENTATION)
        except (OSError, ValueError, SyntaxError, EOFError, Image.DecompressionBombError):
            orientation = None
        return (height, width) if orientation in _SWAPPED_ORIENTATIONS else (width, height)
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0


def recommend_dpi_from_images(
    image_paths: Iterable[str | Path],
    *,
    margin_mm: float = 0.0,
) -> int | None:
    """Recommend DPI from the lowest source-image pixel density when fitted to A4.

    The calculation matches the orientation and fit-to-page rules used by the PDF
    generator. Images with unreadable dimensions are skipped. The returned value is
    clamped to the GUI's supported DPI range and never changes source files.
    """
    if not 0 <= margin_mm <= 40:
        raise ValueError("A margem precisa ficar entre 0 e 40 mm.")

    inset = margin_mm / MM_PER_INCH
    densities: list[float] = []
    for raw_path in image_paths:
        path = Path(raw_path).expanduser()
        try:
            stat = path.stat()
            width, height = _cached_oriented_size(
                str(path.resolve()), stat.st_mtime_ns, stat.st_size
            )
        except (OSError, ValueError, EOFError, SyntaxError, Image.DecompressionBombError):
            continue

        if width < 1 or height < 1:
            continue

        if width > height:
            page_width_mm, page_height_mm = A4_HEIGHT_MM, A4_WIDTH_MM
        else:
            page_width_mm, page_height_mm = A4_WIDTH_MM, A4_HEIGHT_MM

        available_width = page_width_mm / MM_PER_INCH - 2 * inset
        available_height = page_height_mm / MM_PER_INCH - 2 * inset
        if available_width <= 0 or available_height <= 0:
            continue

        aspect_ratio = width / height
        fitted_width_inches = min(available_width, aspect_ratio * available_height)
        if fitted_width_inches > 0:
            densities.append(width / fitted_width_inches)

    if not densities:
        return None
    estimate = round(min(densities))
    return max(MIN_DPI, min(MAX_DPI, estimate))
