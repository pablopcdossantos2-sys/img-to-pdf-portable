from __future__ import annotations

from pathlib import Path

import pytest

import document_tools.batch_processing as batch
from document_tools.batch_processing import BatchControl, CHECKPOINT_FILENAME, process_pdf_folder


def make_profile() -> dict[str, object]:
    return {
        "rotate_enabled": True, "rotate_angle": 90, "rotate_ranges": "",
        "stamp_enabled": False, "stamp_text": "", "page_numbering": False,
        "stamp_ranges": "", "optimize_enabled": False, "optimize_mode": "lossless",
        "quality": 82, "output_suffix": "-processed",
    }


def test_folder_batch_records_per_file_failures_and_never_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for name in ("a.pdf", "b.pdf", "bad.pdf"):
        (source / name).write_bytes(b"fake pdf")
    existing = output / "a-processed.pdf"
    existing.write_bytes(b"keep this")
    processed: list[str] = []

    def fake_pipeline(input_path, output_path, **kwargs):
        name = Path(input_path).name
        processed.append(name)
        if name == "bad.pdf":
            raise ValueError("simulated malformed PDF")
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)
    progress: list[tuple[int, int, str]] = []
    results = process_pdf_folder(
        source, output, make_profile(),
        progress_callback=lambda done, total, name: progress.append((done, total, name)),
    )
    assert [Path(item.source_path).name for item in results] == ["a.pdf", "b.pdf", "bad.pdf"]
    assert [item.success for item in results] == [True, True, False]
    assert Path(results[0].output_path).name == "a-processed-2.pdf"
    assert existing.read_bytes() == b"keep this"
    assert Path(results[1].output_path).read_bytes() == b"processed"
    assert results[2].output_path == "" and "simulated malformed PDF" in results[2].message
    assert processed == ["a.pdf", "b.pdf", "bad.pdf"]
    assert [entry[0] for entry in progress] == [1, 2, 3] and all(entry[1] == 3 for entry in progress)
    assert not (output / CHECKPOINT_FILENAME).exists()


def test_recursive_batch_preserves_subfolder_layout_and_matches_uppercase_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    (source / "nested").mkdir(parents=True)
    output.mkdir()
    (source / "top.PDF").write_bytes(b"fake")
    (source / "nested" / "inside.pdf").write_bytes(b"fake")

    def fake_pipeline(input_path, output_path, **kwargs):
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)
    results = process_pdf_folder(source, output, make_profile(), recursive=True)
    assert len(results) == 2 and all(result.success for result in results)
    assert (output / "top-processed.pdf").exists()
    assert (output / "nested" / "inside-processed.pdf").exists()


def test_folder_batch_resumes_without_reprocessing_recorded_successes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    (source / "a.pdf").write_bytes(b"fake a")
    (source / "b.pdf").write_bytes(b"fake b")
    processed: list[str] = []

    def fake_pipeline(input_path, output_path, **kwargs):
        processed.append(Path(input_path).name)
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)

    def simulate_interruption(done: int, total: int, name: str) -> None:
        if done == 1:
            raise RuntimeError("simulated interruption after checkpoint")

    with pytest.raises(RuntimeError, match="simulated interruption"):
        process_pdf_folder(
            source, output, make_profile(), resume=True,
            progress_callback=simulate_interruption,
        )
    assert (output / CHECKPOINT_FILENAME).is_file()
    assert processed == ["a.pdf"]

    results = process_pdf_folder(source, output, make_profile(), resume=True)
    assert [Path(result.source_path).name for result in results] == ["a.pdf", "b.pdf"]
    assert all(result.success for result in results)
    assert results[0].message == "Concluído antes da interrupção; resultado reutilizado."
    assert processed == ["a.pdf", "b.pdf"]
    assert not (output / CHECKPOINT_FILENAME).exists()


def test_resume_starts_fresh_when_profile_or_inventory_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    (source / "a.pdf").write_bytes(b"fake a")
    (source / "b.pdf").write_bytes(b"fake b")
    processed: list[str] = []

    def fake_pipeline(input_path, output_path, **kwargs):
        processed.append(Path(input_path).name)
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)

    def simulate_interruption(done: int, total: int, name: str) -> None:
        if done == 1:
            raise RuntimeError("simulated interruption after checkpoint")

    original_profile = make_profile()
    with pytest.raises(RuntimeError, match="simulated interruption"):
        process_pdf_folder(
            source, output, original_profile, resume=True,
            progress_callback=simulate_interruption,
        )

    changed_profile = make_profile()
    changed_profile["output_suffix"] = "-different"
    results = process_pdf_folder(source, output, changed_profile, resume=True)
    assert all(result.success for result in results)
    assert processed == ["a.pdf", "a.pdf", "b.pdf"]
    assert (output / "a-processed.pdf").exists()
    assert (output / "a-different.pdf").exists()


