from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_pdf_hub_user_state(tmp_path_factory: pytest.TempPathFactory):
    """Keep GUI tests away from the actual user's settings and batch reports."""
    root = tmp_path_factory.mktemp("pdf-hub-user-state")
    config = root / "config"
    data = root / "data"
    config.mkdir()
    data.mkdir()
    os.environ["HOME"] = str(root)
    os.environ["XDG_CONFIG_HOME"] = str(config)
    os.environ["XDG_DATA_HOME"] = str(data)
    os.environ["APPDATA"] = str(config)
    os.environ["LOCALAPPDATA"] = str(data)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QSettings

    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(config))
    yield root
