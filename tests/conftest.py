from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="pdf-hub-test-user-state-"))
_CONFIG_ROOT = _TEST_ROOT / "config"
_DATA_ROOT = _TEST_ROOT / "data"
_CONFIG_ROOT.mkdir()
_DATA_ROOT.mkdir()

# Configure paths before pytest imports tests that load Qt or QStandardPaths.
os.environ["HOME"] = str(_TEST_ROOT)
os.environ["XDG_CONFIG_HOME"] = str(_CONFIG_ROOT)
os.environ["XDG_DATA_HOME"] = str(_DATA_ROOT)
os.environ["APPDATA"] = str(_CONFIG_ROOT)
os.environ["LOCALAPPDATA"] = str(_DATA_ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(_CONFIG_ROOT))


@atexit.register
def _cleanup_test_state() -> None:
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def isolated_user_state() -> Path:
    return _TEST_ROOT
