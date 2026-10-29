from __future__ import annotations

import sys
from pathlib import Path

import main


def test_selftest_exception_returns_nonzero_and_writes_log(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "argv", ["PDFHub", "--selftest"])
    monkeypatch.setattr(main.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        main,
        "selftest",
        lambda: (_ for _ in ()).throw(RuntimeError("intentional selftest failure")),
    )
    assert main.main() == 1
    log = tmp_path / "pdf-hub-selftest.log"
    assert log.is_file()
    assert "intentional selftest failure" in log.read_text(encoding="utf-8")