def test_folder_batch_rejects_output_inside_source_and_empty_folder(tmp_path: Path) -> None:
    source = tmp_path / "input"
    source.mkdir()
    (source / "subfolder").mkdir()
    with pytest.raises(ValueError, match="pasta de saída"):
        process_pdf_folder(source, source / "subfolder", make_profile())
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError, match="não contém arquivos PDF"):
        process_pdf_folder(source, output, make_profile())


def test_batch_requires_at_least_one_active_operation(tmp_path: Path) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    (source / "one.pdf").write_bytes(b"fake")
    profile = make_profile()
    profile["rotate_enabled"] = False
    with pytest.raises(ValueError, match="pelo menos uma etapa"):
        process_pdf_folder(source, output, profile)



def test_cancel_preserves_checkpoint_and_resume_skips_completed_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (source / name).write_bytes(name.encode("ascii"))
    processed: list[str] = []

    def fake_pipeline(input_path, output_path, **kwargs):
        processed.append(Path(input_path).name)
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)
    control = BatchControl()

    def request_cancel_after_first(done: int, total: int, name: str) -> None:
        if done == 1:
            control.cancel()

    partial = process_pdf_folder(
        source, output, make_profile(), resume=True, control=control,
        progress_callback=request_cancel_after_first,
    )
    assert len(partial) == 1
    assert partial[0].success
    assert control.was_stopped
    assert (output / CHECKPOINT_FILENAME).is_file()
    assert processed == ["a.pdf"]

    resumed = process_pdf_folder(source, output, make_profile(), resume=True, control=BatchControl())
    assert len(resumed) == 3 and all(item.success for item in resumed)
    assert resumed[0].message == "Concluído antes da interrupção; resultado reutilizado."
    assert processed == ["a.pdf", "b.pdf", "c.pdf"]
    assert not (output / CHECKPOINT_FILENAME).exists()


def test_cancel_releases_a_paused_batch_control() -> None:
    import threading

    control = BatchControl()
    control.pause()
    entered = threading.Event()
    outcome: list[bool] = []

    def wait_for_resume() -> None:
        entered.set()
        outcome.append(control.wait_until_resumed())

    worker = threading.Thread(target=wait_for_resume, daemon=True)
    worker.start()
    assert entered.wait(timeout=2)
    control.cancel()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert outcome == [False]
    assert control.was_stopped is False



def test_reprocess_only_failed_preserves_successes_and_skips_them(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (source / name).write_bytes(name.encode("ascii"))
    calls: list[str] = []
    attempts: dict[str, int] = {}

    def fake_pipeline(input_path, output_path, **kwargs):
        name = Path(input_path).name
        calls.append(name)
        attempts[name] = attempts.get(name, 0) + 1
        if name == "a.pdf" and attempts[name] == 1:
            raise ValueError("first attempt fails")
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)
    original = process_pdf_folder(source, output, make_profile())
    assert [item.success for item in original] == [False, True, True]
    assert calls == ["a.pdf", "b.pdf", "c.pdf"]

    retried = process_pdf_folder(
        source, output, make_profile(),
        only_sources=[original[0].source_path],
        initial_results=original,
        resume=True,
    )
    assert [Path(item.source_path).name for item in retried] == ["a.pdf", "b.pdf", "c.pdf"]
    assert all(item.success for item in retried)
    assert calls == ["a.pdf", "b.pdf", "c.pdf", "a.pdf"]
    assert (output / "b-processed.pdf").read_bytes() == b"processed"


