from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

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
from PySide6.QtCore import QSettings

QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(_CONFIG_ROOT))

# On Windows, QSettings("organization", "application") selects the registry
# explicitly and ignores setDefaultFormat(). Redirect only the application's
# constructor during tests so real HKCU preferences can never be read or changed.
from document_tools import gui as _gui_module
from PySide6.QtCore import QStandardPaths as _QStandardPaths

_DATA_ROOT.mkdir(exist_ok=True)
(_DATA_ROOT / "appdata").mkdir(exist_ok=True)
(_CONFIG_ROOT / "appconfig").mkdir(exist_ok=True)

_QSettings = QSettings


class _IsolatedStandardPaths:
    StandardLocation = _QStandardPaths.StandardLocation

    @staticmethod
    def writableLocation(location):
        if location == _QStandardPaths.StandardLocation.AppDataLocation:
            return str(_DATA_ROOT / "appdata")
        if location == _QStandardPaths.StandardLocation.AppConfigLocation:
            return str(_CONFIG_ROOT / "appconfig")
        return _QStandardPaths.writableLocation(location)


def _isolated_qsettings(*args, **kwargs):
    if len(args) == 2 and args == ("PDFHub", "PDF Hub") and not kwargs:
        return _QSettings(
            _QSettings.Format.IniFormat,
            _QSettings.Scope.UserScope,
            "PDFHub",
            "PDF Hub",
        )
    return _QSettings(*args, **kwargs)


_gui_module.QSettings = _isolated_qsettings
_gui_module.QStandardPaths = _IsolatedStandardPaths


@atexit.register
def _cleanup_test_state() -> None:
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session")
def isolated_user_state() -> Path:
    return _TEST_ROOT
