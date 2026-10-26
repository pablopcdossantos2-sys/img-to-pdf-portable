"""PySide6 desktop interface for the local PDF and image toolkit."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from document_tools import __version__
from document_tools.pdf_ops import (
    convert_image,
    extract_pages,
    images_to_pdf,
    merge_pdfs,
    rotate_pdf,
    split_pdf,
)


APP_NAME = "Ferramentas de Arquivo"
IMAGE_FILTER = "Imagens (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff)"
PDF_FILTER = "Documentos PDF (*.pdf)"
FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tif",
}


class OperationWorker(QThread):
    """Run a document operation without blocking the GUI event loop."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, task: Callable[[], str]) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            self.succeeded.emit(self._task())
        except Exception as error:  # The GUI translates common file and format failures.
            self.failed.emit(self._friendly_error_message(error))

    @staticmethod
    def _friendly_error_message(error: Exception) -> str:
        if isinstance(error, PermissionError):
            return "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas."
        if isinstance(error, FileNotFoundError):
            return "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente."
        if isinstance(error, FileExistsError):
            return f"Um arquivo de destino já existe. Escolha outra pasta ou nome. Detalhe: {error}"
        error_type = error.__class__.__name__
        if error_type in {"UnidentifiedImageError", "DecompressionBombError"}:
            return "A imagem é inválida, muito grande para processar com segurança ou usa um formato não suportado."
        if error_type in {"PdfReadError", "PdfStreamError", "WrongPasswordError"}:
            return "Não foi possível interpretar o PDF. Ele pode estar danificado ou protegido por senha."
        return str(error) or error_type


class DocumentToolsWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(920, 650)
        self.resize(1160, 810)
        self._worker: OperationWorker | None = None
        self._pending_output_directory: Path | None = None
        self._split_custom_directory = False

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(28, 22, 28, 18)
        central_layout.setSpacing(16)

        header = QFrame()
        header.setObjectName("headerCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(14)

        brand_mark = QLabel("F")
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(48, 48)
        header_layout.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel(f"PDF e imagens • v{__version__} • organizado, seguro e local")
        subtitle.setObjectName("subtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        header_layout.addLayout(brand_text, 1)

        local_badge = QLabel("●  PROCESSAMENTO LOCAL")
        local_badge.setObjectName("localBadge")
        local_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(local_badge)
        central_layout.addWidget(header)

        page_title = QLabel("O que vamos organizar hoje?")
        page_title.setObjectName("pageTitle")
        central_layout.addWidget(page_title)

        intro = QLabel(
            "Escolha uma ferramenta abaixo. Os arquivos de origem são preservados."
        )
        intro.setObjectName("intro")
        central_layout.addWidget(intro)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_image_pdf_tab(), "  Imagens para PDF  ")
        self.tabs.addTab(self._build_merge_tab(), "  Unir PDFs  ")
        self.tabs.addTab(self._build_extract_tab(), "  Extrair páginas  ")
        self.tabs.addTab(self._build_rotate_tab(), "  Girar páginas  ")
        self.tabs.addTab(self._build_split_tab(), "  Dividir PDF  ")
        self.tabs.addTab(self._build_convert_tab(), "  Converter imagens  ")
        central_layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel("Pronto. Selecione uma operação acima.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label, 1)
        self.open_directory_button = QPushButton("Abrir pasta")
        self.open_directory_button.setObjectName("secondaryButton")
        self.open_directory_button.hide()
        self.open_directory_button.clicked.connect(self._open_output_directory)
        footer.addWidget(self.open_directory_button)
        self.progress = QProgressBar()
        self.progress.setObjectName("progress")
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(140)
        self.progress.hide()
        footer.addWidget(self.progress)
        central_layout.addLayout(footer)

        self.setCentralWidget(central)
        self.setStyleSheet(self._stylesheet())

    @staticmethod
    def _stylesheet() -> str:
        return """
        QMainWindow {
            background: #F3F6FB;
        }
        QWidget {
            color: #172B4D;
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 13px;
        }
        QLabel {
            background: transparent;
        }
        QFrame#headerCard {
            background: #172B4D;
            border: none;
            border-radius: 16px;
        }
        QLabel#brandMark {
            background: #4263EB;
            color: white;
            font-size: 25px;
            font-weight: 800;
            border-radius: 13px;
        }
        QLabel#appTitle {
            color: #FFFFFF;
            font-size: 20px;
            font-weight: 700;
        }
        QLabel#subtitle {
            color: #C8D5E8;
            font-size: 12px;
        }
        QLabel#localBadge {
            background: #223B60;
            color: #D9FBE9;
            padding: 9px 12px;
            border-radius: 14px;
            font-size: 10px;
            font-weight: 700;
        }
        QLabel#pageTitle {
            color: #172B4D;
            font-size: 24px;
            font-weight: 700;
        }
        QLabel#intro, QLabel#muted {
            color: #718096;
        }
        QTabWidget::pane {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 13px;
            top: -1px;
        }
        QTabBar::tab {
            background: transparent;
            color: #64748B;
            border: none;
            padding: 12px 12px;
            margin-right: 3px;
            font-weight: 600;
        }
        QTabBar::tab:selected {
            background: #E8EEFF;
            color: #3346A8;
            border-radius: 8px;
        }
        QTabBar::tab:hover:!selected {
            background: #EAF0F8;
            border-radius: 8px;
        }
        QLabel#sectionTitle {
            color: #172B4D;
            font-size: 17px;
            font-weight: 700;
        }
        QListWidget {
            background: #FFFFFF;
            color: #24344D;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 6px;
            outline: none;
        }
        QListWidget::item {
            background: transparent;
            padding: 8px 10px;
            margin: 2px 0;
            border-radius: 7px;
        }
        QListWidget::item:selected {
            background: #E8EEFF;
            color: #263E9C;
        }
        QListWidget::item:hover:!selected {
            background: #F3F6FB;
        }
        QPushButton {
            background: #F1F4F9;
            color: #344054;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 13px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #E6ECF5;
            border-color: #C9D4E5;
        }
        QPushButton:pressed { background: #DCE5F3; }
        QPushButton:disabled { color: #9AA7B9; background: #F4F6F9; }
        QPushButton#primaryButton {
            background: #4263EB;
            color: white;
            border-color: #4263EB;
            padding: 12px 18px;
            font-weight: 700;
        }
        QPushButton#primaryButton:hover {
            background: #3354DD;
            border-color: #3354DD;
        }
        QPushButton#secondaryButton {
            background: #EEF2FF;
            color: #3346A8;
            border-color: #E0E7FF;
        }
        QLineEdit, QComboBox, QSpinBox {
            background: white;
            color: #24344D;
            border: 1px solid #D8E0EC;
            border-radius: 8px;
            padding: 9px 10px;
            min-height: 18px;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
            border-color: #7C92F3;
        }
        QLabel#statusLabel {
            color: #58677D;
            font-size: 12px;
        }
        QProgressBar {
            border: none;
            background: #E3EAF4;
            border-radius: 4px;
            height: 7px;
        }
        QProgressBar::chunk {
            background: #4263EB;
            border-radius: 4px;
        }
        """

    def _new_page(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(13)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        description_label = QLabel(description)
        description_label.setObjectName("muted")
        description_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(description_label)
        return page, layout

    @staticmethod
    def _new_list(*, extended: bool = False) -> QListWidget:
        widget = QListWidget()
        widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
            if extended
            else QListWidget.SelectionMode.SingleSelection
        )
        widget.setAlternatingRowColors(False)
        widget.setDragEnabled(True)
        widget.setAcceptDrops(True)
        widget.setDropIndicatorShown(True)
        widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        return widget

    @staticmethod
    def _add_paths(list_widget: QListWidget, paths: list[str]) -> int:
        known = {
            str(Path(list_widget.item(index).data(Qt.ItemDataRole.UserRole)).resolve()).casefold()
            for index in range(list_widget.count())
        }
        added = 0
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            if not path.is_file() or str(path.resolve()).casefold() in known:
                continue
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path.resolve()))
            item.setData(Qt.ItemDataRole.UserRole, str(path.resolve()))
            list_widget.addItem(item)
            known.add(str(path.resolve()).casefold())
            added += 1
        return added

    @staticmethod
    def _all_paths(list_widget: QListWidget) -> list[str]:
        return [
            str(list_widget.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(list_widget.count())
        ]

    def _choose_multiple(self, title: str, file_filter: str) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(self, title, "", file_filter)
        return paths

    def _choose_pdf(self, title: str = "Escolher PDF") -> str | None:
        path, _ = QFileDialog.getOpenFileName(self, title, "", PDF_FILTER)
        return path or None

    def _choose_output_pdf(
        self,
        suggested_name: str,
        *,
        source_paths: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        dialog = QFileDialog(self, "Salvar PDF resultante", suggested_name, PDF_FILTER)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setDefaultSuffix("pdf")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
        if dialog.exec() != QFileDialog.DialogCode.Accepted or not dialog.selectedFiles():
            return None

        output = Path(dialog.selectedFiles()[0]).expanduser()
        if output.suffix.lower() != ".pdf":
            output = output.with_suffix(".pdf")
        output = output.resolve()
        sources = {Path(item).expanduser().resolve() for item in source_paths}
        if output in sources:
            QMessageBox.warning(
                self,
                "Escolha outro nome",
                "O arquivo de saída não pode substituir um dos arquivos de origem.",
            )
            return None

        if output.exists():
            answer = QMessageBox.question(
                self,
                "Confirmar substituição",
                f"O arquivo “{output.name}” já existe. Deseja substituí-lo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.status_label.setText("Operação cancelada. O arquivo existente foi preservado.")
                return None
        return str(output)

    def _choose_directory(self, title: str) -> str | None:
        path = QFileDialog.getExistingDirectory(self, title)
        return path or None

    def _run_task(
        self,
        description: str,
        task: Callable[[], str],
        *,
        output_location: str | Path | None = None,
    ) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.status_label.setText(description)
        self.open_directory_button.hide()
        self.progress.show()
        self.tabs.setEnabled(False)
        if output_location is None:
            self._pending_output_directory = None
        else:
            location = Path(output_location).expanduser().resolve()
            self._pending_output_directory = location if location.is_dir() else location.parent

        worker = OperationWorker(task)
        self._worker = worker
        worker.succeeded.connect(self._operation_succeeded)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(self._operation_finished)
        worker.start()

    def _operation_succeeded(self, message: str) -> None:
        self.status_label.setText(message)
        self.open_directory_button.setVisible(
            self._pending_output_directory is not None
            and self._pending_output_directory.is_dir()
        )

    def _operation_failed(self, message: str) -> None:
        self.open_directory_button.hide()
        self.status_label.setText(f"Não foi possível concluir a operação: {message}")
        QMessageBox.warning(self, "Operação não concluída", message)

    def _operation_finished(self) -> None:
        self.progress.hide()
        self.tabs.setEnabled(True)
        worker = self._worker
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        self._worker = None

    def _open_output_directory(self) -> None:
        directory = self._pending_output_directory
        if directory is None or not directory.is_dir():
            self.status_label.setText("A pasta de saída não está disponível.")
            self.open_directory_button.hide()
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            QMessageBox.information(self, APP_NAME, f"Abra esta pasta manualmente:\n{directory}")

    def closeEvent(self, event: QCloseEvent) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            QMessageBox.information(
                self,
                APP_NAME,
                "Uma operação está em andamento. Aguarde a conclusão antes de fechar o aplicativo.",
            )
            event.ignore()
            return
        if worker is not None:
            worker.wait()
            worker.deleteLater()
            self._worker = None
        event.accept()

    def _require_output_pdf(
        self,
        suggested_name: str,
        *,
        source_paths: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        return self._choose_output_pdf(suggested_name, source_paths=source_paths)

    def _build_image_pdf_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Transformar imagens em um documento",
            "Adicione as imagens e organize a sequência. Cada arquivo será colocado em uma página A4 sem distorcer a proporção.",
        )
        list_widget = self._new_list(extended=True)
        self.image_list = list_widget
        layout.addWidget(list_widget, 1)

        buttons = QHBoxLayout()
        add = QPushButton("+  Adicionar imagens")
        add.setObjectName("secondaryButton")
        add.clicked.connect(self._add_images)
        remove = QPushButton("Remover selecionadas")
        remove.clicked.connect(lambda: self._remove_selected(list_widget))
        up = QPushButton("↑  Subir")
        up.clicked.connect(lambda: self._move_selected(list_widget, -1))
        down = QPushButton("↓  Descer")
        down.clicked.connect(lambda: self._move_selected(list_widget, 1))
        duplicate = QPushButton("Duplicar selecionadas")
        duplicate.clicked.connect(lambda: self._duplicate_selected(list_widget))
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addWidget(duplicate)
        buttons.addStretch(1)
        buttons.addWidget(up)
        buttons.addWidget(down)
        layout.addLayout(buttons)

        options = QHBoxLayout()
        options.addWidget(QLabel("Resolução:"))
        self.image_dpi = QSpinBox()
        self.image_dpi.setRange(72, 600)
        self.image_dpi.setValue(150)
        self.image_dpi.setSuffix(" DPI")
        options.addWidget(self.image_dpi)
        options.addSpacing(18)
        options.addWidget(QLabel("Margem:"))
        self.image_margin = QDoubleSpinBox()
        self.image_margin.setRange(0, 40)
        self.image_margin.setDecimals(1)
        self.image_margin.setValue(10)
        self.image_margin.setSuffix(" mm")
        options.addWidget(self.image_margin)
        options.addStretch(1)
        layout.addLayout(options)

        bottom = QHBoxLayout()
        hint = QLabel("Formatos: JPG, PNG, BMP, WEBP e TIFF.")
        hint.setObjectName("muted")
        make_pdf = QPushButton("Criar PDF")
        make_pdf.setObjectName("primaryButton")
        make_pdf.clicked.connect(self._create_pdf_from_images)
        bottom.addWidget(hint, 1)
        bottom.addWidget(make_pdf)
        layout.addLayout(bottom)
        return page

    def _add_images(self) -> None:
        paths = self._choose_multiple("Adicionar imagens", IMAGE_FILTER)
        added = self._add_paths(self.image_list, paths)
        self.status_label.setText(f"{added} imagem(ns) adicionada(s)." if added else "Nenhuma imagem nova adicionada.")

    @staticmethod
    def _remove_selected(list_widget: QListWidget) -> None:
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    @staticmethod
    def _duplicate_selected(list_widget: QListWidget) -> None:
        rows = sorted({list_widget.row(item) for item in list_widget.selectedItems()})
        if not rows:
            return
        for row in reversed(rows):
            original = list_widget.item(row)
            duplicate = QListWidgetItem(original.text())
            duplicate.setToolTip(original.toolTip())
            duplicate.setData(Qt.ItemDataRole.UserRole, original.data(Qt.ItemDataRole.UserRole))
            list_widget.insertItem(row + 1, duplicate)
            duplicate.setSelected(True)

    @staticmethod
    def _move_selected(list_widget: QListWidget, offset: int) -> None:
        if offset not in (-1, 1):
            raise ValueError("A lista só pode ser movida uma posição por vez.")
        if not list_widget.selectedItems():
            return

        if offset < 0:
            for row in range(1, list_widget.count()):
                current = list_widget.item(row)
                previous = list_widget.item(row - 1)
                if current.isSelected() and not previous.isSelected():
                    item = list_widget.takeItem(row)
                    list_widget.insertItem(row - 1, item)
                    item.setSelected(True)
        else:
            for row in range(list_widget.count() - 2, -1, -1):
                current = list_widget.item(row)
                following = list_widget.item(row + 1)
                if current.isSelected() and not following.isSelected():
                    item = list_widget.takeItem(row)
                    list_widget.insertItem(row + 1, item)
                    item.setSelected(True)

    def _create_pdf_from_images(self) -> None:
        sources = self._all_paths(self.image_list)
        if not sources:
            QMessageBox.information(self, "Adicionar imagens", "Adicione pelo menos uma imagem primeiro.")
            return
        output = self._require_output_pdf("imagens.pdf", source_paths=sources)
        if not output:
            return
        dpi = self.image_dpi.value()
        margin_mm = self.image_margin.value()
        self._run_task(
            "Criando PDF a partir das imagens…",
            lambda: f"PDF criado: {images_to_pdf(sources, output, dpi=dpi, margin_mm=margin_mm)}",
            output_location=output,
        )

    def _build_merge_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Reunir documentos em um único arquivo",
            "A ordem dos PDFs na lista será a ordem dos documentos no arquivo final.",
        )
        self.pdf_list = self._new_list(extended=True)
        layout.addWidget(self.pdf_list, 1)

        buttons = QHBoxLayout()
        add = QPushButton("+  Adicionar PDFs")
        add.setObjectName("secondaryButton")
        add.clicked.connect(self._add_pdfs)
        remove = QPushButton("Remover selecionados")
        remove.clicked.connect(lambda: self._remove_selected(self.pdf_list))
        up = QPushButton("↑  Subir")
        up.clicked.connect(lambda: self._move_selected(self.pdf_list, -1))
        down = QPushButton("↓  Descer")
        down.clicked.connect(lambda: self._move_selected(self.pdf_list, 1))
        duplicate = QPushButton("Duplicar selecionados")
        duplicate.clicked.connect(lambda: self._duplicate_selected(self.pdf_list))
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addWidget(duplicate)
        buttons.addStretch(1)
        buttons.addWidget(up)
        buttons.addWidget(down)
        layout.addLayout(buttons)

        bottom = QHBoxLayout()
        hint = QLabel("Selecione pelo menos dois PDFs.")
        hint.setObjectName("muted")
        merge = QPushButton("Unir PDFs")
        merge.setObjectName("primaryButton")
        merge.clicked.connect(self._merge_pdfs)
        bottom.addWidget(hint, 1)
        bottom.addWidget(merge)
        layout.addLayout(bottom)
        return page

    def _add_pdfs(self) -> None:
        paths = self._choose_multiple("Adicionar PDFs", PDF_FILTER)
        added = self._add_paths(self.pdf_list, paths)
        self.status_label.setText(f"{added} PDF(s) adicionado(s)." if added else "Nenhum PDF novo adicionado.")

    def _merge_pdfs(self) -> None:
        sources = self._all_paths(self.pdf_list)
        if len(sources) < 2:
            QMessageBox.information(self, "Unir PDFs", "Adicione pelo menos dois PDFs.")
            return
        output = self._require_output_pdf("documentos-unidos.pdf", source_paths=sources)
        if not output:
            return
        self._run_task(
            "Unindo os PDFs…",
            lambda: f"PDFs unidos: {merge_pdfs(sources, output)}",
            output_location=output,
        )

    def _build_extract_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Salvar somente as páginas necessárias",
            "Escolha o documento e informe os números das páginas ou intervalos que deseja manter.",
        )
        form = QFormLayout()
        self.extract_path = QLineEdit()
        self.extract_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_extract_pdf)
        source_row = QHBoxLayout()
        source_row.addWidget(self.extract_path, 1)
        source_row.addWidget(browse)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("Arquivo de origem", source_container)

        self.extract_ranges = QLineEdit("1-3")
        self.extract_ranges.setPlaceholderText("Ex.: 1-3, 5, 8-10")
        form.addRow("Páginas", self.extract_ranges)
        self.extract_allow_duplicates = QCheckBox("Permitir repetir páginas no PDF resultante")
        form.addRow("", self.extract_allow_duplicates)
        helper = QLabel("A ordem informada será mantida. Intervalos inválidos ou páginas repetidas são recusados.")
        helper.setObjectName("muted")
        helper.setWordWrap(True)
        layout.addLayout(form)
        layout.addWidget(helper)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        extract = QPushButton("Extrair páginas")
        extract.setObjectName("primaryButton")
        extract.clicked.connect(self._extract_pages)
        button_row.addWidget(extract)
        layout.addLayout(button_row)
        return page

    def _select_extract_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para extrair páginas")
        if path:
            self.extract_path.setText(path)

    def _extract_pages(self) -> None:
        source = self.extract_path.text().strip()
        ranges = self.extract_ranges.text().strip()
        if not source:
            QMessageBox.information(self, "Escolher PDF", "Escolha o PDF de origem.")
            return
        output = self._require_output_pdf(f"{Path(source).stem}-paginas.pdf", source_paths=[source])
        if not output:
            return
        allow_duplicates = self.extract_allow_duplicates.isChecked()
        self._run_task(
            "Extraindo páginas…",
            lambda: f"Páginas extraídas: {extract_pages(source, ranges, output, allow_duplicates=allow_duplicates)}",
            output_location=output,
        )

    def _build_rotate_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Corrigir a orientação das páginas",
            "Gire todas as páginas do documento ou informe um intervalo específico. Os conteúdos não são rasterizados.",
        )
        form = QFormLayout()
        self.rotate_path = QLineEdit()
        self.rotate_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_rotate_pdf)
        row = QHBoxLayout()
        row.addWidget(self.rotate_path, 1)
        row.addWidget(browse)
        container = QWidget()
        container.setLayout(row)
        form.addRow("PDF de origem", container)

        self.rotate_angle = QComboBox()
        self.rotate_angle.addItems(["90° no sentido horário", "180°", "270° no sentido horário"])
        form.addRow("Rotação", self.rotate_angle)

        self.rotate_ranges = QLineEdit()
        self.rotate_ranges.setPlaceholderText("Deixe vazio para girar todas as páginas")
        form.addRow("Páginas (opcional)", self.rotate_ranges)
        layout.addLayout(form)
        note = QLabel("Exemplo: 1-2, 5. As páginas não selecionadas permanecem sem rotação.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        rotate = QPushButton("Girar páginas")
        rotate.setObjectName("primaryButton")
        rotate.clicked.connect(self._rotate_pdf)
        actions.addWidget(rotate)
        layout.addLayout(actions)
        return page

    def _select_rotate_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para girar")
        if path:
            self.rotate_path.setText(path)

    def _rotate_pdf(self) -> None:
        source = self.rotate_path.text().strip()
        if not source:
            QMessageBox.information(self, "Escolher PDF", "Escolha o PDF de origem.")
            return
        angle = (90, 180, 270)[self.rotate_angle.currentIndex()]
        ranges = self.rotate_ranges.text().strip() or None
        output = self._require_output_pdf(f"{Path(source).stem}-rotacionado.pdf", source_paths=[source])
        if not output:
            return
        self._run_task(
            "Girando páginas…",
            lambda: f"PDF rotacionado: {rotate_pdf(source, output, angle, ranges)}",
            output_location=output,
        )

    def _build_split_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Dividir o PDF em arquivos menores",
            "Cada página será salva como um PDF separado. Se algum nome de destino já existir, a operação será interrompida para evitar sobrescrita.",
        )
        form = QFormLayout()
        self.split_path = QLineEdit()
        self.split_path.setReadOnly(True)
        self._split_custom_directory = False
        browse_pdf = QPushButton("Escolher PDF")
        browse_pdf.clicked.connect(self._select_split_pdf)
        source_row = QHBoxLayout()
        source_row.addWidget(self.split_path, 1)
        source_row.addWidget(browse_pdf)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("PDF de origem", source_container)

        self.split_directory = QLineEdit()
        self.split_directory.setReadOnly(True)
        browse_dir = QPushButton("Escolher pasta")
        browse_dir.clicked.connect(self._select_split_directory)
        directory_row = QHBoxLayout()
        directory_row.addWidget(self.split_directory, 1)
        directory_row.addWidget(browse_dir)
        directory_container = QWidget()
        directory_container.setLayout(directory_row)
        form.addRow("Pasta de saída", directory_container)
        layout.addLayout(form)
        layout.addStretch(1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        split = QPushButton("Dividir PDF")
        split.setObjectName("primaryButton")
        split.clicked.connect(self._split_pdf)
        actions.addWidget(split)
        layout.addLayout(actions)
        return page

    def _select_split_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para dividir")
        if path:
            self.split_path.setText(path)
            if not self._split_custom_directory:
                self.split_directory.setText(str(Path(path).parent / f"{Path(path).stem}-paginas"))

    def _select_split_directory(self) -> None:
        path = self._choose_directory("Escolher pasta de saída")
        if path:
            self.split_directory.setText(path)
            self._split_custom_directory = True

    def _split_pdf(self) -> None:
        source = self.split_path.text().strip()
        directory = self.split_directory.text().strip()
        if not source or not directory:
            QMessageBox.information(self, "Dividir PDF", "Escolha o PDF e uma pasta de saída.")
            return
        self._run_task(
            "Dividindo PDF em arquivos de página única…",
            lambda: f"{len(split_pdf(source, directory))} páginas salvas em: {directory}",
            output_location=directory,
        )

    def _build_convert_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Converter e redimensionar imagens",
            "Converta várias imagens de uma só vez. O redimensionamento mantém a proporção e nunca amplia imagens pequenas.",
        )
        self.convert_list = self._new_list(extended=True)
        layout.addWidget(self.convert_list, 1)

        file_row = QHBoxLayout()
        add = QPushButton("+  Adicionar imagens")
        add.setObjectName("secondaryButton")
        add.clicked.connect(self._add_convert_images)
        remove = QPushButton("Remover selecionadas")
        remove.clicked.connect(lambda: self._remove_selected(self.convert_list))
        file_row.addWidget(add)
        file_row.addWidget(remove)
        file_row.addStretch(1)
        layout.addLayout(file_row)

        form = QFormLayout()
        self.convert_format = QComboBox()
        self.convert_format.addItems(["JPEG", "PNG", "WEBP", "BMP", "TIFF"])
        form.addRow("Formato de saída", self.convert_format)

        dimension_row = QHBoxLayout()
        self.convert_width = QSpinBox()
        self.convert_width.setRange(0, 30000)
        self.convert_width.setSpecialValueText("Original")
        self.convert_width.setValue(0)
        self.convert_height = QSpinBox()
        self.convert_height.setRange(0, 30000)
        self.convert_height.setSpecialValueText("Original")
        self.convert_height.setValue(0)
        dimension_row.addWidget(QLabel("Largura máx."))
        dimension_row.addWidget(self.convert_width)
        dimension_row.addSpacing(12)
        dimension_row.addWidget(QLabel("Altura máx."))
        dimension_row.addWidget(self.convert_height)
        dimensions = QWidget()
        dimensions.setLayout(dimension_row)
        form.addRow("Dimensões (px)", dimensions)

        self.convert_quality = QSpinBox()
        self.convert_quality.setRange(1, 100)
        self.convert_quality.setValue(90)
        self.convert_quality.setSuffix(" / 100")
        form.addRow("Qualidade JPEG/WEBP", self.convert_quality)

        self.convert_directory = QLineEdit()
        self.convert_directory.setReadOnly(True)
        browse_dir = QPushButton("Escolher pasta")
        browse_dir.clicked.connect(self._select_convert_directory)
        out_row = QHBoxLayout()
        out_row.addWidget(self.convert_directory, 1)
        out_row.addWidget(browse_dir)
        out_container = QWidget()
        out_container.setLayout(out_row)
        form.addRow("Pasta de saída", out_container)

        layout.addLayout(form)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        convert = QPushButton("Converter imagens")
        convert.setObjectName("primaryButton")
        convert.clicked.connect(self._convert_images)
        button_row.addWidget(convert)
        layout.addLayout(button_row)
        return page

    def _add_convert_images(self) -> None:
        paths = self._choose_multiple("Escolher imagens para converter", IMAGE_FILTER)
        added = self._add_paths(self.convert_list, paths)
        self.status_label.setText(f"{added} imagem(ns) adicionada(s)." if added else "Nenhuma imagem nova adicionada.")

    def _select_convert_directory(self) -> None:
        path = self._choose_directory("Escolher pasta para salvar as imagens")
        if path:
            self.convert_directory.setText(path)

    def _convert_images(self) -> None:
        sources = self._all_paths(self.convert_list)
        directory_text = self.convert_directory.text().strip()
        if not sources:
            QMessageBox.information(self, "Converter imagens", "Adicione pelo menos uma imagem.")
            return
        if not directory_text or not Path(directory_text).is_dir():
            QMessageBox.information(self, "Pasta de saída", "Escolha uma pasta de saída existente.")
            return

        image_format = self.convert_format.currentText()
        extension = FORMAT_EXTENSIONS[image_format]
        max_width = self.convert_width.value() or None
        max_height = self.convert_height.value() or None
        quality = self.convert_quality.value()
        directory = Path(directory_text)

        def task() -> str:
            completed: list[Path] = []
            failures: list[str] = []
            for source_text in sources:
                source = Path(source_text)
                destination = directory / f"{source.stem}{extension}"
                suffix = 2
                while destination.exists() or destination.resolve() == source.resolve():
                    destination = directory / f"{source.stem}-{suffix}{extension}"
                    suffix += 1
                try:
                    completed.append(
                        convert_image(
                            source,
                            destination,
                            image_format,
                            max_width=max_width,
                            max_height=max_height,
                            quality=quality,
                        )
                    )
                except Exception as error:
                    failures.append(f"{source.name}: {error}")

            summary = f"{len(completed)} imagem(ns) convertida(s) em {directory}."
            if failures:
                summary += f" Falhas: {len(failures)}. " + " | ".join(failures[:3])
            if not completed:
                raise RuntimeError(summary)
            return summary

        self._run_task("Convertendo imagens…", task, output_location=directory)


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("FerramentasDeArquivo")
    application.setFont(QFont("Segoe UI", 10))
    window = DocumentToolsWindow()
    window.show()
    return application.exec()
