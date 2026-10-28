from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSize, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtGui import QImage
from pypdf import PdfWriter
from pypdf.errors import PdfReadError
from PySide6.QtWidgets import QApplication, QAbstractItemView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea
from PIL import Image as PILImage

from document_tools.gui import APP_NAME, DocumentToolsWindow, ImageDropList, OperationWorker, PageThumbnailWorker, SideNavigationWidget
from document_tools.pdf_rendering import export_pdf_pages_to_images


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
        assert "Delete pages" in english_tabs
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
        assert "Eliminar páginas" in spanish_tabs
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
        assert window.reorder_list.dragDropMode() == QAbstractItemView.DragDropMode.DragDrop
        assert window.reorder_list.movement() == QListWidget.Movement.Static
        assert window.stamp_numbering.isChecked() is False
        assert window.optimize_mode.currentData() == "balanced"
        assert window.optimize_quality.isEnabled() is True
        window.optimize_mode.setCurrentIndex(window.optimize_mode.findData("lossless"))
        assert window.optimize_quality.isEnabled() is False
        window.optimize_mode.setCurrentIndex(window.optimize_mode.findData("balanced"))
        assert window.optimize_quality.isEnabled() is True
        assert window.split_mode.currentData() == "each_page"
        assert window.split_pages_per_file.isHidden()
        window.split_mode.setCurrentIndex(window.split_mode.findData("every_n_pages"))
        assert not window.split_pages_per_file.isHidden()
        window.split_mode.setCurrentIndex(window.split_mode.findData("after_pages"))
        assert not window.split_after_pages.isHidden()
        window.split_mode.setCurrentIndex(window.split_mode.findData("by_size"))
        assert not window.split_target_mb.isHidden()
        window.split_mode.setCurrentIndex(window.split_mode.findData("by_bookmarks"))
        assert not window.split_bookmark_level.isHidden()
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()

