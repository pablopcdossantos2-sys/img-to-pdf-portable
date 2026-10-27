from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as reportlab_canvas

import document_tools.pdf_ops as pdf_ops
from document_tools.pdf_ops import (
    convert_image,
    extract_pages,
    images_to_pdf,
    merge_pdfs,
    parse_page_ranges,
    process_pdf_pipeline,
    pdf_requires_user_password,
    pdf_page_count,
    optimize_pdf,
    reorder_pdf_pages,
    stamp_pdf,
    rotate_pdf,
    split_pdf,
)


def create_pdf(path: Path, widths: list[float], *, password: str | None = None) -> Path:
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width=width, height=300)
    if password is not None:
        writer.encrypt(user_password=password, owner_password="owner", algorithm="AES-256")
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def read_pdf(path: Path) -> PdfReader:
    """Read from memory so tests never leave a file handle open on Windows."""
    return PdfReader(BytesIO(path.read_bytes()))


def test_parse_page_ranges_expands_ranges_and_preserves_order() -> None:
    assert parse_page_ranges("3, 1-2, 5, 8-9", 9) == [2, 0, 1, 4, 7, 8]


@pytest.mark.parametrize(
    ("specification", "page_count", "message"),
    [
        ("", 5, "Informe páginas"),
        ("1,,2", 5, "item vazio"),
        ("1-0", 5, "precisa estar"),
        ("2-6", 5, "precisa estar"),
        ("1, 1-2", 5, "informada mais de uma vez"),
        ("1-a", 5, "inválido"),
    ],
)
def test_parse_page_ranges_rejects_invalid_input(
    specification: str, page_count: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_page_ranges(specification, page_count)


def test_parse_page_ranges_can_allow_duplicate_pages() -> None:
    assert parse_page_ranges("2, 1-2", 3, allow_duplicates=True) == [1, 0, 1]


def test_images_to_pdf_creates_one_a4_page_per_image(tmp_path: Path) -> None:
    portrait = tmp_path / "portrait.png"
    landscape = tmp_path / "landscape.png"
    output = tmp_path / "images.pdf"
    Image.new("RGB", (400, 800), "red").save(portrait)
    Image.new("RGB", (800, 400), "blue").save(landscape)

    result = images_to_pdf([portrait, landscape], output)

    assert result == output.resolve()
    reader = read_pdf(output)
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.height) > float(reader.pages[0].mediabox.width)
    assert float(reader.pages[1].mediabox.width) > float(reader.pages[1].mediabox.height)


def test_images_to_pdf_flattens_transparency_over_white(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    output = tmp_path / "transparent.pdf"
    image = Image.new("RGBA", (16, 16), (255, 0, 0, 0))
    image.putpixel((8, 8), (255, 0, 0, 128))
    image.save(source)
    image.close()

    images_to_pdf([source], output)

    reader = read_pdf(output)
    assert len(reader.pages) == 1
    embedded_images = reader.pages[0].images
    assert embedded_images
    with embedded_images[0].image as extracted:
        background = extracted.convert("RGB").getpixel((0, 0))
        assert min(background) >= 245


def test_merge_pdfs_preserves_document_order_and_outline(tmp_path: Path) -> None:
    first = create_pdf(tmp_path / "first.pdf", [120, 130])
    second = tmp_path / "second.pdf"
    writer = PdfWriter()
    for width in [220, 230, 240]:
        writer.add_blank_page(width=width, height=300)
    writer.add_outline_item("Second document", 0)
    with second.open("wb") as stream:
        writer.write(stream)
    output = tmp_path / "merged.pdf"

    merge_pdfs([first, second], output)

    reader = read_pdf(output)
    assert len(reader.pages) == 5
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [
        120, 130, 220, 230, 240
    ]
    assert reader.outline


def test_extract_pages_keeps_requested_order(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140, 150])
    output = tmp_path / "extracted.pdf"

    extract_pages(source, "5, 2-3", output)

    reader = read_pdf(output)
    assert len(reader.pages) == 3
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [
        150, 120, 130
    ]


def test_extract_pages_can_repeat_pages_when_requested(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130])
    output = tmp_path / "repeated.pdf"

    extract_pages(source, "2, 1-2", output, allow_duplicates=True)

    reader = read_pdf(output)
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [120, 110, 120]


@pytest.mark.parametrize("angle", [90, 180, 270])
def test_rotate_pdf_rotates_only_requested_pages(tmp_path: Path, angle: int) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120, 130, 140])
    output = tmp_path / f"rotated-{angle}.pdf"

    rotate_pdf(source, output, angle, "2, 2")

    reader = read_pdf(output)
    assert [int(page.get("/Rotate", 0)) for page in reader.pages] == [0, angle, 0]


