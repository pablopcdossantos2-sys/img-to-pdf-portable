"""Process a folder of PDFs with a reusable PDF Hub workflow profile."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from document_tools.errors import friendly_error_message
from document_tools.pdf_ops import process_pdf_pipeline
from document_tools.profiles import migrate_local_profile


@dataclass(frozen=True)
class BatchFileResult:
    source_path: str
    success: bool
    output_path: str
    message: str


ProgressCallback = Callable[[int, int, str], None]


def _unique_output_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}.pdf"
    number = 2
    while candidate.exists():
        candidate = directory / f"{stem}{suffix}-{number}.pdf"
        number += 1
    return candidate


def process_pdf_folder(
    source_directory: str | Path,
    output_directory: str | Path,
    profile: dict[str, object],
    *,
    recursive: bool = False,
    file_mode: int = 0o600,
    progress_callback: ProgressCallback | None = None,
) -> list[BatchFileResult]:
    """Apply a profile to each PDF; failures are recorded without stopping the batch.

    Source PDFs are never modified. Existing output files are preserved by selecting
    a numbered alternative. Recursive runs mirror the source's relative subfolders.
    """
    source_root = Path(source_directory).expanduser().resolve()
    output_root = Path(output_directory).expanduser().resolve()
    if not source_root.is_dir():
        raise ValueError("Selecione uma pasta de origem.")
    if not output_root.is_dir():
        raise ValueError("Escolha uma pasta de saída existente.")
    if output_root == source_root or source_root in output_root.parents:
        raise ValueError("A pasta de saída não pode ser a pasta de origem nem ficar dentro dela.")

    settings = migrate_local_profile(profile)
    rotate_enabled = settings["rotate_enabled"]
    stamp_enabled = settings["stamp_enabled"]
    optimize_enabled = settings["optimize_enabled"]
    if not (rotate_enabled or stamp_enabled or optimize_enabled):
        raise ValueError("Selecione pelo menos uma etapa do fluxo.")
    watermark_text = str(settings["stamp_text"]).strip() if stamp_enabled else ""
    page_numbering = bool(settings["page_numbering"]) if stamp_enabled else False
    if stamp_enabled and not watermark_text and not page_numbering:
        raise ValueError("A etapa de marca d'água precisa de um texto ou da numeração ativada.")

    discovered = source_root.rglob("*") if recursive else source_root.iterdir()
    sources = sorted(
        (path for path in discovered if path.is_file() and not path.is_symlink() and path.suffix.casefold() == ".pdf"),
        key=lambda path: str(path).casefold(),
    )
    if not sources:
        raise ValueError("A pasta selecionada não contém arquivos PDF.")

    suffix = str(settings["output_suffix"])
    results: list[BatchFileResult] = []
    total = len(sources)
    for completed, source in enumerate(sources, start=1):
        try:
            relative_parent = source.parent.relative_to(source_root) if recursive else Path()
            target_directory = output_root / relative_parent
            target_directory.mkdir(parents=True, exist_ok=True)
            destination = _unique_output_path(target_directory, source.stem, suffix)
            process_pdf_pipeline(
                source, destination,
                rotate_angle=int(settings["rotate_angle"]) if rotate_enabled else None,
                rotate_ranges=(str(settings["rotate_ranges"]).strip() or None) if rotate_enabled else None,
                watermark_text=watermark_text or None,
                page_numbering=page_numbering,
                stamp_ranges=(str(settings["stamp_ranges"]).strip() or None) if stamp_enabled else None,
                optimize_mode=str(settings["optimize_mode"]) if optimize_enabled else None,
                quality=int(settings["quality"]),
                password=None,
                file_mode=file_mode,
            )
            result = BatchFileResult(str(source), True, str(destination), "Processado com sucesso.")
        except Exception as error:
            result = BatchFileResult(str(source), False, "", friendly_error_message(error))
        results.append(result)
        if progress_callback is not None:
            progress_callback(completed, total, source.name)
    return results
