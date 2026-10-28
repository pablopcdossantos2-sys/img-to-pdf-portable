from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from document_tools.report_history import (
    MAX_HISTORY_REPORTS,
    _prune_history,
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
    malformed_id = "c" * 32
    malformed = dict(saved)
    malformed["id"] = malformed_id
    malformed["created_timestamp"] = "not-a-number"
    (history_dir / f"batch-report-{malformed_id}.json").write_text(
        json.dumps(malformed), encoding="utf-8"
    )
    invalid_profile_id = "d" * 32
    invalid_profile = dict(saved)
    invalid_profile["id"] = invalid_profile_id
    invalid_profile["profile"] = {"rotate_enabled": True, "unexpected": ["nested"]}
    (history_dir / f"batch-report-{invalid_profile_id}.json").write_text(
        json.dumps(invalid_profile), encoding="utf-8"
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


def test_history_pruning_uses_report_timestamp_not_filesystem_mtime(
    tmp_path: Path, monkeypatch
) -> None:
    history_dir = tmp_path / "history"
    monkeypatch.setattr("document_tools.report_history._prune_history", lambda _directory: None)
    ids = [str(save_one(history_dir, f"{index}.pdf")["id"]) for index in range(MAX_HISTORY_REPORTS + 1)]
    oldest = history_dir / f"batch-report-{ids[0]}.json"
    newest = history_dir / f"batch-report-{ids[-1]}.json"

    now = time.time()
    os.utime(oldest, (now, now))
    os.utime(newest, (now - 100_000, now - 100_000))
    _prune_history(history_dir)

    assert not oldest.exists()
    assert newest.exists()



def test_save_report_with_surrogate_path(tmp_path: Path, monkeypatch) -> None:
    if os.name == "nt":
        return
    legacy_path = os.fsdecode(bytes([47, 108, 101, 103, 97, 99, 121, 47, 97, 0xE7, 46, 112, 100, 102]))
    saved = save_one(
        tmp_path / "history",
        results=[FakeResult(legacy_path, False, "", "Malformed PDF")],
    )
    history_file = tmp_path / "history" / f"batch-report-{saved['id']}.json"
    assert chr(92) + "udce7" in history_file.read_text(encoding="utf-8")
    loaded = load_batch_history(tmp_path / "history")
    assert loaded[0]["results"][0]["source_path"] == legacy_path


def test_deeply_nested_report_is_ignored_and_does_not_block_saving(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    valid = save_one(history_dir, "valid.pdf")
    corrupt_id = "e" * 32
    corrupt = history_dir / f"batch-report-{corrupt_id}.json"
    corrupt.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")

    loaded = load_batch_history(history_dir)
    assert [report["id"] for report in loaded] == [valid["id"]]
    second = save_one(history_dir, "second.pdf")
    assert second["id"] != valid["id"]
    assert len(load_batch_history(history_dir)) == 2