def test_split_pdf_creates_missing_destination_directory(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120, 130, 140])
    output_dir = tmp_path / "new" / "split"

    outputs = split_pdf(source, output_dir)

    assert output_dir.is_dir()
    assert [path.name for path in outputs] == [
        "source-pagina-001.pdf",
        "source-pagina-002.pdf",
        "source-pagina-003.pdf",
    ]
    assert all(len(read_pdf(path).pages) == 1 for path in outputs)
    with pytest.raises(FileExistsError, match="já contém"):
        split_pdf(source, output_dir)


def test_split_pdf_can_group_every_n_pages(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140, 150])
    outputs = split_pdf(source, tmp_path / "split", mode="every_n_pages", pages_per_file=2)
    assert [len(read_pdf(path).pages) for path in outputs] == [2, 2, 1]
    assert [round(float(page.mediabox.width)) for path in outputs for page in read_pdf(path).pages] == [110, 120, 130, 140, 150]


def test_split_pdf_can_split_after_selected_pages(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140, 150, 160])
    outputs = split_pdf(source, tmp_path / "split", mode="after_pages", split_after_pages="2, 5")
    assert [len(read_pdf(path).pages) for path in outputs] == [2, 3, 1]


@pytest.mark.parametrize(
    ("mode", "expected_lengths"),
    [("after_even_pages", [2, 2, 1]), ("after_odd_pages", [1, 2, 2])],
)
def test_split_pdf_can_split_after_even_or_odd_pages(tmp_path: Path, mode: str, expected_lengths: list[int]) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140, 150])
    outputs = split_pdf(source, tmp_path / mode, mode=mode)
    assert [len(read_pdf(path).pages) for path in outputs] == expected_lengths


def test_split_pdf_can_split_by_approximate_size(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130])
    outputs = split_pdf(source, tmp_path / "split", mode="by_size", target_size_mb=0.000001)
    assert len(outputs) == 3
    assert all(len(read_pdf(path).pages) == 1 for path in outputs)


def test_split_pdf_can_split_at_bookmark_level(tmp_path: Path) -> None:
    source = tmp_path / "bookmarked.pdf"
    writer = PdfWriter()
    for width in (110, 120, 130, 140):
        writer.add_blank_page(width=width, height=300)
    writer.add_outline_item("Chapter One", 0)
    writer.add_outline_item("Chapter Two", 2)
    with source.open("wb") as stream:
        writer.write(stream)
    outputs = split_pdf(source, tmp_path / "split", mode="by_bookmarks", bookmark_level=1)
    assert [len(read_pdf(path).pages) for path in outputs] == [2, 2]
    assert [round(float(page.mediabox.width)) for path in outputs for page in read_pdf(path).pages] == [110, 120, 130, 140]


def test_split_pdf_rolls_back_partial_outputs_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120, 130, 140])
    output_dir = tmp_path / "split"
    original_save = pdf_ops._atomic_pdf_save
    calls = 0

    def fail_second_save(output: Path, write_document, *, overwrite: bool = True, file_mode: int = 0o600) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated failure")
        original_save(output, write_document, overwrite=overwrite, file_mode=file_mode)

    monkeypatch.setattr(pdf_ops, "_atomic_pdf_save", fail_second_save)
    with pytest.raises(OSError, match="simulated failure"):
        split_pdf(source, output_dir)
    assert list(output_dir.glob("*.pdf")) == []


def test_empty_password_encrypted_pdf_can_be_processed(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "owner-only.pdf", [120, 130], password="")
    output = tmp_path / "extracted.pdf"

    extract_pages(source, "1", output)

    assert len(read_pdf(output).pages) == 1


def test_password_protected_pdf_accepts_correct_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [120], password="secret")
    output = tmp_path / "out.pdf"

    assert pdf_requires_user_password(source) is True
    extract_pages(source, "1", output, password="secret")

    assert len(read_pdf(output).pages) == 1


def test_password_protected_pdf_rejects_wrong_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [120], password="secret")
    output = tmp_path / "out.pdf"

    with pytest.raises(ValueError, match="senha informada.*incorreta"):
        extract_pages(source, "1", output, password="wrong")
    assert not output.exists()


def test_merge_pdfs_accepts_individual_passwords(tmp_path: Path) -> None:
    first = create_pdf(tmp_path / "locked.pdf", [120], password="secret")
    second = create_pdf(tmp_path / "plain.pdf", [130])
    output = tmp_path / "merged.pdf"

    merge_pdfs([first, second], output, passwords=["secret", None])

    assert [round(float(page.mediabox.width)) for page in read_pdf(output).pages] == [120, 130]


