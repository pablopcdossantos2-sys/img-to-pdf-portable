"""Process a folder of PDFs with resumable, reusable PDF Hub workflow profiles."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from document_tools.errors import friendly_error_message
from document_tools.pdf_ops import process_pdf_pipeline
from document_tools.profiles import migrate_local_profile


CHECKPOINT_FILENAME = ".pdf-hub-batch-state.json"
_CHECKPOINT_VERSION = 1
_RESUMED_MESSAGE = "Concluído antes da interrupção; resultado reutilizado."


@dataclass(frozen=True)
class BatchFileResult:
    source_path: str
    success: bool
    output_path: str
    message: str


ProgressCallback = Callable[[int, int, str], None]


class BatchControl:
    """Thread-safe pause and cancel requests, checked between PDFs."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._pause_requested = False
        self._cancel_requested = False
        self._stopped = False

    def pause(self) -> None:
        with self._condition:
            if not self._cancel_requested:
                self._pause_requested = True

    def resume(self) -> None:
        with self._condition:
            self._pause_requested = False
            self._condition.notify_all()

    def cancel(self) -> None:
        with self._condition:
            self._cancel_requested = True
            self._pause_requested = False
            self._condition.notify_all()

    def wait_until_resumed(self) -> bool:
        """Block while paused; return False when cancellation has been requested."""
        with self._condition:
            while self._pause_requested and not self._cancel_requested:
                self._condition.wait()
            return not self._cancel_requested

    @property
    def is_paused(self) -> bool:
        with self._condition:
            return self._pause_requested and not self._cancel_requested

    @property
    def was_stopped(self) -> bool:
        with self._condition:
            return self._stopped

    def mark_stopped(self) -> None:
        with self._condition:
            self._stopped = True


def _unique_output_path(directory: Path, stem: str, suffix: str) -> Path:
    candidate = directory / f"{stem}{suffix}.pdf"
    number = 2
    while candidate.exists():
        candidate = directory / f"{stem}{suffix}-{number}.pdf"
        number += 1
    return candidate


def _batch_fingerprint(
    source_root: Path,
    output_root: Path,
    recursive: bool,
    settings: dict[str, object],
    sources: list[Path],
) -> str:
    inventory: list[dict[str, object]] = []
    for source in sources:
        relative = source.relative_to(source_root).as_posix()
        try:
            stat = source.stat()
            size: int | None = stat.st_size
            modified_ns: int | None = stat.st_mtime_ns
        except OSError:
            size = None
            modified_ns = None
        inventory.append({"path": relative, "size": size, "modified_ns": modified_ns})
    identity = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "recursive": recursive,
        "profile": settings,
        "files": inventory,
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_checkpoint(
    checkpoint_path: Path,
    fingerprint: str,
    results: dict[str, dict[str, object]],
    *,
    completed: bool = False,
) -> None:
    """Atomically persist per-file progress so a later run can safely resume."""
    temporary_path = checkpoint_path.with_name(checkpoint_path.name + ".tmp")
    payload = {
        "version": _CHECKPOINT_VERSION,
        "fingerprint": fingerprint,
        "completed": completed,
        "results": results,
    }
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, checkpoint_path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _read_checkpoint(
    checkpoint_path: Path,
    fingerprint: str,
    valid_relative_paths: set[str],
    output_root: Path,
) -> dict[str, dict[str, object]]:
    """Read only matching, well-formed records and reuse successful existing outputs."""
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if (
        not isinstance(payload, dict)
        or type(payload.get("version")) is not int
        or payload.get("version") != _CHECKPOINT_VERSION
        or payload.get("fingerprint") != fingerprint
        or payload.get("completed") is True
        or not isinstance(payload.get("results"), dict)
    ):
        return {}

    reusable: dict[str, dict[str, object]] = {}
    for relative, item in payload["results"].items():
        if relative not in valid_relative_paths or not isinstance(item, dict):
            continue
        success = item.get("success")
        message = item.get("message")
        if not isinstance(success, bool) or not isinstance(message, str):
            continue
        if success:
            raw_output_path = item.get("output_path")
            if not isinstance(raw_output_path, str) or not raw_output_path:
                continue
            try:
                output_path = Path(raw_output_path).expanduser().resolve()
                is_safe_output = output_path.is_file() and output_root in output_path.parents
            except (OSError, RuntimeError, ValueError):
                is_safe_output = False
            if not is_safe_output:
                continue
            reusable[relative] = {
                "success": True,
                "output_path": str(output_path),
                "message": message,
            }
        else:
            reusable[relative] = {"success": False, "output_path": "", "message": message}
    return reusable


def process_pdf_folder(
    source_directory: str | Path,
    output_directory: str | Path,
    profile: dict[str, object],
    *,
    recursive: bool = False,
    file_mode: int = 0o600,
    progress_callback: ProgressCallback | None = None,
    resume: bool = False,
    control: BatchControl | None = None,
) -> list[BatchFileResult]:
    """Apply a profile to each PDF, optionally resuming an interrupted batch.

    Successful files recorded in a matching checkpoint are reused only when the
    source/output folders, profile, recursion setting, and source-file inventory
    still match. Failed files are retried. Originals are never modified and
    existing output files are preserved by choosing a numbered alternative.
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
    checkpoint_path = output_root / CHECKPOINT_FILENAME
    fingerprint = _batch_fingerprint(source_root, output_root, recursive, settings, sources)
    relative_paths = {source.relative_to(source_root).as_posix() for source in sources}
    previous = (
        _read_checkpoint(checkpoint_path, fingerprint, relative_paths, output_root)
        if resume and checkpoint_path.is_file()
        else {}
    )
    # Write an initial checkpoint before opening the first PDF, then update it
    # after every file. A mismatch intentionally starts a new batch.
    result_state = dict(previous)
    _write_checkpoint(checkpoint_path, fingerprint, result_state)

    results: list[BatchFileResult] = []
    total = len(sources)
    for completed, source in enumerate(sources, start=1):
        if control is not None and not control.wait_until_resumed():
            control.mark_stopped()
            break
        relative = source.relative_to(source_root).as_posix()
        stored = previous.get(relative)
        if stored is not None and stored.get("success") is True:
            result = BatchFileResult(str(source), True, str(stored["output_path"]), _RESUMED_MESSAGE)
        else:
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

            result_state[relative] = {
                "success": result.success,
                "output_path": result.output_path,
                "message": result.message,
            }
            _write_checkpoint(checkpoint_path, fingerprint, result_state)

        results.append(result)
        if progress_callback is not None:
            progress_callback(completed, total, source.name)

    # On user cancellation, keep the last atomic checkpoint for the next run.
    # The current PDF is always allowed to finish before this boundary is checked.
    if control is not None and control.was_stopped:
        return results

    # Mark completion before cleanup. If cleanup is blocked, the completed
    # checkpoint is ignored on the next run instead of suppressing a new batch.
    try:
        _write_checkpoint(checkpoint_path, fingerprint, result_state, completed=True)
    finally:
        try:
            checkpoint_path.unlink()
        except OSError:
            pass
    return results