def test_reorder_titles_are_below_thumbnails_and_layout_is_stable(qt_app: QApplication) -> None:
    from PySide6.QtWidgets import QStyleOptionViewItem
    from document_tools.gui import ReorderPageDelegate

    window = DocumentToolsWindow()
    try:
        delegate = window.reorder_list.itemDelegate()
        assert isinstance(delegate, ReorderPageDelegate)
        option = QStyleOptionViewItem()
        delegate.initStyleOption(option, window.reorder_list.model().index(0, 0))
        assert option.decorationPosition == QStyleOptionViewItem.Position.Top
        assert window.reorder_list.layoutMode() == QListWidget.LayoutMode.SinglePass
        assert window.reorder_list.resizeMode() == QListWidget.ResizeMode.Fixed
        assert window.reorder_list.dragDropMode() == QAbstractItemView.DragDropMode.DragDrop

        window.theme_combo.setCurrentIndex(window.theme_combo.findData("light"))
        icon = window.tabs._reorder_pages_button.icon()
        assert not icon.isNull()
        light_pixmap = icon.pixmap(QSize(24, 24))
        assert not light_pixmap.isNull()

        window.theme_combo.setCurrentIndex(window.theme_combo.findData("dark"))
        dark_pixmap = window.tabs._reorder_pages_button.icon().pixmap(QSize(24, 24))
        assert not dark_pixmap.isNull()
        assert light_pixmap.toImage().pixelColor(10, 12) != dark_pixmap.toImage().pixelColor(10, 12)
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_reorder_multiple_moves_keep_every_page(qt_app: QApplication) -> None:
    from document_tools.gui import ReorderablePageList

    widget = ReorderablePageList()
    try:
        for page_number in range(1, 7):
            item = QListWidgetItem(f"Página {page_number:02d}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            widget.addItem(item)

        widget.move_page_to_row(0, 4)
        widget.move_page_to_row(5, 1)
        widget.move_page_to_row(2, 0)

        assert widget.count() == 6
        assert sorted(
            widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(widget.count())
        ) == list(range(1, 7))
    finally:
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_reorder_grid_moves_the_actual_item_row(qt_app: QApplication) -> None:
    from document_tools.gui import ReorderablePageList
    widget = ReorderablePageList()
    try:
        for page_number in range(1, 5):
            item = QListWidgetItem(f"Página {page_number}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            widget.addItem(item)
        widget.move_page_to_row(0, 2)
        assert [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())] == [2, 3, 1, 4]
    finally:
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_reorder_grid_accepts_internal_drag_and_moves_the_dropped_page(qt_app: QApplication) -> None:
    from PySide6.QtCore import QSize
    from document_tools.gui import ReorderablePageList

    class FakePosition:
        def __init__(self, point) -> None:
            self._point = point

        def toPoint(self):
            return self._point

    class FakeDragEvent:
        def __init__(self, source, point=None) -> None:
            self._source = source
            self._position = FakePosition(point)
            self.accepted = False
            self.ignored = False
            self.action = None

        def source(self):
            return self._source

        def position(self):
            return self._position

        def acceptProposedAction(self):
            self.accepted = True

        def setDropAction(self, action):
            self.action = action

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.ignored = True

    widget = ReorderablePageList()
    try:
        widget.setViewMode(QListWidget.ViewMode.IconMode)
        widget.setIconSize(QSize(76, 96))
        widget.setGridSize(QSize(112, 132))
        widget.resize(420, 180)
        for page_number in (1, 2, 3):
            item = QListWidgetItem(f"Page {page_number}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            widget.addItem(item)
        widget.show()
        qt_app.processEvents()

        source_item = widget.item(0)
        target_item = widget.item(2)
        widget.setCurrentItem(source_item)
        enter_event = FakeDragEvent(widget)
        widget.dragEnterEvent(enter_event)
        assert enter_event.accepted and not enter_event.ignored
        move_event = FakeDragEvent(widget)
        widget.dragMoveEvent(move_event)
        assert move_event.accepted and not move_event.ignored

        target_point = widget.visualItemRect(target_item).center()
        drop_event = FakeDragEvent(widget, target_point)
        widget._dragged_item = source_item
        widget.dropEvent(drop_event)
        widget._dragged_item = None

        assert drop_event.accepted and not drop_event.ignored
        assert drop_event.action == Qt.DropAction.MoveAction
        assert [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())] == [2, 3, 1]
        assert widget.currentItem() is source_item
    finally:
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_pdf_pages_export_to_selected_png_pages_and_never_overwrite(
    qt_app: QApplication, tmp_path: Path
) -> None:
    source = tmp_path / "export.pdf"
    output = tmp_path / "images"
    output.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=144)
    writer.add_blank_page(width=144, height=72)
    with source.open("wb") as stream:
        writer.write(stream)

    exported = export_pdf_pages_to_images(
        source, output, image_format="PNG", dpi=72, pages="2"
    )
    assert len(exported) == 1
    assert exported[0].name == "export-pagina-002.png"
    with PILImage.open(exported[0]) as image:
        assert image.size == (144, 72)
        assert image.format == "PNG"

    rerun = export_pdf_pages_to_images(
        source, output, image_format="PNG", dpi=72, pages="2"
    )
    assert rerun[0].name == "export-pagina-002-2.png"
    assert exported[0].read_bytes() == (output / "export-pagina-002.png").read_bytes()

    jpeg = export_pdf_pages_to_images(
        source, output, image_format="JPEG", dpi=72, quality=80, pages="1"
    )
    with PILImage.open(jpeg[0]) as image:
        assert image.size == (72, 144)
        assert image.format == "JPEG"