def test_split_pdf_accepts_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [120, 130], password="secret")
    outputs = split_pdf(source, tmp_path / "split", password="secret")

    assert len(outputs) == 2
    assert all(len(read_pdf(path).pages) == 1 for path in outputs)


def test_rotate_pdf_accepts_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [120], password="secret")
    output = tmp_path / "rotated.pdf"

    rotate_pdf(source, output, 90, password="secret")

    assert int(read_pdf(output).pages[0].get("/Rotate", 0)) == 90


def test_images_to_pdf_imports_all_frames_from_multipage_tiff(tmp_path: Path) -> None:
    source = tmp_path / "multipage.tiff"
    output = tmp_path / "all-frames.pdf"
    first = Image.new("RGB", (24, 16), "red")
    second = Image.new("RGB", (32, 20), "blue")
    try:
        first.save(source, format="TIFF", save_all=True, append_images=[second])
    finally:
        first.close()
        second.close()

    images_to_pdf([source], output, all_frames=True)

    assert len(read_pdf(output).pages) == 2


def test_images_to_pdf_can_use_only_first_frame(tmp_path: Path) -> None:
    source = tmp_path / "multipage.tiff"
    output = tmp_path / "first-frame.pdf"
    first = Image.new("RGB", (24, 16), "red")
    second = Image.new("RGB", (32, 20), "blue")
    try:
        first.save(source, format="TIFF", save_all=True, append_images=[second])
    finally:
        first.close()
        second.close()

    images_to_pdf([source], output, all_frames=False)

    assert len(read_pdf(output).pages) == 1


def test_extract_pages_preserves_metadata_and_bookmarks(tmp_path: Path) -> None:
    source = tmp_path / "with-outline.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=110, height=300)
    writer.add_blank_page(width=120, height=300)
    writer.add_blank_page(width=130, height=300)
    writer.add_metadata({"/Title": "PDF Hub test"})
    writer.add_outline_item("Second page", 1)
    writer.add_outline_item("Third page", 2)
    with source.open("wb") as stream:
        writer.write(stream)
    output = tmp_path / "extract.pdf"

    extract_pages(source, "2-3", output)

    reader = read_pdf(output)
    assert reader.metadata.title == "PDF Hub test"
    assert reader.outline


@pytest.mark.skipif(__import__("os").name == "nt", reason="POSIX permission bits are not portable to Windows")
def test_pdf_output_permissions_can_be_shared(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120])
    output = tmp_path / "shared.pdf"

    extract_pages(source, "1", output, file_mode=0o644)

    assert output.stat().st_mode & 0o777 == 0o644


def test_pdf_page_count_supports_password_protected_pdfs(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [120, 130], password="secret")

    assert pdf_page_count(source, password="secret") == 2
    with pytest.raises(ValueError, match="senha informada.*incorreta"):
        pdf_page_count(source, password="wrong")


def test_reorder_pdf_pages_preserves_requested_order(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140])
    output = tmp_path / "reordered.pdf"

    reorder_pdf_pages(source, [4, 2, 1, 3], output)

    reader = read_pdf(output)
    assert [round(float(page.mediabox.width)) for page in reader.pages] == [140, 120, 110, 130]


@pytest.mark.parametrize("order", [[1, 1, 3], [1, 2], [1, 2, 4], []])
def test_reorder_pdf_pages_rejects_non_permutations(tmp_path: Path, order: list[int]) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130])
    output = tmp_path / "reordered.pdf"

    with pytest.raises(ValueError, match="cada página uma única vez"):
        reorder_pdf_pages(source, order, output)

    assert not output.exists()


def test_reorder_pdf_pages_accepts_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [110, 120], password="secret")
    output = tmp_path / "reordered.pdf"

    reorder_pdf_pages(source, [2, 1], output, password="secret")

    assert [round(float(page.mediabox.width)) for page in read_pdf(output).pages] == [120, 110]


def test_stamp_pdf_applies_watermark_and_page_numbers(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [300, 320])
    output = tmp_path / "stamped.pdf"

    stamp_pdf(source, output, watermark_text="CONFIDENTIAL", page_numbering=True)

    reader = read_pdf(output)
    assert len(reader.pages) == 2
    assert "CONFIDENTIAL" in reader.pages[0].extract_text()
    assert "1 / 2" in reader.pages[0].extract_text()
    assert "2 / 2" in reader.pages[1].extract_text()


