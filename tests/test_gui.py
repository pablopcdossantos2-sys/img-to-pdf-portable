from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtGui import QImage
from pypdf import PdfWriter
from pypdf.errors import PdfReadError
from PySide6.QtWidgets import QApplication, QAbstractItemView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton
from PIL import Image as PILImage

from document_tools.gui import APP_NAME, DocumentToolsWindow, ImageDropList, OperationWorker, PageThumbnailWorker, SideNavigationWidget


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
        english_buttons = [button.text() for button in window.findChildren(QPushButton)]
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
        spanish_buttons = [button.text() for button in window.findChildren(QPushButton)]
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

def test_pipeline_profile_json_export_import_round_trip_excludes_sensitive_data(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    window = DocumentToolsWindow()
    previous_profiles = window.settings.value("pipeline_profiles", None)
    try:
        window.settings.setValue("pipeline_profiles", "{}")
        window.pipeline_path.setText("private-source.pdf")
        window.pipeline_password.setText("do-not-export-this")
        window.pipeline_rotate_enabled.setChecked(True)
        window.pipeline_rotate_angle.setCurrentIndex(window.pipeline_rotate_angle.findData(180))
        window.pipeline_rotate_ranges.setText("2, 4-5")
        window.pipeline_stamp_enabled.setChecked(True)
        window.pipeline_stamp_text.setText("REVIEW")
        window.pipeline_numbering.setChecked(True)
        window.pipeline_stamp_ranges.setText("1-3")
        window.pipeline_optimize_enabled.setChecked(True)
        window.pipeline_optimize_mode.setCurrentIndex(window.pipeline_optimize_mode.findData("balanced"))
        window.pipeline_optimize_quality.setValue(73)
        profile = window._capture_pipeline_profile()
        window.settings.setValue("pipeline_profiles", json.dumps({"Portable review": profile}))

        target = tmp_path / "portable-review.json"
        monkeypatch.setattr(
            "document_tools.gui.QInputDialog.getItem",
            lambda *args, **kwargs: ("Portable review", True),
        )
        monkeypatch.setattr(
            "document_tools.gui.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (str(target), "JSON files (*.json)"),
        )
        window._export_pipeline_profile()
        document = json.loads(target.read_text(encoding="utf-8"))
        assert document == {
            "schema_version": 2,
            "name": "Portable review",
            "profile": profile,
        }
        serialized = target.read_text(encoding="utf-8")
        assert "private-source.pdf" not in serialized
        assert "do-not-export-this" not in serialized

        window.settings.setValue("pipeline_profiles", "{}")
        monkeypatch.setattr(
            "document_tools.gui.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: (str(target), "JSON files (*.json)"),
        )
        window._import_pipeline_profile()
        assert window._read_pipeline_profiles() == {"Portable review": profile}
        assert window.pipeline_password.text() == "do-not-export-this"
    finally:
        if previous_profiles is None:
            window.settings.remove("pipeline_profiles")
        else:
            window.settings.setValue("pipeline_profiles", previous_profiles)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_pipeline_profile_import_rejects_unrecognized_fields(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    window = DocumentToolsWindow()
    previous_profiles = window.settings.value("pipeline_profiles", None)
    try:
        window.settings.setValue("pipeline_profiles", "{}")
        invalid = tmp_path / "invalid-profile.json"
        invalid.write_text(
            json.dumps({
                "schema_version": 1,
                "name": "Injected",
                "profile": {
                    "rotate_enabled": False,
                    "rotate_angle": 90,
                    "rotate_ranges": "",
                    "stamp_enabled": False,
                    "stamp_text": "",
                    "page_numbering": False,
                    "stamp_ranges": "",
                    "optimize_enabled": False,
                    "optimize_mode": "lossless",
                    "quality": 82,
                    "password": "should-not-be-accepted",
                },
            }),
            encoding="utf-8",
        )
        warnings: list[str] = []
        monkeypatch.setattr(
            "document_tools.gui.QFileDialog.getOpenFileName",
            lambda *args, **kwargs: (str(invalid), "JSON files (*.json)"),
        )
        monkeypatch.setattr(
            "document_tools.gui.QMessageBox.warning",
            lambda _parent, _title, message: warnings.append(str(message)),
        )
        window._import_pipeline_profile()
        assert window._read_pipeline_profiles() == {}
        assert warnings
    finally:
        if previous_profiles is None:
            window.settings.remove("pipeline_profiles")
        else:
            window.settings.setValue("pipeline_profiles", previous_profiles)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_external_pdf_errors_have_translatable_user_friendly_messages(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        message = OperationWorker._friendly_error_message(PdfReadError("internal parser diagnostic"))
        assert message == "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar."
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        assert window._t(message) == "The PDF contains an unsupported structure or is damaged. Try saving a fresh copy before processing it."
        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        assert window._t(message) == "El PDF contiene una estructura no compatible o está dañado. Intenta guardar una copia nueva antes de procesarlo."
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()



def test_settings_theme_icon_and_left_navigation(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    previous_theme = window.settings.value("theme", None)
    previous_language = window.language_combo.currentData()
    try:
        assert isinstance(window.tabs, SideNavigationWidget)
        assert not window.windowIcon().isNull()
        assert window.tabs.tabText(window.settings_tab_index) == "Configurações"
        assert window.output_permissions.currentData() in (0o600, 0o644)
        assert window.output_permissions_info.text() == "ⓘ"
        assert window.output_permissions_info.toolTip() == "Sobre permissões de saída"
        assert window.output_permissions_info.accessibleName() == "Sobre permissões de saída"
        assert window.image_margin.value() == 0
        assert window.image_list.acceptDrops()
        labels = {label.text() for label in window.findChildren(QLabel)}
        assert "O que vamos organizar hoje?" not in labels
        assert "Escolha uma ferramenta abaixo. Os arquivos de origem são preservados." not in labels

        dark_index = window.theme_combo.findData("dark")
        assert dark_index >= 0
        window.theme_combo.setCurrentIndex(dark_index)
        assert window._theme == "dark"
        assert window.settings.value("theme") == "dark"
        assert "#111827" in window.styleSheet()

        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        assert window.tabs.tabText(window.settings_tab_index) == "Settings"
        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        assert window.tabs.tabText(window.settings_tab_index) == "Configuración"
    finally:
        if previous_theme is None:
            window.settings.remove("theme")
            window._theme = "light"
            window.setStyleSheet(window._stylesheet("light"))
        else:
            previous_theme_text = str(previous_theme)
            theme_index = window.theme_combo.findData(previous_theme_text)
            if theme_index >= 0:
                window.theme_combo.setCurrentIndex(theme_index)
            window.settings.setValue("theme", previous_theme)
        window.language_combo.setCurrentIndex(window.language_combo.findData(previous_language))
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_image_dpi_is_estimated_after_adding_a_source_image(
    qt_app: QApplication, tmp_path: Path
) -> None:
    image_path = tmp_path / "a4-300dpi.png"
    with PILImage.new("RGB", (2480, 3508), "white") as image:
        image.save(image_path)

    window = DocumentToolsWindow()
    try:
        assert DocumentToolsWindow._add_paths(window.image_list, [str(image_path)]) == 1
        window._update_image_dpi_from_sources()
        assert window.image_dpi.value() == 300
        assert window.image_margin.value() == 0
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_desktop_is_the_default_folder_for_save_dialogs(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        desktop = window._desktop_directory()
        assert desktop.is_dir()
        assert Path(window._default_save_path("sample.pdf")).parent == desktop
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()
