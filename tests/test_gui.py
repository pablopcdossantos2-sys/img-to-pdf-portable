from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtPdf import QPdfDocument
from pypdf import PdfWriter
from PySide6.QtWidgets import QApplication, QAbstractItemView, QLineEdit, QListWidget, QListWidgetItem

from document_tools.gui import APP_NAME, DocumentToolsWindow, PageThumbnailWorker


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
        assert "Batch workflow" in english_tabs
        english_buttons = [button.text() for button in window.findChildren(__import__("PySide6").QtWidgets.QPushButton)]
        assert "Save profile" in english_buttons
        assert "Load profile" in english_buttons
        assert "Delete profile" in english_buttons
        assert window.windowTitle() == "PDF Hub"

        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        spanish_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Reordenar páginas" in spanish_tabs
        assert "Marca de agua y numeración" in spanish_tabs
        assert "Optimizar PDF" in spanish_tabs
        assert "Flujo por lotes" in spanish_tabs
        spanish_buttons = [button.text() for button in window.findChildren(__import__("PySide6").QtWidgets.QPushButton)]
        assert "Guardar perfil" in spanish_buttons
        assert "Cargar perfil" in spanish_buttons
        assert "Eliminar perfil" in spanish_buttons
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_new_pdf_tools_are_available_in_the_interface(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        assert window.reorder_list.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
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

def test_reorder_preview_renders_the_selected_page(qt_app: QApplication, tmp_path) -> None:
    source = tmp_path / "preview.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=240, height=360)
    writer.add_blank_page(width=360, height=240)
    with source.open("wb") as stream:
        writer.write(stream)

    window = DocumentToolsWindow()
    try:
        window.show()
        qt_app.processEvents()
        document = QPdfDocument(window)
        document.load(str(source))
        assert document.pageCount() == 2
        window.reorder_document = document

        # The rows are deliberately in reverse order: preview follows the source page
        # represented by each row, not merely the current row index.
        for page_number in (2, 1):
            item = QListWidgetItem(f"Page {page_number}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            window.reorder_list.addItem(item)

        window.reorder_list.setCurrentRow(0)
        qt_app.processEvents()
        pixmap = window.reorder_preview.pixmap()
        assert pixmap is not None
        assert not pixmap.isNull()
        assert pixmap.width() > pixmap.height()
        assert window.reorder_preview.text() == ""

        window.reorder_list.setCurrentRow(1)
        qt_app.processEvents()
        pixmap = window.reorder_preview.pixmap()
        assert not pixmap.isNull()
        assert pixmap.height() > pixmap.width()
    finally:
        if window.reorder_document is not None:
            window.reorder_document.close()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_stamp_range_field_is_present_and_translatable(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        assert window.stamp_ranges.placeholderText() == "Deixe vazio para aplicar em todas as páginas"
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        assert window.stamp_ranges.placeholderText() == "Leave blank to apply to all pages"
        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        assert window.stamp_ranges.placeholderText() == "Déjalo vacío para aplicar a todas las páginas"
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()

def test_dynamic_page_range_errors_are_translated(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        assert window._t("O intervalo '4-6' precisa estar entre 1 e 3.") == "Range '4-6' must be between 1 and 3."
        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        assert window._t("O intervalo '4-6' precisa estar entre 1 e 3.") == "El intervalo '4-6' debe estar entre 1 y 3."
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()

def test_batch_workflow_controls_follow_selected_steps(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        assert window.pipeline_rotate_angle.isEnabled() is False
        assert window.pipeline_rotate_ranges.isEnabled() is False
        assert window.pipeline_stamp_text.isEnabled() is False
        assert window.pipeline_stamp_ranges.isEnabled() is False
        assert window.pipeline_optimize_mode.isEnabled() is False
        assert window.pipeline_optimize_quality.isEnabled() is False

        window.pipeline_rotate_enabled.setChecked(True)
        assert window.pipeline_rotate_angle.isEnabled() is True
        window.pipeline_stamp_enabled.setChecked(True)
        assert window.pipeline_stamp_text.isEnabled() is True
        assert window.pipeline_stamp_ranges.isEnabled() is True
        window.pipeline_optimize_enabled.setChecked(True)
        assert window.pipeline_optimize_mode.isEnabled() is True
        assert window.pipeline_optimize_quality.isEnabled() is False
        window.pipeline_optimize_mode.setCurrentIndex(window.pipeline_optimize_mode.findData("balanced"))
        assert window.pipeline_optimize_quality.isEnabled() is True
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()

def test_reorder_grid_renders_page_thumbnails(qt_app: QApplication, tmp_path) -> None:
    source = tmp_path / "thumbnails.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=240, height=360)
    writer.add_blank_page(width=360, height=240)
    with source.open("wb") as stream:
        writer.write(stream)

    rendered: list[tuple[int, int, int]] = []
    errors: list[str] = []
    worker = PageThumbnailWorker(str(source))
    worker.thumbnail_ready.connect(
        lambda page, image: rendered.append((page, image.width(), image.height()))
    )
    worker.failed.connect(errors.append)
    worker.run()

    assert errors == []
    assert [item[0] for item in rendered] == [1, 2]
    assert all(width > 0 and height > 0 for _, width, height in rendered)

    window = DocumentToolsWindow()
    try:
        assert window.reorder_list.viewMode() == QListWidget.ViewMode.IconMode
        assert window.reorder_list.iconSize().width() >= 60
        for page_number, width, height in rendered:
            item = QListWidgetItem(f"Page {page_number}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            window.reorder_list.addItem(item)
            window._reorder_items_by_page[page_number] = item
            from PySide6.QtGui import QImage
            image = QImage(width, height, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFFFF)
            window._set_reorder_thumbnail(page_number, image)
            assert not item.icon().isNull()
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_pipeline_profile_saves_loads_and_deletes_options_without_paths_or_passwords(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = DocumentToolsWindow()
    previous_profiles = window.settings.value("pipeline_profiles", None)
    try:
        window.settings.setValue("pipeline_profiles", "{}")
        window.pipeline_path.setText("sensitive-source.pdf")
        window.pipeline_password.setText("must-not-be-saved")
        window.pipeline_rotate_enabled.setChecked(True)
        window.pipeline_rotate_angle.setCurrentIndex(window.pipeline_rotate_angle.findData(270))
        window.pipeline_rotate_ranges.setText("2-4")
        window.pipeline_stamp_enabled.setChecked(True)
        window.pipeline_stamp_text.setText("REVIEW")
        window.pipeline_numbering.setChecked(True)
        window.pipeline_stamp_ranges.setText("1, 3-4")
        window.pipeline_optimize_enabled.setChecked(True)
        window.pipeline_optimize_mode.setCurrentIndex(window.pipeline_optimize_mode.findData("balanced"))
        window.pipeline_optimize_quality.setValue(76)
        expected = window._capture_pipeline_profile()

        monkeypatch.setattr(
            "document_tools.gui.QInputDialog.getText",
            lambda *args, **kwargs: ("Print review", True),
        )
        window._save_pipeline_profile()
        profiles = window._read_pipeline_profiles()
        assert profiles == {"Print review": expected}
        serialized = str(window.settings.value("pipeline_profiles", "{}"))
        assert "sensitive-source.pdf" not in serialized
        assert "must-not-be-saved" not in serialized
        assert "pipeline_password" not in serialized

        window.pipeline_rotate_enabled.setChecked(False)
        window.pipeline_rotate_ranges.clear()
        window.pipeline_stamp_enabled.setChecked(False)
        window.pipeline_stamp_text.clear()
        window.pipeline_numbering.setChecked(False)
        window.pipeline_stamp_ranges.clear()
        window.pipeline_optimize_enabled.setChecked(False)
        window.pipeline_optimize_mode.setCurrentIndex(window.pipeline_optimize_mode.findData("lossless"))
        window.pipeline_optimize_quality.setValue(82)
        window.pipeline_password.clear()

        monkeypatch.setattr(
            "document_tools.gui.QInputDialog.getItem",
            lambda *args, **kwargs: ("Print review", True),
        )
        window._load_pipeline_profile()
        assert window._capture_pipeline_profile() == expected
        assert window.pipeline_password.text() == ""

        from PySide6.QtWidgets import QMessageBox
        monkeypatch.setattr(
            "document_tools.gui.QMessageBox.question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        window._delete_pipeline_profile()
        assert window._read_pipeline_profiles() == {}
    finally:
        if previous_profiles is None:
            window.settings.remove("pipeline_profiles")
        else:
            window.settings.setValue("pipeline_profiles", previous_profiles)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()