def test_stamp_pdf_only_changes_selected_pages_and_keeps_original_numbering(
    tmp_path: Path,
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [300, 320, 340, 360])
    output = tmp_path / "selected.pdf"

    stamp_pdf(
        source,
        output,
        watermark_text="SELECTED",
        page_numbering=True,
        page_ranges="2-3",
    )

    pages = read_pdf(output).pages
    assert len(pages) == 4
    assert "SELECTED" not in (pages[0].extract_text() or "")
    assert "1 / 4" not in (pages[0].extract_text() or "")
    assert "SELECTED" in (pages[1].extract_text() or "")
    assert "2 / 4" in (pages[1].extract_text() or "")
    assert "SELECTED" in (pages[2].extract_text() or "")
    assert "3 / 4" in (pages[2].extract_text() or "")
    assert "SELECTED" not in (pages[3].extract_text() or "")
    assert "4 / 4" not in (pages[3].extract_text() or "")


def test_stamp_pdf_rejects_invalid_page_range_without_creating_output(
    tmp_path: Path,
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [300, 320])
    output = tmp_path / "invalid-ranges.pdf"

    with pytest.raises(ValueError, match="precisa estar entre 1 e 2"):
        stamp_pdf(source, output, watermark_text="TEST", page_ranges="2-3")

    assert not output.exists()


def test_stamp_pdf_rejects_empty_stamp_request(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [300])
    output = tmp_path / "stamped.pdf"

    with pytest.raises(ValueError, match="Informe o texto da marca"):
        stamp_pdf(source, output)

    assert not output.exists()


def test_stamp_pdf_can_number_pages_without_watermark(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [300])
    output = tmp_path / "numbered.pdf"

    stamp_pdf(source, output, page_numbering=True)

    assert "1 / 1" in read_pdf(output).pages[0].extract_text()


def test_stamp_pdf_accepts_password(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "locked.pdf", [300], password="secret")
    output = tmp_path / "stamped.pdf"

    stamp_pdf(source, output, watermark_text="TEST", password="secret")

    assert "TEST" in read_pdf(output).pages[0].extract_text()


def test_optimize_pdf_lossless_preserves_pages_and_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    writer = PdfWriter()
    for width in (110, 120, 130):
        writer.add_blank_page(width=width, height=300)
    writer.add_metadata({"/Title": "PDF Hub optimize test"})
    with source.open("wb") as stream:
        writer.write(stream)
    output = tmp_path / "optimized.pdf"

    optimize_pdf(source, output, mode="lossless")

    reader = read_pdf(output)
    assert len(reader.pages) == 3
    assert reader.metadata.title == "PDF Hub optimize test"


def test_optimize_pdf_balanced_recompresses_supported_image_pdfs(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    source = tmp_path / "source.pdf"
    output = tmp_path / "optimized.pdf"
    Image.new("RGB", (600, 400), "navy").save(image)
    images_to_pdf([image], source)

    optimize_pdf(source, output, mode="balanced", quality=75)

    reader = read_pdf(output)
    assert len(reader.pages) == 1
    assert output.stat().st_size > 0


def test_optimize_pdf_quality_setting_changes_image_compression(tmp_path: Path) -> None:
    image_path = tmp_path / "photo.jpg"
    source = tmp_path / "photo.pdf"
    low_quality = tmp_path / "low-quality.pdf"
    high_quality = tmp_path / "high-quality.pdf"
    image = Image.effect_noise((1000, 700), 100).convert("RGB")
    image.save(image_path, format="JPEG", quality=96)
    image.close()
    document = reportlab_canvas.Canvas(str(source), pagesize=(1000, 700))
    document.drawImage(str(image_path), 0, 0, width=1000, height=700)
    document.showPage()
    document.save()
    optimize_pdf(source, low_quality, mode="balanced", quality=50)
    optimize_pdf(source, high_quality, mode="balanced", quality=95)
    assert len(read_pdf(low_quality).pages) == 1
    assert low_quality.stat().st_size < high_quality.stat().st_size
    assert low_quality.stat().st_size < source.stat().st_size


def test_optimize_pdf_rejects_invalid_mode_and_quality(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110])
    output = tmp_path / "optimized.pdf"

    with pytest.raises(ValueError, match="Escolha otimização"):
        optimize_pdf(source, output, mode="maximum")
    with pytest.raises(ValueError, match="qualidade JPEG"):
        optimize_pdf(source, output, mode="balanced", quality=99)


