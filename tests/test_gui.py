from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLineEdit, QListWidget, QListWidgetItem

from document_tools.gui import APP_NAME, DocumentToolsWindow


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make_list(*, selected: tuple[int, ...] = ()) -> QListWidget:
    widget = QListWidget()
    widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    for name in ("a", "b", "c", "d", "e"):
        widget.addItem(QListWidgetItem(name))
    for index in selected:
        widget.item(index).setSelected(True)
    return widget


def names(widget: QListWidget) -> list[str]:
    return [widget.item(index).text() for index in range(widget.count())]


def selected_names(widget: QListWidget) -> list[str]:
    return [
        widget.item(index).text()
        for index in range(widget.count())
        if widget.item(index).isSelected()
    ]


def test_move_selected_up_does_not_reorder_block_at_top(qt_app: QApplication) -> None:
    widget = make_list(selected=(0, 1))

    DocumentToolsWindow._move_selected(widget, -1)

    assert names(widget) == ["a", "b", "c", "d", "e"]
    assert selected_names(widget) == ["a", "b"]


def test_move_selected_up_preserves_contiguous_block_order(qt_app: QApplication) -> None:
    widget = make_list(selected=(1, 2))

    DocumentToolsWindow._move_selected(widget, -1)

    assert names(widget) == ["b", "c", "a", "d", "e"]
    assert selected_names(widget) == ["b", "c"]


def test_move_selected_down_does_not_reorder_block_at_bottom(qt_app: QApplication) -> None:
    widget = make_list(selected=(3, 4))

    DocumentToolsWindow._move_selected(widget, 1)

    assert names(widget) == ["a", "b", "c", "d", "e"]
    assert selected_names(widget) == ["d", "e"]


def test_move_selected_down_preserves_contiguous_block_order(qt_app: QApplication) -> None:
    widget = make_list(selected=(1, 2))

    DocumentToolsWindow._move_selected(widget, 1)

    assert names(widget) == ["a", "d", "b", "c", "e"]
    assert selected_names(widget) == ["b", "c"]


def test_window_is_branded_pdf_hub_and_exposes_password_fields(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        assert APP_NAME == "PDF Hub"
        assert window.windowTitle() == "PDF Hub"
        assert window.extract_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.rotate_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.split_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.image_all_frames.isChecked()
        assert window.output_permissions.currentData() in (0o600, 0o644)
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()

def test_language_selector_translates_tabs_into_english_and_spanish(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        english_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Reorder pages" in english_tabs
        assert "Watermark and page numbers" in english_tabs
        assert "Optimize PDF" in english_tabs
        assert window.windowTitle() == "PDF Hub"

        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        spanish_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Reordenar páginas" in spanish_tabs
        assert "Marca de agua y numeración" in spanish_tabs
        assert "Optimizar PDF" in spanish_tabs
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_new_pdf_tools_are_available_in_the_interface(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        assert window.reorder_list.dragDropMode() == window.reorder_list.DragDropMode.InternalMove
        assert window.stamp_numbering.isChecked() is False
        assert window.optimize_mode.currentData() == "lossless"
        assert window.optimize_quality.isEnabled() is False
        window.optimize_mode.setCurrentIndex(window.optimize_mode.findData("balanced"))
        assert window.optimize_quality.isEnabled() is True
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()
