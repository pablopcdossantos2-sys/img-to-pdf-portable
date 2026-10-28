from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from document_tools.image_resolution import recommend_dpi_from_images


def create_image(path: Path, size: tuple[int, int]) -> Path:
    with Image.new("RGB", size, "white") as image:
        image.save(path)
    return path


def test_recommend_dpi_recovers_300_for_a4_sized_pixel_dimensions(tmp_path: Path) -> None:
    image_path = create_image(tmp_path / "a4-300dpi.png", (2480, 3508))
    assert recommend_dpi_from_images([image_path], margin_mm=0) == 300


def test_mixed_image_sizes_use_the_lowest_native_fit_density(tmp_path: Path) -> None:
    high = create_image(tmp_path / "high.png", (2480, 3508))
    lower = create_image(tmp_path / "lower.png", (1240, 1754))
    assert recommend_dpi_from_images([high, lower], margin_mm=0) == 150


def test_margin_changes_recommended_density_and_values_are_clamped(tmp_path: Path) -> None:
    image_path = create_image(tmp_path / "image.png", (2480, 3508))
    no_margin = recommend_dpi_from_images([image_path], margin_mm=0)
    margin = recommend_dpi_from_images([image_path], margin_mm=10)
    oversized = create_image(tmp_path / "oversized.png", (5000, 7000))
    tiny = create_image(tmp_path / "tiny.png", (80, 80))

    assert no_margin == 300
    assert margin is not None and margin > no_margin
    assert recommend_dpi_from_images([oversized]) == 600
    assert recommend_dpi_from_images([tiny]) == 72


def test_unreadable_images_are_skipped_and_empty_input_has_no_recommendation(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.png"
    invalid.write_text("not an image", encoding="utf-8")
    assert recommend_dpi_from_images([]) is None
    assert recommend_dpi_from_images([invalid]) is None
    assert recommend_dpi_from_images([invalid, create_image(tmp_path / "valid.png", (1240, 1754))]) == 150


def test_recommend_dpi_swaps_axes_for_exif_orientation_6(tmp_path: Path) -> None:
    oriented_path = tmp_path / "orientation-6.jpg"
    reference_path = tmp_path / "portrait.jpg"
    image = Image.new("RGB", (200, 100), "white")
    exif = image.getexif()
    exif[0x0112] = 6
    image.save(oriented_path, exif=exif)
    image.close()
    create_image(reference_path, (100, 200))
    assert recommend_dpi_from_images([oriented_path]) == recommend_dpi_from_images([reference_path])


def test_recommend_dpi_does_not_decode_pixels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = create_image(tmp_path / "header-only.png", (2480, 3508))
    def forbidden(*_args, **_kwargs):
        raise AssertionError("DPI estimation should read metadata only")
    monkeypatch.setattr(Image.Image, "load", forbidden)
    monkeypatch.setattr(Image.Image, "copy", forbidden)
    assert recommend_dpi_from_images([source]) == 300


def test_recommend_dpi_skips_decompression_bomb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = create_image(tmp_path / "large-for-threshold.png", (50, 50))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    assert recommend_dpi_from_images([source]) is None


def test_invalid_margin_is_rejected() -> None:
    with pytest.raises(ValueError, match="margem"):
        recommend_dpi_from_images([], margin_mm=41)