def test_convert_image_resizes_and_converts_to_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "converted.jpg"
    Image.new("RGBA", (800, 400), (50, 150, 230, 120)).save(source)

    convert_image(
        source,
        output,
        "JPEG",
        max_width=300,
        max_height=300,
        quality=85,
    )

    with Image.open(output) as converted:
        assert converted.format == "JPEG"
        assert converted.size == (300, 150)
        assert converted.mode == "RGB"


@pytest.mark.parametrize(
    ("output_format", "extension"),
    [
        ("JPEG", ".jpg"),
        ("PNG", ".png"),
        ("WEBP", ".webp"),
        ("BMP", ".bmp"),
        ("TIFF", ".tif"),
    ],
)
def test_convert_image_supports_each_output_format(
    tmp_path: Path, output_format: str, extension: str
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / f"converted{extension}"
    Image.new("RGBA", (40, 20), (20, 100, 220, 90)).save(source)

    convert_image(source, output, output_format)

    with Image.open(output) as converted:
        assert converted.format == output_format
        assert converted.size == (40, 20)


@pytest.mark.parametrize("output_format", ["PNG", "WEBP"])
def test_cmyk_image_can_convert_to_rgb_only_formats(
    tmp_path: Path, output_format: str
) -> None:
    source = tmp_path / "source.tiff"
    output = tmp_path / f"converted.{output_format.lower()}"
    Image.new("CMYK", (120, 60), (10, 20, 30, 40)).save(source)

    convert_image(source, output, output_format)

    with Image.open(output) as converted:
        assert converted.format == output_format
        assert converted.mode in {"RGB", "RGBA"}
        assert converted.size == (120, 60)


def test_convert_image_preserves_compatible_icc_profile(tmp_path: Path) -> None:
    source = tmp_path / "profile.png"
    output = tmp_path / "profile.jpg"
    profile = b"test-rgb-icc-profile"
    Image.new("RGB", (30, 20), "blue").save(source, icc_profile=profile)

    convert_image(source, output, "JPEG")

    with Image.open(output) as converted:
        assert converted.info.get("icc_profile") == profile


def test_operations_never_overwrite_their_source(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [120])
    original = source.read_bytes()
    with pytest.raises(ValueError, match="não pode substituir"):
        extract_pages(source, "1", source)
    assert source.read_bytes() == original


def test_atomic_pdf_save_preserves_existing_destination_when_writer_fails(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "existing.pdf"
    original_content = b"pre-existing file"
    destination.write_bytes(original_content)

    def fail_write(_temporary: Path) -> None:
        raise OSError("simulated write error")

    with pytest.raises(OSError, match="simulated write error"):
        pdf_ops._atomic_pdf_save(destination, fail_write)

    assert destination.read_bytes() == original_content
    assert list(tmp_path.glob(".document-tools-*.pdf")) == []

def test_process_pdf_pipeline_chains_rotation_stamping_and_optimization(
    tmp_path: Path,
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120, 130, 140])
    original = source.read_bytes()
    output = tmp_path / "pipeline.pdf"

    process_pdf_pipeline(
        source,
        output,
        rotate_angle=90,
        rotate_ranges="2",
        watermark_text="BATCH",
        page_numbering=True,
        stamp_ranges="3",
        optimize_mode="lossless",
    )

    pages = read_pdf(output).pages
    assert len(pages) == 4
    assert int(pages[1].get("/Rotate", 0)) == 90
    assert "BATCH" not in (pages[0].extract_text() or "")
    assert "BATCH" in (pages[2].extract_text() or "")
    assert "3 / 4" in (pages[2].extract_text() or "")
    assert "BATCH" not in (pages[3].extract_text() or "")
    assert source.read_bytes() == original


def test_process_pdf_pipeline_requires_at_least_one_operation(tmp_path: Path) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110])
    output = tmp_path / "pipeline.pdf"

    with pytest.raises(ValueError, match="Selecione pelo menos uma etapa"):
        process_pdf_pipeline(source, output)

    assert not output.exists()


def test_process_pdf_pipeline_preserves_existing_output_on_failed_final_stage(
    tmp_path: Path,
) -> None:
    source = create_pdf(tmp_path / "source.pdf", [110, 120])
    output = create_pdf(tmp_path / "existing.pdf", [210])
    original = output.read_bytes()

    with pytest.raises(ValueError, match="precisa estar entre 1 e 2"):
        process_pdf_pipeline(
            source,
            output,
            rotate_angle=90,
            watermark_text="BATCH",
            stamp_ranges="2-3",
        )

    assert output.read_bytes() == original
    assert not list(tmp_path.glob("pdf-hub-pipeline-*"))
