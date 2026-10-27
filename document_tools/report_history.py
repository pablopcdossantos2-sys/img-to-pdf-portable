"""Local persistence for complete PDF-folder batch reports."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

HISTORY_SCHEMA_VERSION = 1
MAX_HISTORY_REPORTS = 50
_FILENAME_PREFIX = "batch-report-"
_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_PROFILE_FIELDS = {
    "rotate_enabled", "rotate_angle", "rotate_ranges",
    "stamp_enabled", "stamp_text", "page_numbering", "stamp_ranges",
    "optimize_enabled", "optimize_mode", "quality", "output_suffix",
}


def _report_path(directory: Path, report_id: str) -> Path:
    if not _ID_PATTERN.fullmatch(report_id):
        raise ValueError("Identificador de relatório inválido.")
    return directory / f"{_FILENAME_PREFIX}{report_id}.json"


def _clean_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Keep known processing options only; paths and credentials are never copied."""
    clean: dict[str, Any] = {}
    for key in _PROFILE_FIELDS:
        value = profile.get(key)
        if isinstance(value, (str, bool, int, float)) or value is None:
            clean[key] = value
    return clean


def _valid_report(report: Any, expected_id: str | None = None) -> bool:
    if not isinstance(report, dict):
        return False
    report_id = report.get("id")
    if not isinstance(report_id, str) or not _ID_PATTERN.fullmatch(report_id):
        return False
    if expected_id is not None and report_id != expected_id:
        return False
    if report.get("schema_version") != HISTORY_SCHEMA_VERSION:
        return False
    if not all(isinstance(report.get(key), str) for key in (
        "created_at", "source_directory", "output_directory", "profile_name"
    )):
        return False
    if not isinstance(report.get("profile"), dict) or not isinstance(report.get("recursive"), bool):
        return False
    if report.get("file_mode") not in (0o600, 0o644):
        return False
    if not isinstance(report.get("cancelled"), bool) or not isinstance(report.get("results"), list):
        return False
    for item in report["results"]:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("source_path"), str) or not isinstance(item.get("success"), bool):
            return False
        if not isinstance(item.get("output_path"), str) or not isinstance(item.get("message"), str):
            return False
    return True


def save_batch_report(
    directory: str | Path,
    *,
    source_directory: str,
    output_directory: str,
    profile_name: str,
    profile: dict[str, Any],
    recursive: bool,
    file_mode: int,
    results: list[Any],
    cancelled: bool = False,
) -> dict[str, Any]:
    """Atomically save every result in a report and prune older reports beyond the limit."""
    history_dir = Path(directory).expanduser()
    history_dir.mkdir(parents=True, exist_ok=True)
    report_id = uuid.uuid4().hex
    saved_results = [
        {
            "source_path": str(item.source_path),
            "success": bool(item.success),
            "output_path": str(item.output_path),
            "message": str(item.message),
        }
        for item in results
    ]
    report: dict[str, Any] = {
        "schema_version": HISTORY_SCHEMA_VERSION,
        "id": report_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "created_timestamp": time.time(),
        "source_directory": str(source_directory),
        "output_directory": str(output_directory),
        "profile_name": str(profile_name),
        "profile": _clean_profile(profile),
        "recursive": bool(recursive),
        "file_mode": file_mode if file_mode in (0o600, 0o644) else 0o600,
        "cancelled": bool(cancelled),
        "results": saved_results,
    }
    if not _valid_report(report, report_id):
        raise ValueError("O relatório do lote contém dados inválidos.")

    target = _report_path(history_dir, report_id)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=history_dir,
            prefix=".batch-report-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass

    _prune_history(history_dir)
    return report


def _candidate_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    paths = [
        path for path in directory.glob(f"{_FILENAME_PREFIX}*.json")
        if _ID_PATTERN.fullmatch(path.stem.removeprefix(_FILENAME_PREFIX))
    ]
    def modified(path: Path) -> tuple[int, str]:
        try:
            timestamp = path.stat().st_mtime_ns
        except OSError:
            timestamp = 0
        return timestamp, path.name
    return sorted(paths, key=modified, reverse=True)


def _prune_history(directory: Path) -> None:
    for path in _candidate_files(directory)[MAX_HISTORY_REPORTS:]:
        try:
            path.unlink()
        except OSError:
            # A cleanup failure must not invalidate the report that was just saved.
            continue


def load_batch_history(directory: str | Path) -> list[dict[str, Any]]:
    """Read newest valid reports; malformed or unsupported files are safely ignored."""
    history_dir = Path(directory).expanduser()
    reports: list[dict[str, Any]] = []
    for path in _candidate_files(history_dir):
        try:
            with path.open("r", encoding="utf-8") as stream:
                report = json.load(stream)
            expected_id = path.stem.removeprefix(_FILENAME_PREFIX)
            if not _valid_report(report, expected_id):
                continue
            if "created_timestamp" not in report:
                report["created_timestamp"] = path.stat().st_mtime
            reports.append(report)
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    reports.sort(
        key=lambda item: (float(item.get("created_timestamp", 0)), str(item.get("id", ""))),
        reverse=True,
    )
    return reports[:MAX_HISTORY_REPORTS]


def delete_batch_report(directory: str | Path, report_id: str) -> bool:
    """Delete exactly one report by its generated identifier."""
    target = _report_path(Path(directory).expanduser(), report_id)
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