def test_pdf_to_images_tab_is_available_and_translated(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        labels = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "PDF para imagens" in labels
        assert window.pdf_to_images_quality.isEnabled() is False
        window.pdf_to_images_format.setCurrentIndex(window.pdf_to_images_format.findData("JPEG"))
        assert window.pdf_to_images_quality.isEnabled() is True
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        labels = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "PDF to images" in labels
        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        labels = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "PDF a imágenes" in labels
    finally:
        window.language_combo.setCurrentIndex(window.language_combo.findData("pt"))
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



def test_stylesheet_preserves_complete_palette_tokens_and_thumbnail_tiles(qt_app: QApplication) -> None:
    for theme in ("light", "dark"):
        stylesheet = DocumentToolsWindow._stylesheet(theme)
        # No template tokens should leak into Qt stylesheets: partial substitutions
        # used to create invalid colors such as "#0B1220_MUTED".
        assert "$" not in stylesheet
        assert "#172B4D_TEXT" not in stylesheet
        assert "#0B1220_MUTED" not in stylesheet
        assert "#263755_TEXT" not in stylesheet
        assert "QLabel#appTitle { color: #FFFFFF;" in stylesheet
        assert "QLabel#subtitle { color:" in stylesheet
        assert "QListWidget#reorderPageList::item" in stylesheet
        assert "background: #FFFFFF; color:" in stylesheet
        assert "QLabel#pagePreview" in stylesheet


def test_settings_theme_icon_and_left_navigation(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    previous_theme = window.settings.value("theme", None)
    previous_language = window.language_combo.currentData()
    try:
        assert isinstance(window.tabs, SideNavigationWidget)
        assert window.tabs.count() == len(window.tabs._buttons)
        assert all(not button.icon().isNull() for button in window.tabs._buttons)
        pt_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Excluir páginas" in pt_tabs
        assert window.delete_pages_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.tabs.sidebar.minimumWidth() >= 276
        navigation_scroll = window.tabs.findChild(QScrollArea, "navigationScroll")
        assert navigation_scroll is not None
        assert navigation_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert window.reorder_list.objectName() == "reorderPageList"
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

        # The DPI estimate is an initial value, not a lock: manual choices remain intact.
        window.image_dpi.setValue(180)
        window.image_margin.setValue(10)
        assert window.image_dpi.value() == 180
        window.image_list.item(0).setSelected(True)
        window._remove_image_inputs()
        assert window.image_dpi.value() == 150
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


def test_reorder_custom_drag_does_not_remove_the_dropped_page(
    qt_app: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    import document_tools.gui as gui
    from PySide6.QtCore import QSize

    class FakePosition:
        def __init__(self, point) -> None:
            self._point = point

        def toPoint(self):
            return self._point

    class FakeDropEvent:
        def __init__(self, source, point) -> None:
            self._source = source
            self._position = FakePosition(point)
            self.accepted = False
            self.action = None

        def source(self):
            return self._source

        def position(self):
            return self._position

        def setDropAction(self, action):
            self.action = action

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.accepted = False

    class FakeDrag:
        def __init__(self, source) -> None:
            self.source = source

        def setMimeData(self, _mime_data) -> None:
            pass

        def setPixmap(self, _pixmap) -> None:
            pass

        def setHotSpot(self, _point) -> None:
            pass

        def exec(self, _actions, _default_action):
            target_point = self.source.visualItemRect(self.source.item(2)).center()
            event = FakeDropEvent(self.source, target_point)
            self.source.dropEvent(event)
            assert event.accepted
            assert event.action == Qt.DropAction.MoveAction
            return Qt.DropAction.MoveAction

    widget = gui.ReorderablePageList()
    try:
        widget.setViewMode(QListWidget.ViewMode.IconMode)
        widget.setIconSize(QSize(76, 96))
        widget.setGridSize(QSize(124, 164))
        widget.resize(420, 180)
        for page_number in (1, 2, 3):
            item = QListWidgetItem(f"Página {page_number}")
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            widget.addItem(item)
        widget.show()
        qt_app.processEvents()
        monkeypatch.setattr(gui, "QDrag", FakeDrag)

        widget.setCurrentRow(0)
        widget.startDrag(Qt.DropAction.MoveAction)

        assert widget.count() == 3
        assert [widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())] == [2, 3, 1]
        assert widget.currentItem() is not None
        assert widget.currentItem().data(Qt.ItemDataRole.UserRole) == 1
    finally:
        widget.close()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_application_starts_the_window_maximized(qt_app: QApplication, monkeypatch: pytest.MonkeyPatch) -> None:
    import document_tools.gui as gui

    calls = {"maximized": False}

    class FakeApplication:
        def __init__(self, _args) -> None:
            pass

        def setApplicationName(self, _name) -> None:
            pass

        def setOrganizationName(self, _name) -> None:
            pass

        def setWindowIcon(self, _icon) -> None:
            pass

        def setFont(self, _font) -> None:
            pass

        def exec(self) -> int:
            return 0

    class FakeWindow:
        def showMaximized(self) -> None:
            calls["maximized"] = True

    monkeypatch.setattr(gui, "QApplication", FakeApplication)
    monkeypatch.setattr(gui, "DocumentToolsWindow", FakeWindow)

    assert gui.main() == 0
    assert calls["maximized"]


def test_window_preserves_space_for_controls_and_aligned_file_pickers(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        screen = qt_app.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            assert window.minimumWidth() == min(1120, available.width())
            assert window.minimumHeight() == min(700, available.height())

        content_areas = window.findChildren(QScrollArea, "contentScrollArea")
        assert content_areas
        assert all(
            area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            for area in content_areas
        )

        assert window.reorder_list.gridSize().height() >= 160
        assert window.reorder_list.wordWrap()

        path_fields = (
            "extract_path",
            "delete_pages_path",
            "rotate_path",
            "split_path",
            "split_directory",
            "reorder_path",
            "stamp_path",
            "optimize_path",
            "pipeline_path",
            "batch_source_directory",
            "batch_output_directory",
            "pdf_to_images_path",
            "pdf_to_images_directory",
            "convert_directory",
        )
        for field_name in path_fields:
            field = getattr(window, field_name)
            row_layout = field.parentWidget().layout()
            assert row_layout is not None, field_name
            margins = row_layout.contentsMargins()
            assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0), field_name
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_pdfsam_mix_and_repeated_insert_tools_are_available_and_translated(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    previous_language = window.language_combo.currentData()
    try:
        pt_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Misturar PDFs" in pt_tabs
        assert "Inserir páginas" in pt_tabs
        assert window.mix_first_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.mix_second_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.insert_target_password.echoMode() == QLineEdit.EchoMode.Password
        assert window.insert_source_password.echoMode() == QLineEdit.EchoMode.Password

        for field_name in (
            "mix_first_path",
            "mix_second_path",
            "insert_target_path",
            "insert_source_path",
        ):
            field = getattr(window, field_name)
            row_layout = field.parentWidget().layout()
            assert row_layout is not None, field_name
            margins = row_layout.contentsMargins()
            assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0)

        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        en_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Mix PDFs" in en_tabs
        assert "Insert pages" in en_tabs

        window.language_combo.setCurrentIndex(window.language_combo.findData("es"))
        es_tabs = [window.tabs.tabText(i).strip() for i in range(window.tabs.count())]
        assert "Mezclar PDF" in es_tabs
        assert "Insertar páginas" in es_tabs
    finally:
        previous_index = window.language_combo.findData(previous_language)
        if previous_index >= 0:
            window.language_combo.setCurrentIndex(previous_index)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_merge_page_ranges_are_saved_per_input_and_copied_when_duplicating(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    try:
        for name in ("first.pdf", "second.pdf"):
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            window.pdf_list.addItem(item)

        window.pdf_list.setCurrentRow(0)
        assert window.merge_page_ranges.isEnabled()
        window._save_merge_selected_range("2-")
        window.pdf_list.setCurrentRow(1)
        window._save_merge_selected_range("1, 3")
        window.pdf_list.setCurrentRow(0)
        assert window.merge_page_ranges.text() == "2-"
        assert window.pdf_list.currentItem().data(Qt.ItemDataRole.UserRole + 1) == "2-"

        window.pdf_list.item(0).setSelected(True)
        DocumentToolsWindow._duplicate_selected(window.pdf_list)
        duplicate = window.pdf_list.item(1)
        assert duplicate.data(Qt.ItemDataRole.UserRole + 1) == "2-"
    finally:
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()


def test_saving_pipeline_profiles_preserves_future_schema_entries(qt_app: QApplication) -> None:
    window = DocumentToolsWindow()
    previous_profiles = window.settings.value("pipeline_profiles", None)
    future_profile = {"schema_version": 999, "future_option": {"enabled": True}}
    try:
        window.settings.setValue("pipeline_profiles", json.dumps({"Future profile": future_profile}))
        assert window._write_pipeline_profiles({"New profile": {"rotate_enabled": False}})
        persisted = json.loads(window.settings.value("pipeline_profiles", "{}"))
        assert persisted["Future profile"] == future_profile
        assert persisted["New profile"] == {"rotate_enabled": False}

        window.settings.setValue("pipeline_profiles", "invalid json")
        assert not window._write_pipeline_profiles({"Another profile": {"rotate_enabled": True}})
        assert window.settings.value("pipeline_profiles") == "invalid json"
    finally:
        if previous_profiles is None:
            window.settings.remove("pipeline_profiles")
        else:
            window.settings.setValue("pipeline_profiles", previous_profiles)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        qt_app.processEvents()