def test_failure_only_retry_checkpoint_resumes_the_same_subset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (source / name).write_bytes(name.encode("ascii"))
    calls: list[str] = []
    attempts: dict[str, int] = {}

    def fake_pipeline(input_path, output_path, **kwargs):
        name = Path(input_path).name
        calls.append(name)
        attempts[name] = attempts.get(name, 0) + 1
        if name in {"a.pdf", "b.pdf"} and attempts[name] == 1:
            raise ValueError("initial failure")
        Path(output_path).write_bytes(b"processed")
        return Path(output_path)

    monkeypatch.setattr(batch, "process_pdf_pipeline", fake_pipeline)
    original = process_pdf_folder(source, output, make_profile())
    assert [item.success for item in original] == [False, False, True]

    control = BatchControl()

    def cancel_after_one(done: int, total: int, name: str) -> None:
        if done == 1:
            control.cancel()

    partial = process_pdf_folder(
        source, output, make_profile(),
        only_sources=[original[0].source_path, original[1].source_path],
        initial_results=original, resume=True, control=control,
        progress_callback=cancel_after_one,
    )
    assert [Path(item.source_path).name for item in partial] == ["a.pdf", "b.pdf", "c.pdf"]
    assert partial[0].success and not partial[1].success and partial[2].success
    assert (output / CHECKPOINT_FILENAME).is_file()
    assert calls == ["a.pdf", "b.pdf", "c.pdf", "a.pdf"]

    resumed = process_pdf_folder(source, output, make_profile(), resume=True)
    assert all(item.success for item in resumed)
    assert calls == ["a.pdf", "b.pdf", "c.pdf", "a.pdf", "b.pdf"]
    assert not (output / CHECKPOINT_FILENAME).exists()

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from document_tools.report_history import (
    MAX_HISTORY_REPORTS,
    delete_batch_report,
    load_batch_history,
    save_batch_report,
)


@dataclass
class FakeResult:
    source_path: str
    success: bool
    output_path: str
    message: str


def save_one(directory: Path, name: str = "one.pdf", **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_directory": "/local/input",
        "output_directory": "/local/output",
        "profile_name": "Profile A",
        "profile": {
            "rotate_enabled": True,
            "rotate_angle": 90,
            "output_suffix": "-processed",
            "password": "must-not-be-stored",
            "source_directory": "/must-not-be-stored",
        },
        "recursive": True,
        "file_mode": 0o600,
        "results": [FakeResult(f"/local/input/{name}", False, "", "Malformed PDF")],
        "cancelled": False,
    }
    values.update(overrides)
    return save_batch_report(directory, **values)  # type: ignore[arg-type]


def test_history_round_trip_keeps_full_results_and_only_known_profile_options(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    result = save_one(
        history_dir,
        results=[
            FakeResult("/local/input/a.pdf", True, "/local/output/a.pdf", "Completed"),
            FakeResult("/local/input/b.pdf", False, "", "Password required"),
        ],
    )

    loaded = load_batch_history(history_dir)
    assert len(loaded) == 1
    assert loaded[0]["id"] == result["id"]
    assert loaded[0]["results"] == result["results"]
    assert len(loaded[0]["results"]) == 2
    assert loaded[0]["profile"] == {
        "rotate_enabled": True,
        "rotate_angle": 90,
        "output_suffix": "-processed",
    }
    assert "password" not in json.dumps(loaded[0])
    assert "/must-not-be-stored" not in json.dumps(loaded[0])


def test_history_retains_only_the_most_recent_fifty_reports(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    ids = [save_one(history_dir, f"{index}.pdf")["id"] for index in range(MAX_HISTORY_REPORTS + 4)]

    loaded = load_batch_history(history_dir)
    assert len(loaded) == MAX_HISTORY_REPORTS
    assert ids[-1] in {report["id"] for report in loaded}
    assert ids[0] not in {report["id"] for report in loaded}


def test_history_skips_corrupt_or_unsupported_reports(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    saved = save_one(history_dir)
    corrupt_path = history_dir / ("batch-report-" + "a" * 32 + ".json")
    corrupt_path.write_text("{not-json", encoding="utf-8")
    unsupported_id = "b" * 32
    unsupported = dict(saved)
    unsupported["id"] = unsupported_id
    unsupported["schema_version"] = 999
    (history_dir / f"batch-report-{unsupported_id}.json").write_text(
        json.dumps(unsupported), encoding="utf-8"
    )

    loaded = load_batch_history(history_dir)
    assert [report["id"] for report in loaded] == [saved["id"]]


def test_history_delete_removes_only_selected_report_and_rejects_invalid_ids(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    first = save_one(history_dir, "first.pdf")
    second = save_one(history_dir, "second.pdf")

    assert delete_batch_report(history_dir, str(first["id"]))
    assert not delete_batch_report(history_dir, str(first["id"]))
    assert [report["id"] for report in load_batch_history(history_dir)] == [second["id"]]
    try:
        delete_batch_report(history_dir, "../../unrelated")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid report identifiers must be rejected.")
