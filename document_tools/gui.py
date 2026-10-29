"""PySide6 desktop interface for the local PDF and image toolkit."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSettings, QSize, QThread, QTimer, Signal, Qt, QUrl, QStandardPaths, QMimeData, QPoint
from PySide6.QtGui import QCloseEvent, QDesktopServices, QDrag, QFont, QIcon, QImage, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QInputDialog,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStyle,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QToolButton,
    QWidget,
)
from PySide6.QtGui import QColor, QPainter, QPen

from document_tools import __version__
from document_tools.batch_processing import BatchControl, BatchFileResult, process_pdf_folder
from document_tools.report_history import delete_batch_report, load_batch_history, save_batch_report
from document_tools.image_resolution import recommend_dpi_from_images
from document_tools.errors import friendly_error_message
from document_tools.pdf_rendering import export_pdf_pages_to_images
from document_tools.profiles import (
    CURRENT_PROFILE_SCHEMA_VERSION,
    migrate_local_profile,
    validate_profile_document,
)
from document_tools.pdf_ops import (
    convert_image,
    delete_pages,
    extract_pages,
    images_to_pdf,
    merge_pdfs,
    mix_pdfs,
    insert_pages_repeatedly,
    optimize_pdf,
    pdf_page_count,
    reorder_pdf_pages,
    stamp_pdf,
    rotate_pdf,
    split_pdf,
    pdf_requires_user_password,
    process_pdf_pipeline,
)


APP_NAME = "PDF Hub"
IMAGE_FILTER = "Imagens (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.gif)"
PDF_FILTER = "Documentos PDF (*.pdf)"


def _same_existing_file(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False



def _ensure_suffix(path: Path, suffix: str) -> Path:
    """Append an extension without replacing dotted parts of the filename."""
    normalized = suffix if suffix.startswith(".") else f".{suffix}"
    if path.suffix.casefold() == normalized.casefold():
        return path
    return path.with_name(path.name + normalized)


def _match_template(text: str, template: str) -> tuple[str, ...] | None:
    """Match a rendered string against a template containing {placeholders}."""
    parts = re.split(r"(\{[^{}]+\})", template)
    pattern = "^" + "".join(
        "(.+?)" if re.fullmatch(r"\{[^{}]+\}", part) else re.escape(part)
        for part in parts
    ) + "$"
    match = re.fullmatch(pattern, text, flags=re.DOTALL)
    return match.groups() if match else None


def _fill_template(template: str, values: tuple[str, ...]) -> str:
    iterator = iter(values)
    return re.sub(r"\{[^{}]+\}", lambda _match: next(iterator, ""), template)

FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "TIFF": ".tif",
}

TRANSLATIONS = {
    "en": {
        "PDF e imagens • v{version} • organizado, seguro e local": "PDFs and images • v{version} • organized, safe and local",
        "●  PDF HUB • PROCESSAMENTO LOCAL": "●  PDF HUB • LOCAL PROCESSING",
        "O que vamos organizar hoje?": "What would you like to organize today?",
        "Escolha uma ferramenta abaixo. Os arquivos de origem são preservados.": "Choose a tool below. Original files are preserved.",
        "Permissões de saída (Linux/macOS)": "Output permissions (Linux/macOS)",
        "No Windows, o sistema de permissões é gerenciado pelo próprio sistema operacional.": "On Windows, permissions are managed by the operating system.",
        "Somente usuário (0600)": "Owner only (0600)",
        "Compartilhado (0644)": "Shared readable (0644)",
        "0600: somente o usuário atual. 0644: outros usuários do sistema podem ler os arquivos.": "0600: only the current user. 0644: other system users can read the files.",
        "Idioma / Language": "Language",
        "Imagens para PDF": "Images to PDF",
        "Unir PDFs": "Merge PDFs",
        "Misturar PDFs": "Mix PDFs",
        "Inserir páginas": "Insert pages",
        "Combinar páginas de dois PDFs alternadamente": "Interleave pages from two PDFs",
        "Escolha os documentos e defina quantas páginas de cada arquivo serão usadas em cada bloco.": "Choose the documents and set how many pages from each file are used in each block.",
        "Primeiro PDF": "First PDF",
        "Segundo PDF": "Second PDF",
        "Páginas do PDF selecionado (opcional)": "Pages from the selected PDF (optional)",
        "Páginas do primeiro PDF (opcional)": "Pages from the first PDF (optional)",
        "Páginas do segundo PDF (opcional)": "Pages from the second PDF (optional)",
        "Senha do primeiro PDF (opcional)": "First PDF password (optional)",
        "Senha do segundo PDF (opcional)": "Second PDF password (optional)",
        "Páginas do primeiro PDF por bloco": "Pages from first PDF per block",
        "Páginas do segundo PDF por bloco": "Pages from second PDF per block",
        "Inverter a ordem das páginas do segundo PDF": "Reverse the order of pages from the second PDF",
        "Deixe em branco para usar todas as páginas; exemplo: 1-3, 5.": "Leave blank to use every page; example: 1-3, 5.",
        "Misturar PDFs": "Mix PDFs",
        "Misturando PDFs…": "Mixing PDFs…",
        "PDFs misturados: ": "PDFs mixed: ",
        "Inserir páginas de um PDF repetidamente dentro de outro": "Insert pages from one PDF repeatedly into another",
        "Escolha o PDF de destino e o arquivo que contém as páginas a inserir.": "Choose the destination PDF and the file containing the pages to insert.",
        "PDF de destino": "Destination PDF",
        "PDF com páginas a inserir": "PDF containing pages to insert",
        "Páginas a inserir (opcional)": "Pages to insert (optional)",
        "Inserir após cada N páginas": "Insert after every N pages",
        "Senha do PDF de destino (opcional)": "Destination PDF password (optional)",
        "Senha do PDF a inserir (opcional)": "PDF-to-insert password (optional)",
        "Inserindo páginas…": "Inserting pages…",
        "PDF com páginas inseridas: ": "PDF with inserted pages: ",
        "Escolha o primeiro PDF.": "Choose the first PDF.",
        "Escolha o segundo PDF.": "Choose the second PDF.",
        "Escolher o primeiro PDF.": "Choose the first PDF",
        "Escolher o segundo PDF.": "Choose the second PDF",
        "Escolher PDF de destino.": "Choose destination PDF",
        "Escolher o PDF que contém as páginas a inserir.": "Choose the PDF containing pages to insert",
        "Escolha o PDF de destino.": "Choose the destination PDF.",
        "Escolha o PDF que contém as páginas a inserir.": "Choose the PDF containing the pages to insert.",
        "O número de páginas por bloco deve ser positivo.": "The number of pages per block must be positive.",
        "O intervalo entre inserções deve ser positivo.": "The insertion interval must be positive.",
        "O intervalo entre inserções não pode exceder o número de páginas do PDF de destino.": "The insertion interval cannot exceed the number of pages in the destination PDF.",
        "Extrair páginas": "Extract pages",
        "Girar páginas": "Rotate pages",
        "Dividir PDF": "Split PDF",
        "Reordenar páginas": "Reorder pages",
        "Marca d'água e numeração": "Watermark and page numbers",
        "Otimizar PDF": "Optimize PDF",
        "Converter imagens": "Convert images",
        "Pronto. Selecione uma operação acima.": "Ready. Choose an operation above.",
        "Abrir pasta": "Open folder",
        "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente.": "The file or folder could not be found. Check the path and try again.",
        "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas.": "The file could not be accessed or saved. Check permissions and close it in other applications.",
        "A imagem é inválida, muito grande para processar com segurança ou usa um formato não suportado.": "The image is invalid, too large to process safely, or uses an unsupported format.",
        "Não foi possível interpretar o PDF. Ele pode estar danificado ou protegido por senha.": "The PDF could not be read. It may be damaged or password-protected.",
        "Imagens para PDF": "Images to PDF",
        "Unir PDFs": "Merge PDFs",
        "Extrair páginas": "Extract pages",
        "Girar páginas": "Rotate pages",
        "Dividir PDF": "Split PDF",
        "Converter imagens": "Convert images",
        "Adicionar imagens": "Add images",
        "+  Adicionar imagens": "+  Add images",
        "Remover selecionadas": "Remove selected",
        "↑  Subir": "↑  Move up",
        "↓  Descer": "↓  Move down",
        "Duplicar selecionadas": "Duplicate selected",
        "Resolução:": "Resolution:",
        "Margem:": "Margin:",
        "Incluir todas as páginas/quadros de imagens multipágina ou animadas": "Include all pages/frames from multipage or animated images",
        "Quando desmarcado, usa somente a primeira página ou o primeiro quadro de cada arquivo.": "When unchecked, only the first page or frame of each file is used.",
        "Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.": "Formats: JPG, PNG, BMP, WEBP, TIFF and GIF.",
        "Criar PDF": "Create PDF",
        "Criando PDF a partir das imagens…": "Creating PDF from images…",
        "Criando PDF a partir das imagens": "Creating PDF from images",
        "Selecione pelo menos dois PDFs.": "Select at least two PDFs.",
        "Salvar somente as páginas necessárias": "Save only the pages you need",
        "Escolha o documento e informe os números das páginas ou intervalos que deseja manter.": "Choose the document and enter the page numbers or ranges to keep.",
        "Arquivo de origem": "Source file",
        "Páginas": "Pages",
        "Ex.: 1-3, 5, 8-10": "e.g. 1-3, 5, 8-10",
        "Senha do PDF (opcional)": "PDF password (optional)",
        "Opcional; não é armazenada": "Optional; not stored",
        "Permitir repetir páginas no PDF resultante": "Allow repeated pages in the output PDF",
        "A ordem informada será mantida. Intervalos inválidos ou páginas repetidas são recusados.": "The requested order is preserved. Invalid ranges or duplicate pages are rejected.",
        "Extrair páginas": "Extract pages",
        "Corrigir a orientação das páginas": "Correct page orientation",
        "Gire todas as páginas do documento ou informe um intervalo específico. Os conteúdos não são rasterizados.": "Rotate all pages or enter a specific range. Page content is not rasterized.",
        "PDF de origem": "Source PDF",
        "90° no sentido horário": "90° clockwise",
        "270° no sentido horário": "270° clockwise",
        "Deixe vazio para girar todas as páginas": "Leave blank to rotate all pages",
        "Páginas (opcional)": "Pages (optional)",
        "Exemplo: 1-2, 5. As páginas não selecionadas permanecem sem rotação.": "Example: 1-2, 5. Unselected pages are not rotated.",
        "Girar páginas": "Rotate pages",
        "Dividir o PDF em arquivos menores": "Split the PDF into smaller files",
        "Cada página será salva como um PDF separado. Se algum nome de destino já existir, a operação será interrompida para evitar sobrescrita.": "Each page is saved as a separate PDF. If a destination filename already exists, the operation stops to prevent overwriting.",
        "Pasta de saída": "Output folder",
        "Escolher pasta": "Choose folder",
        "Dividir PDF": "Split PDF",
        "Converter e redimensionar imagens": "Convert and resize images",
        "Converta várias imagens de uma só vez. O redimensionamento mantém a proporção e nunca amplia imagens pequenas.": "Convert multiple images at once. Resizing preserves aspect ratio and never enlarges small images.",
        "Formato de saída": "Output format",
        "Largura máx.": "Max width",
        "Altura máx.": "Max height",
        "Dimensões (px)": "Dimensions (px)",
        "Qualidade JPEG/WEBP": "JPEG/WEBP quality",
        "Converter imagens": "Convert images",
        "Escolher PDF": "Choose PDF",
        "Escolher pasta de saída": "Choose output folder",
        "Escolher pasta para salvar as imagens": "Choose a folder to save images",
        "Salvar PDF resultante": "Save output PDF",
        "Escolha outro nome": "Choose another name",
        "O arquivo de saída não pode substituir um dos arquivos de origem.": "The output file cannot replace a source file.",
        "Confirmar substituição": "Confirm replacement",
        "O arquivo “{name}” já existe. Deseja substituí-lo?": "The file “{name}” already exists. Replace it?",
        "Operação cancelada. O arquivo existente foi preservado.": "Operation cancelled. The existing file was preserved.",
        "Operação não concluída": "Operation not completed",
        "Não foi possível concluir a operação: {message}": "Could not complete operation: {message}",
        "A pasta de saída não está disponível.": "The output folder is not available.",
        "Abra esta pasta manualmente:\n{path}": "Open this folder manually:\n{path}",
        "Uma operação está em andamento. Aguarde a conclusão antes de fechar o aplicativo.": "An operation is in progress. Wait for it to finish before closing the app.",
        "Selecione pelo menos um arquivo de origem.": "Select at least one source file.",
        "Adicione pelo menos uma imagem primeiro.": "Add at least one image first.",
        "Adicione pelo menos dois PDFs.": "Add at least two PDFs.",
        "Selecione pelo menos dois PDFs para unir.": "Select at least two PDFs to merge.",
        "Escolha o PDF de origem.": "Choose the source PDF.",
        "Senha do PDF": "PDF password",
        "O arquivo '{name}' está protegido. Digite a senha:": "The file '{name}' is protected. Enter its password:",
        "Senha necessária": "Password required",
        "Informe uma senha não vazia para continuar.": "Enter a non-empty password to continue.",
        "Não foi possível verificar o PDF": "Could not inspect the PDF",
        "Não foi possível abrir o PDF": "Could not open the PDF",
        "Escolha o PDF e uma pasta de saída.": "Choose the PDF and an output folder.",
        "Escolha uma pasta de saída existente.": "Choose an existing output folder.",
        "Página {number}": "Page {number}",
        "Visualize e arraste as páginas para definir a ordem final. Todas as páginas devem permanecer na lista.": "Drag pages to set the final order. Every page must remain in the list.",
        "Salvar PDF reordenado": "Save reordered PDF",
        "Reordenar PDF": "Reorder PDF",
        "Escolha um PDF para reorganizar suas páginas.": "Choose a PDF to reorder its pages.",
        "PDF reordenado: {path}": "PDF reordered: {path}",
        "Adicionar uma marca d'água de texto, numeração, ou ambos. O conteúdo original não é rasterizado.": "Add a text watermark, page numbers, or both. Original content is not rasterized.",
        "Texto da marca d'água": "Watermark text",
        "Ex.: CONFIDENCIAL": "e.g. CONFIDENTIAL",
        "Adicionar numeração de páginas": "Add page numbers",
        "Posição da marca d'água": "Watermark position",
        "Diagonal (centro)": "Diagonal (center)",
        "Centralizada": "Centered",
        "Rodapé central": "Centered footer",
        "Posição da numeração": "Page number position",
        "Rodapé direito": "Bottom right",
        "Rodapé centralizado": "Bottom center",
        "Tamanho do texto": "Text size",
        "Opacidade": "Opacity",
        "Aplicar marca d'água/numeração": "Apply watermark/page numbers",
        "PDF carimbado: {path}": "PDF stamped: {path}",
        "Informe o texto da marca d'água ou ative a numeração de páginas.": "Enter watermark text or enable page numbering.",
        "PDF de origem para otimizar": "Source PDF to optimize",
        "Escolha entre preservar toda a qualidade (sem perdas) ou reduzir mais o tamanho recomprimindo imagens.": "Choose to preserve full quality (lossless) or reduce size further by recompressing images.",
        "Sem perdas (mais conservador)": "Lossless (safer)",
        "Equilibrada (recomprimir imagens)": "Balanced (recompress images)",
        "Qualidade das imagens": "Image quality",
        "Reduzir tamanho do PDF": "Reduce PDF size",
        "Otimização sem perdas": "Lossless optimization",
        "Otimização equilibrada": "Balanced optimization",
        "PDF otimizado: {old} → {new} ({percent}% de redução)": "PDF optimized: {old} → {new} ({percent}% smaller)",
        "Qualidade JPEG precisa ficar entre 50 e 95.": "JPEG quality must be between 50 and 95.",
        "Escolha otimização sem perdas ou equilibrada.": "Choose lossless or balanced optimization.",
        "Esta opção recomprime imagens sem transparência; a qualidade visual pode diminuir.": "This option recompresses opaque images; visual quality may decrease.",
        "Junte documentos em um único arquivo": "Combine documents into one file",
        "A ordem dos PDFs na lista será a ordem dos documentos no arquivo final.": "The PDF list order will become the document order in the final file.",
        "Escolha uma senha por PDF ou deixe a senha como None.": "Provide one password per PDF or leave the password as None.",
        "Unir documentos em um único arquivo": "Combine documents into one file",
        "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água.": "Choose the document and set watermark text, position, and opacity.",
        "Escolha o modo de otimização e a qualidade das imagens.": "Choose the optimization mode and image quality.",
        "Modo de otimização": "Optimization mode",
        "{count} páginas carregadas. Arraste para reorganizar.": "{count} pages loaded. Drag to reorder.",
        "Arraste uma página para cima ou para baixo. A numeração indica a página original.": "Drag a page up or down. The label shows its original page number.",
        "Escolher PDF para otimizar": "Choose PDF to optimize",
        "Escolher PDF para marca d'água/numeração": "Choose PDF for watermark/page numbering",
        "Escolher PDF para reorganizar suas páginas": "Choose a PDF to reorder",
        "Processamento local:": "Local processing:",
        "{added} imagem(ns) adicionada(s).": "{added} image(s) added.",
        "Nenhuma imagem nova adicionada.": "No new images added.",
        "{added} PDF(s) adicionado(s).": "{added} PDF(s) added.",
        "Nenhum PDF novo adicionado.": "No new PDFs added.",
        "{count} imagem(ns) convertida(s) em {directory}.": "{count} image(s) converted in {directory}.",
        "Qualidade": "Quality",
        "+  Adicionar PDFs": "+  Add PDFs",
        "Remover selecionados": "Remove selected",
        "Duplicar selecionados": "Duplicate selected",
        "Rotação": "Rotation",
        "Prévia da página selecionada": "Selected page preview",
        "Selecione uma página para visualizar.": "Select a page to preview it.",
        "Não foi possível gerar a prévia desta página.": "Could not render a preview for this page.",
        "Deixe vazio para aplicar em todas as páginas": "Leave blank to apply to all pages",
        "O texto e a numeração serão aplicados apenas às páginas selecionadas. A numeração conserva o número original da página.": "Text and numbering are applied only to selected pages. Page numbers retain the original document numbering.",
        "Páginas marcadas: {ranges}": "Selected pages: {ranges}",
        "Transformar imagens em um documento": "Turn images into a document",
        "Adicione as imagens e organize a sequência. Cada arquivo será colocado em uma página A4 sem distorcer a proporção.": "Add images and arrange their order. Each file will be placed on an A4 page without distorting its aspect ratio.",
        "Reunir documentos em um único arquivo": "Combine documents into one file",
        "A otimização sem perdas comprime streams e remove objetos redundantes; a equilibrada também recomprime imagens opacas.": "Lossless optimization compresses streams and removes redundant objects; balanced optimization also recompresses opaque images.",
        "Unindo os PDFs…": "Merging PDFs…",
        "Extraindo páginas…": "Extracting pages…",
        "Girando páginas…": "Rotating pages…",
        "Dividindo PDF em arquivos de página única…": "Splitting PDF into single-page files…",
        "Convertendo imagens…": "Converting images…",
        "{count} páginas salvas em: {directory}": "{count} pages saved to: {directory}",
        " Falhas: {count}.": " Failures: {count}.",
        "O intervalo '{range}' precisa estar entre 1 e {count}.": "Range '{range}' must be between 1 and {count}.",
        "A página {number} foi informada mais de uma vez.": "Page {number} was specified more than once.",
        "Intervalo de páginas inválido: '{range}'.": "Invalid page range: '{range}'.",
        "A senha informada para o PDF '{name}' está incorreta.": "The password for PDF '{name}' is incorrect.",
        "A senha informada para o PDF '{name}' está incorreta ou não pôde ser usada.": "The password for PDF '{name}' is incorrect or could not be used.",
        "O PDF '{name}' exige uma senha. Informe-a para continuar.": "PDF '{name}' requires a password. Enter it to continue.",
        "A pasta já contém '{name}'. Escolha outra pasta ou remova os arquivos conflitantes.": "The folder already contains '{name}'. Choose another folder or remove conflicting files.",
        "Fluxo em lote": "Batch workflow",
        "Processar um PDF em várias etapas": "Process one PDF in multiple steps",
        "Etapas executadas nesta ordem: rotação, marca d'água/numeração e otimização. O arquivo original é preservado.": "Steps run in this order: rotation, watermark/page numbering, and optimization. The original file is preserved.",
        "Escolher PDF para fluxo em lote": "Choose PDF for batch workflow",
        "Aplicar rotação": "Apply rotation",
        "Aplicar otimização": "Apply optimization",
        "Executar fluxo em lote": "Run batch workflow",
        "Executando fluxo em lote…": "Running batch workflow…",
        "Fluxo em lote concluído: {path}": "Batch workflow completed: {path}",
        "Selecione pelo menos uma etapa do fluxo.": "Select at least one workflow step.",
        "A etapa de marca d'água precisa de um texto ou da numeração ativada.": "The watermark step needs text or page numbering enabled.",
        "Qualquer etapa selecionada será executada na sequência indicada acima.": "Selected steps will run in the order shown above.",
        "Texto da marca d'água (opcional)": "Watermark text (optional)",
        "Arraste as miniaturas para organizar as páginas. Os números indicam as páginas originais.": "Drag the thumbnails to reorder pages. Labels show the original page numbers.",
        "Salvar perfil": "Save profile",
        "Carregar perfil": "Load profile",
        "Excluir perfil": "Delete profile",
        "Nome do perfil:": "Profile name:",
        "Selecione um perfil:": "Select a profile:",
        "Nenhum perfil salvo ainda.": "No saved profiles yet.",
        "Informe um nome para o perfil.": "Enter a name for the profile.",
        "O nome do perfil deve ter até 80 caracteres.": "Profile names must be 80 characters or fewer.",
        "Já existe um perfil chamado '{name}'. Deseja substituí-lo?": "A profile named '{name}' already exists. Replace it?",
        "O perfil '{name}' já existe, mas usa um esquema que esta versão não reconhece. Substituí-lo pode impedir que versões mais novas recuperem suas opções. Deseja continuar?": "The profile '{name}' already exists, but its schema is not recognized by this version. Replacing it may prevent newer versions from recovering its options. Continue?",
        "Lote pausado após {completed} de {total} arquivo(s).": "Batch paused after {completed} of {total} file(s).",
        "Deseja excluir o perfil '{name}'?": "Delete the profile '{name}'?",
        "Perfil salvo: {name}": "Profile saved: {name}",
        "Perfil carregado: {name}": "Profile loaded: {name}",
        "Perfil excluído: {name}": "Profile deleted: {name}",
        "Os perfis guardam somente as opções do fluxo; não incluem caminho do PDF nem senha.": "Profiles store workflow options only; they do not include the PDF path or password.",
        "Não foi possível gerar miniaturas do PDF.": "Could not render PDF thumbnails.",
        "Visualize todas as páginas e arraste para definir a ordem final. Todas as páginas devem permanecer na lista.": "View all page thumbnails and drag them into the final order. Every page must remain in the list.",
        "Exportar perfil": "Export profile",
        "Importar perfil": "Import profile",
        "Arquivos JSON (*.json)": "JSON files (*.json)",
        "Nenhum perfil salvo para exportar.": "No saved profiles to export.",
        "Selecione um perfil para exportar:": "Select a profile to export:",
        "Não foi possível salvar o arquivo de perfil. Verifique a pasta e as permissões.": "Could not save the profile file. Check the folder and permissions.",
        "Perfil exportado: {name}": "Profile exported: {name}",
        "Perfil importado: {name}": "Profile imported: {name}",
        "O arquivo de perfil não contém um objeto JSON.": "The profile file does not contain a JSON object.",
        "O arquivo contém campos extras ou não reconhecidos.": "The file contains extra or unrecognized fields.",
        "A versão do perfil não é compatível.": "The profile version is not compatible.",
        "O nome do perfil é inválido.": "The profile name is invalid.",
        "O perfil contém opções ausentes ou campos não reconhecidos.": "The profile has missing options or unrecognized fields.",
        "O perfil contém opções com tipos inválidos.": "The profile contains options with invalid types.",
        "O ângulo de rotação do perfil é inválido.": "The profile rotation angle is invalid.",
        "O perfil contém texto inválido ou longo demais.": "The profile contains invalid or oversized text.",
        "O modo de otimização do perfil é inválido.": "The profile optimization mode is invalid.",
        "A qualidade do perfil deve ficar entre 50 e 95.": "The profile quality must be between 50 and 95.",
        "O arquivo de perfil excede o tamanho máximo permitido.": "The profile file exceeds the maximum allowed size.",
        "O arquivo não é um perfil JSON válido do PDF Hub. Verifique a versão e as opções do arquivo.": "This is not a valid PDF Hub JSON profile. Check the file version and options.",
        "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar.": "The PDF contains an unsupported structure or is damaged. Try saving a fresh copy before processing it.",
        "A imagem não pôde ser processada. Verifique se o arquivo está íntegro e usa um formato compatível.": "The image could not be processed. Check that the file is intact and uses a supported format.",
        "Não foi possível renderizar o PDF. Ele pode usar recursos não suportados ou estar danificado.": "The PDF could not be rendered. It may use unsupported features or be damaged.",
        "O perfil salvo contém opções inválidas e não pode ser exportado.": "The saved profile contains invalid options and cannot be exported.",
        "Processar pasta": "Process folder",
        "Sufixo dos arquivos processados em pasta": "Output filename suffix for folder batches",
        "Pasta de origem": "Source folder",
        "Pasta de saída": "Output folder",
        "Escolher pasta de origem": "Choose source folder",
        "Escolher pasta de saída": "Choose output folder",
        "Incluir subpastas": "Include subfolders",
        "Retomar lote interrompido, se aplicável": "Resume an interrupted batch when possible",
        "Usa resultados salvos somente quando a origem, o destino, o perfil e a lista de PDFs não mudaram. Desmarque para iniciar do zero.": "Reuse saved results only when the source, destination, profile, and PDF list are unchanged. Uncheck to start from scratch.",
        "Concluído antes da interrupção; resultado reutilizado.": "Completed before the interruption; reusing this result.",
        "Reprocessar apenas falhas": "Retry failed PDFs only",
        "Não há PDFs com falha para reprocessar.": "There are no failed PDFs to retry.",
        "Pausar lote": "Pause batch",
        "Retomar lote": "Resume batch",
        "Cancelar lote": "Cancel batch",
        "Pausa solicitada; o PDF atual será concluído antes de pausar.": "Pause requested; the current PDF will finish before pausing.",
        "Retomando lote…": "Resuming batch…",
        "Cancelamento solicitado; o PDF atual será concluído antes de parar.": "Cancellation requested; the current PDF will finish before stopping.",
        "Lote cancelado com segurança após {completed} arquivo(s). O progresso foi preservado; execute novamente com a retomada ativada.": "Batch safely cancelled after {completed} file(s). Progress was preserved; run it again with resume enabled.",
        "Processar PDFs de uma pasta": "Process PDFs in a folder",
        "Selecione a pasta de origem e o destino, depois escolha um perfil salvo. Os arquivos originais serão preservados; PDFs com erro não interrompem os demais.": "Choose a source folder and destination, then select a saved profile. Originals are preserved; a failed PDF will not stop the others.",
        "Sufixo usado nos nomes dos PDFs de saída ao processar uma pasta com este perfil.": "Suffix used in output PDF filenames when processing a folder with this profile.",
        "Quando ativado, preserva a estrutura de subpastas no destino.": "When enabled, the subfolder structure is preserved in the destination.",
        "O perfil também define o sufixo dos arquivos de saída. PDFs que exigem senha serão registrados como falha, sem interromper o lote.": "The profile also defines the output filename suffix. PDFs requiring a password are reported as failures without interrupting the batch.",
        "Aplicar perfil salvo à pasta": "Apply saved profile to folder",
        "Salvar relatório CSV": "Save CSV report",
        "Arquivo de origem": "Source file",
        "Resultado": "Result",
        "Detalhes": "Details",
        "Arquivo de saída": "Output file",
        "Sucesso": "Success",
        "Falha": "Failure",
        "Processado com sucesso.": "Processed successfully.",
        "Selecione uma pasta de origem.": "Select a source folder.",
        "A pasta selecionada não contém arquivos PDF.": "The selected folder contains no PDF files.",
        "A pasta de saída não pode ser a pasta de origem nem ficar dentro dela.": "The output folder cannot be the source folder or a folder inside it.",
        "Nenhum perfil salvo para aplicar.": "No saved profile is available to apply.",
        "Selecione o perfil a aplicar:": "Select the profile to apply:",
        "Histórico de relatórios": "Report history",
        "Relatórios anteriores": "Previous reports",
        "Carregar relatório": "Load report",
        "Excluir relatório selecionado": "Delete selected report",
        "Não há relatórios salvos.": "There are no saved reports.",
        "Selecione um relatório para carregar.": "Select a report to load.",
        "Relatório {date} — {total} PDF(s), {failed} falha(s) — perfil: {profile}": "Report {date} — {total} PDF(s), {failed} failure(s) — profile: {profile}",
        "Histórico de relatórios restaurado.": "Report history restored.",
        "Relatório histórico carregado.": "Historical report loaded.",
        "Relatório removido do histórico.": "Report removed from history.",
        "Não foi possível ler o relatório histórico.": "Could not read the historical report.",
        "Não foi possível excluir o relatório histórico.": "Could not delete the historical report.",
        "Não foi possível armazenar o relatório no histórico local.": "Could not save the report to local history.",
        "Processando arquivo {completed} de {total}: {name}": "Processing file {completed} of {total}: {name}",
        "Lote concluído: {success} sucesso(s), {failed} falha(s) de {total} PDF(s).": "Batch complete: {success} succeeded, {failed} failed out of {total} PDF(s).",
        "Pronto. Selecione uma ferramenta no menu lateral.": "Ready. Choose a tool from the left menu.",
        "Não há relatório para exportar.": "There is no report to export.",
        "Relatório salvo: {path}": "Report saved: {path}",
        "Não foi possível salvar o relatório CSV. Verifique a pasta e as permissões.": "Could not save the CSV report. Check the folder and permissions.",
        "Arquivos CSV (*.csv)": "CSV files (*.csv)",
        "O sufixo de saída contém caracteres inválidos ou é longo demais.": "The output suffix contains invalid characters or is too long.",
        "Não foi possível gerar o relatório individual do lote.": "Could not generate the individual batch report.",
        "Configurações": "Settings",
        "Defina o idioma, o tema visual e as permissões dos arquivos gerados.": "Choose the interface language, visual theme, and permissions for generated files.",
        "As permissões de saída se aplicam aos arquivos que o PDF Hub cria. O modo 0600 é a opção mais restritiva.": "Output permissions apply to files created by PDF Hub. Mode 0600 is the more restrictive option.",
        "Modo de aparência": "Appearance",
        "Modo claro": "Light mode",
        "Modo escuro": "Dark mode",
        "Sobre permissões de saída": "About output permissions",
        "0600 permite leitura e escrita apenas pelo usuário atual. 0644 permite que outros usuários locais leiam o arquivo. Isso afeta os arquivos gerados em Linux/macOS; no Windows, as permissões são gerenciadas pelo sistema.": "0600 allows only the current user to read and write the file. 0644 allows other local users to read it. This applies to files created on Linux/macOS; Windows permissions are managed by the operating system.",
        "Arraste imagens para esta área ou use “Adicionar imagens”.": "Drop images here or use “Add images”.",
        "Resolução estimada automaticamente a partir das dimensões em pixels das imagens; você pode ajustá-la manualmente.": "Automatically estimated from the images' pixel dimensions; you can adjust it manually.",
        "Calculando resolução a partir das imagens.": "Estimating resolution from images.",
        "Resolução recomendada calculada a partir das imagens.": "Recommended resolution calculated from the images.",
    },
    "es": {
        "PDF e imagens • v{version} • organizado, seguro e local": "PDF e imágenes • v{version} • organizado, seguro y local",
        "●  PDF HUB • PROCESSAMENTO LOCAL": "●  PDF HUB • PROCESAMIENTO LOCAL",
        "O que vamos organizar hoje?": "¿Qué quieres organizar hoy?",
        "Escolha uma ferramenta abaixo. Os arquivos de origem são preservados.": "Elige una herramienta. Los archivos originales se conservan.",
        "Permissões de saída (Linux/macOS)": "Permisos de salida (Linux/macOS)",
        "No Windows, o sistema de permissões é gerenciado pelo próprio sistema operacional.": "En Windows, los permisos los gestiona el sistema operativo.",
        "Somente usuário (0600)": "Solo el usuario (0600)",
        "Compartilhado (0644)": "Lectura compartida (0644)",
        "0600: somente o usuário atual. 0644: outros usuários do sistema podem ler os arquivos.": "0600: solo el usuario actual. 0644: otros usuarios pueden leer los archivos.",
        "Idioma / Language": "Idioma",
        "Imagens para PDF": "Imágenes a PDF",
        "Unir PDFs": "Unir PDF",
        "Misturar PDFs": "Mezclar PDF",
        "Inserir páginas": "Insertar páginas",
        "Combinar páginas de dois PDFs alternadamente": "Intercalar páginas de dos PDF",
        "Escolha os documentos e defina quantas páginas de cada arquivo serão usadas em cada bloco.": "Elige los documentos y define cuántas páginas de cada archivo se usarán en cada bloque.",
        "Primeiro PDF": "Primer PDF",
        "Segundo PDF": "Segundo PDF",
        "Páginas do PDF selecionado (opcional)": "Páginas del PDF seleccionado (opcional)",
        "Páginas do primeiro PDF (opcional)": "Páginas del primer PDF (opcional)",
        "Páginas do segundo PDF (opcional)": "Páginas del segundo PDF (opcional)",
        "Senha do primeiro PDF (opcional)": "Contraseña del primer PDF (opcional)",
        "Senha do segundo PDF (opcional)": "Contraseña del segundo PDF (opcional)",
        "Páginas do primeiro PDF por bloco": "Páginas del primer PDF por bloque",
        "Páginas do segundo PDF por bloco": "Páginas del segundo PDF por bloque",
        "Inverter a ordem das páginas do segundo PDF": "Invertir el orden de las páginas del segundo PDF",
        "Deixe em branco para usar todas as páginas; exemplo: 1-3, 5.": "Deja en blanco para usar todas las páginas; ejemplo: 1-3, 5.",
        "Misturar PDFs": "Mezclar PDF",
        "Misturando PDFs…": "Mezclando PDF…",
        "PDFs misturados: ": "PDF mezclados: ",
        "Inserir páginas de um PDF repetidamente dentro de outro": "Insertar páginas de un PDF repetidamente dentro de otro",
        "Escolha o PDF de destino e o arquivo que contém as páginas a inserir.": "Elige el PDF de destino y el archivo que contiene las páginas que se insertarán.",
        "PDF de destino": "PDF de destino",
        "PDF com páginas a inserir": "PDF que contiene las páginas que se insertarán",
        "Páginas a inserir (opcional)": "Páginas que insertar (opcional)",
        "Inserir após cada N páginas": "Insertar después de cada N páginas",
        "Senha do PDF de destino (opcional)": "Contraseña del PDF de destino (opcional)",
        "Senha do PDF a inserir (opcional)": "Contraseña del PDF que insertar (opcional)",
        "Inserindo páginas…": "Insertando páginas…",
        "PDF com páginas inseridas: ": "PDF con páginas insertadas: ",
        "Escolha o primeiro PDF.": "Elige el primer PDF.",
        "Escolha o segundo PDF.": "Elige el segundo PDF.",
        "Escolher o primeiro PDF.": "Elegir el primer PDF",
        "Escolher o segundo PDF.": "Elegir el segundo PDF",
        "Escolher PDF de destino.": "Elegir PDF de destino",
        "Escolher o PDF que contém as páginas a inserir.": "Elegir el PDF que contiene las páginas que se insertarán",
        "Escolha o PDF de destino.": "Elige el PDF de destino.",
        "Escolha o PDF que contém as páginas a inserir.": "Elige el PDF que contiene las páginas que se insertarán.",
        "O número de páginas por bloco deve ser positivo.": "El número de páginas por bloque debe ser positivo.",
        "O intervalo entre inserções deve ser positivo.": "El intervalo entre inserciones debe ser positivo.",
        "O intervalo entre inserções não pode exceder o número de páginas do PDF de destino.": "El intervalo de inserción no puede superar el número de páginas del PDF de destino.",
        "Extrair páginas": "Extraer páginas",
        "Girar páginas": "Girar páginas",
        "Dividir PDF": "Dividir PDF",
        "Reordenar páginas": "Reordenar páginas",
        "Marca d'água e numeração": "Marca de agua y numeración",
        "Otimizar PDF": "Optimizar PDF",
        "Converter imagens": "Convertir imágenes",
        "Pronto. Selecione uma operação acima.": "Listo. Selecciona una operación arriba.",
        "Abrir pasta": "Abrir carpeta",
        "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas.": "No se pudo acceder o guardar el archivo. Comprueba los permisos y cierra el documento en otras aplicaciones.",
        "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente.": "El archivo o la carpeta no se encontró. Comprueba la ruta e inténtalo de nuevo.",
        "A imagem é inválida, muito grande para processar com segurança ou usa um formato não suportado.": "La imagen no es válida, es demasiado grande para procesarla de forma segura o usa un formato no compatible.",
        "Não foi possível interpretar o PDF. Ele pode estar danificado ou protegido por senha.": "No se pudo leer el PDF. Puede estar dañado o protegido por contraseña.",
        "Adicionar imagens": "Añadir imágenes",
        "+  Adicionar imagens": "+  Añadir imágenes",
        "Remover selecionadas": "Eliminar seleccionadas",
        "↑  Subir": "↑  Subir",
        "↓  Descer": "↓  Bajar",
        "Duplicar selecionadas": "Duplicar seleccionadas",
        "Resolução:": "Resolución:",
        "Margem:": "Margen:",
        "Incluir todas as páginas/quadros de imagens multipágina ou animadas": "Incluir todas las páginas/fotogramas de imágenes animadas o multipágina",
        "Quando desmarcado, usa somente a primeira página ou o primeiro quadro de cada arquivo.": "Si se desmarca, solo se usa la primera página o el primer fotograma de cada archivo.",
        "Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.": "Formatos: JPG, PNG, BMP, WEBP, TIFF y GIF.",
        "Criar PDF": "Crear PDF",
        "Salv​ar somente as páginas necessárias": "Guardar solo las páginas necesarias",
        "Salvar somente as páginas necessárias": "Guardar solo las páginas necesarias",
        "Escolha o documento e informe os números das páginas ou intervalos que deseja manter.": "Elige el documento e indica los números o intervalos de páginas que deseas conservar.",
        "Arquivo de origem": "Archivo de origen",
        "Páginas": "Páginas",
        "Ex.: 1-3, 5, 8-10": "Ej.: 1-3, 5, 8-10",
        "Senha do PDF (opcional)": "Contraseña del PDF (opcional)",
        "Opcional; não é armazenada": "Opcional; no se guarda",
        "Permitir repetir páginas no PDF resultante": "Permitir repetir páginas en el PDF resultante",
        "A ordem informada será mantida. Intervalos inválidos ou páginas repetidas são recusados.": "Se conserva el orden indicado. Los intervalos inválidos o las páginas repetidas se rechazan.",
        "Corrigir a orientação das páginas": "Corregir la orientación de las páginas",
        "Gire todas as páginas do documento ou informe um intervalo específico. Os conteúdos não são rasterizados.": "Gira todas las páginas o indica un intervalo. El contenido no se rasteriza.",
        "PDF de origem": "PDF de origen",
        "90° no sentido horário": "90° en sentido horario",
        "270° no sentido horário": "270° en sentido horario",
        "Deixe vazio para girar todas as páginas": "Déjalo vacío para girar todas las páginas",
        "Páginas (opcional)": "Páginas (opcional)",
        "Exemplo: 1-2, 5. As páginas não selecionadas permanecem sem rotação.": "Ejemplo: 1-2, 5. Las páginas no seleccionadas no giran.",
        "Dividir o PDF em arquivos menores": "Dividir el PDF en archivos más pequeños",
        "Cada página será salva como um PDF separado. Se algum nome de destino já existir, a operação será interrompida para evitar sobrescrita.": "Cada página se guardará como un PDF separado. Si ya existe un archivo de destino, la operación se detendrá para evitar sobrescribirlo.",
        "Pasta de saída": "Carpeta de salida",
        "Escolher pasta": "Elegir carpeta",
        "Converter e redimensionar imagens": "Convertir y cambiar tamaño de imágenes",
        "Converta várias imagens de uma só vez. O redimensionamento mantém a proporção e nunca amplia imagens pequenas.": "Convierte varias imágenes a la vez. El cambio de tamaño conserva la proporción y no amplía imágenes pequeñas.",
        "Formato de saída": "Formato de salida",
        "Largura máx.": "Ancho máx.",
        "Altura máx.": "Alto máx.",
        "Dimensões (px)": "Dimensiones (px)",
        "Qualidade JPEG/WEBP": "Calidad JPEG/WEBP",
        "Escolher PDF": "Elegir PDF",
        "Escolher pasta de saída": "Elegir carpeta de salida",
        "Escolher pasta para salvar as imagens": "Elegir carpeta para guardar imágenes",
        "Salvar PDF resultante": "Guardar PDF resultante",
        "Escolha outro nome": "Elige otro nombre",
        "O arquivo de saída não pode substituir um dos arquivos de origem.": "El archivo de salida no puede reemplazar uno de los archivos de origen.",
        "Confirmar substituição": "Confirmar reemplazo",
        "O arquivo “{name}” já existe. Deseja substituí-lo?": "El archivo “{name}” ya existe. ¿Deseas reemplazarlo?",
        "Operação cancelada. O arquivo existente foi preservado.": "Operación cancelada. Se conservó el archivo existente.",
        "Operação não concluída": "Operación no completada",
        "Não foi possível concluir a operação: {message}": "No se pudo completar la operación: {message}",
        "A pasta de saída não está disponível.": "La carpeta de salida no está disponible.",
        "Uma operação está em andamento. Aguarde a conclusão antes de fechar o aplicativo.": "Hay una operación en curso. Espera a que termine antes de cerrar la aplicación.",
        "Adicione pelo menos uma imagem primeiro.": "Añade al menos una imagen primero.",
        "Adicione pelo menos dois PDFs.": "Añade al menos dos PDFs.",
        "Selecione pelo menos dois PDFs para unir.": "Selecciona al menos dos PDFs para unir.",
        "Escolha o PDF de origem.": "Elige el PDF de origen.",
        "Senha do PDF": "Contraseña del PDF",
        "O arquivo '{name}' está protegido. Digite a senha:": "El archivo '{name}' está protegido. Introduce la contraseña:",
        "Senha necessária": "Se necesita contraseña",
        "Informe uma senha não vazia para continuar.": "Introduce una contraseña no vacía para continuar.",
        "Não foi possível verificar o PDF": "No se pudo comprobar el PDF",
        "Escolha o PDF e uma pasta de saída.": "Elige el PDF y una carpeta de salida.",
        "Escolha uma pasta de saída existente.": "Elige una carpeta de salida existente.",
        "Página {number}": "Página {number}",
        "Visualize e arraste as páginas para definir a ordem final. Todas as páginas devem permanecer na lista.": "Arrastra las páginas para definir el orden final. Deben permanecer todas las páginas.",
        "Salvar PDF reordenado": "Guardar PDF reordenado",
        "Reordenar PDF": "Reordenar PDF",
        "Escolha um PDF para reorganizar suas páginas.": "Elige un PDF para reorganizar sus páginas.",
        "PDF reordenado: {path}": "PDF reordenado: {path}",
        "Adicionar uma marca d'água de texto, numeração, ou ambos. O conteúdo original não é rasterizado.": "Añade una marca de agua de texto, numeración o ambas. El contenido original no se rasteriza.",
        "Texto da marca d'água": "Texto de la marca de agua",
        "Ex.: CONFIDENCIAL": "Ej.: CONFIDENCIAL",
        "Adicionar numeração de páginas": "Añadir numeración de páginas",
        "Posição da marca d'água": "Posición de la marca de agua",
        "Diagonal (centro)": "Diagonal (centro)",
        "Centralizada": "Centrada",
        "Rodapé central": "Pie centrado",
        "Posição da numeração": "Posición de la numeración",
        "Rodapé direito": "Pie derecho",
        "Rodapé centralizado": "Pie centrado",
        "Tamanho do texto": "Tamaño del texto",
        "Opacidade": "Opacidad",
        "Aplicar marca d'água/numeração": "Aplicar marca de agua/numeración",
        "PDF carimbado: {path}": "PDF marcado: {path}",
        "Informe o texto da marca d'água ou ative a numeração de páginas.": "Escribe el texto de la marca de agua o activa la numeración.",
        "PDF de origem para otimizar": "PDF de origen para optimizar",
        "Escolha entre preservar toda a qualidade (sem perdas) ou reduzir mais o tamanho recomprimindo imagens.": "Elige conservar toda la calidad (sin pérdida) o reducir más el tamaño recomprimiendo imágenes.",
        "Sem perdas (mais conservador)": "Sin pérdida (más conservador)",
        "Equilibrada (recomprimir imagens)": "Equilibrada (recomprimir imágenes)",
        "Qualidade das imagens": "Calidad de las imágenes",
        "Reduzir tamanho do PDF": "Reducir el tamaño del PDF",
        "Otimização sem perdas": "Optimización sin pérdida",
        "Otimização equilibrada": "Optimización equilibrada",
        "PDF otimizado: {old} → {new} ({percent}% de redução)": "PDF optimizado: {old} → {new} ({percent}% menos)",
        "Esta opção recomprime imagens sem transparência; a qualidade visual pode diminuir.": "Esta opción recomprime imágenes sin transparencia; la calidad visual puede disminuir.",
        "Junte documentos em um único arquivo": "Unir documentos en un solo archivo",
        "A ordem dos PDFs na lista será a ordem dos documentos no arquivo final.": "El orden de la lista de PDFs será el orden en el documento final.",
        "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água.": "Elige un documento y define el texto, la posición y la opacidad de la marca de agua.",
        "Escolha o modo de otimização e a qualidade das imagens.": "Elige el modo de optimización y la calidad de imagen.",
        "Modo de otimização": "Modo de optimización",
        "{count} páginas carregadas. Arraste para reorganizar.": "{count} páginas cargadas. Arrastra para reordenar.",
        "Arraste uma página para cima ou para baixo. A numeração indica a página original.": "Arrastra una página hacia arriba o abajo. La etiqueta indica el número de página original.",
        "Não foi possível abrir o PDF": "No se pudo abrir el PDF",
        "Escolher PDF para otimizar": "Elegir PDF para optimizar",
        "Escolher PDF para marca d'água/numeração": "Elegir PDF para marca de agua/numeración",
        "Escolher PDF para reorganizar suas páginas": "Elegir PDF para reorganizar sus páginas",
        "Qualidade": "Calidad",
        "{added} imagem(ns) adicionada(s).": "{added} imagen(es) añadida(s).",
        "Nenhuma imagem nova adicionada.": "No se añadieron imágenes nuevas.",
        "{added} PDF(s) adicionado(s).": "Se añadieron {added} PDF(s).",
        "Nenhum PDF novo adicionado.": "No se añadieron PDF nuevos.",
        "+  Adicionar PDFs": "+  Añadir PDFs",
        "Rotação": "Rotación",
        "Prévia da página selecionada": "Vista previa de la página seleccionada",
        "Selecione uma página para visualizar.": "Selecciona una página para verla.",
        "Não foi possível gerar a prévia desta página.": "No se pudo generar una vista previa de esta página.",
        "Deixe vazio para aplicar em todas as páginas": "Déjalo vacío para aplicar a todas las páginas",
        "O texto e a numeração serão aplicados apenas às páginas selecionadas. A numeração conserva o número original da página.": "El texto y la numeración solo se aplican a las páginas seleccionadas. La numeración conserva el número original de la página.",
        "Páginas marcadas: {ranges}": "Páginas seleccionadas: {ranges}",
        "Remover selecionados": "Eliminar seleccionados",
        "Duplicar selecionados": "Duplicar seleccionados",
        "Selecione pelo menos dois PDFs.": "Selecciona al menos dos PDFs.",
        "Unir documentos em um único arquivo": "Unir documentos en un solo archivo",
        "Transformar imagens em um documento": "Convertir imágenes en un documento",
        "Adicione as imagens e organize a sequência. Cada arquivo será colocado em uma página A4 sem distorcer a proporção.": "Añade las imágenes y organiza la secuencia. Cada archivo se colocará en una página A4 sin deformar sus proporciones.",
        "Reunir documentos em um único arquivo": "Unir documentos en un solo archivo",
        "A otimização sem perdas comprime streams e remove objetos redundantes; a equilibrada também recomprime imagens opacas.": "La optimización sin pérdida comprime los streams y elimina objetos redundantes; la equilibrada también recomprime imágenes opacas.",
        "Unindo os PDFs…": "Uniendo los PDF…",
        "Extraindo páginas…": "Extrayendo páginas…",
        "Girando páginas…": "Girando páginas…",
        "Dividindo PDF em arquivos de página única…": "Dividiendo el PDF en archivos de una página…",
        "Convertendo imagens…": "Convirtiendo imágenes…",
        "{count} páginas salvas em: {directory}": "{count} páginas guardadas en: {directory}",
        "{count} imagem(ns) convertida(s) em {directory}.": "{count} imagen(es) convertida(s) en {directory}.",
        " Falhas: {count}.": " Errores: {count}.",
        "O intervalo '{range}' precisa estar entre 1 e {count}.": "El intervalo '{range}' debe estar entre 1 y {count}.",
        "A página {number} foi informada mais de uma vez.": "La página {number} se indicó más de una vez.",
        "Intervalo de páginas inválido: '{range}'.": "Intervalo de páginas no válido: '{range}'.",
        "A senha informada para o PDF '{name}' está incorreta.": "La contraseña del PDF '{name}' es incorrecta.",
        "A senha informada para o PDF '{name}' está incorreta ou não pôde ser usada.": "La contraseña del PDF '{name}' es incorrecta o no se pudo usar.",
        "O PDF '{name}' exige uma senha. Informe-a para continuar.": "El PDF '{name}' requiere una contraseña. Introdúcela para continuar.",
        "A pasta já contém '{name}'. Escolha outra pasta ou remova os arquivos conflitantes.": "La carpeta ya contiene '{name}'. Elige otra carpeta o elimina los archivos en conflicto.",
        "Fluxo em lote": "Flujo por lotes",
        "Processar um PDF em várias etapas": "Procesar un PDF en varias etapas",
        "Etapas executadas nesta ordem: rotação, marca d'água/numeração e otimização. O arquivo original é preservado.": "Las etapas se ejecutan en este orden: rotación, marca de agua/numeración y optimización. El archivo original se conserva.",
        "Escolher PDF para fluxo em lote": "Elegir PDF para el flujo por lotes",
        "Aplicar rotação": "Aplicar rotación",
        "Aplicar otimização": "Aplicar optimización",
        "Executar fluxo em lote": "Ejecutar flujo por lotes",
        "Executando fluxo em lote…": "Ejecutando flujo por lotes…",
        "Fluxo em lote concluído: {path}": "Flujo por lotes completado: {path}",
        "Selecione pelo menos uma etapa do fluxo.": "Selecciona al menos una etapa del flujo.",
        "A etapa de marca d'água precisa de um texto ou da numeração ativada.": "La etapa de marca de agua necesita texto o que actives la numeración.",
        "Qualquer etapa selecionada será executada na sequência indicada acima.": "Las etapas seleccionadas se ejecutan en el orden indicado arriba.",
        "Texto da marca d'água (opcional)": "Texto de marca de agua (opcional)",
        "Arraste as miniaturas para organizar as páginas. Os números indicam as páginas originais.": "Arrastra las miniaturas para ordenar las páginas. Las etiquetas muestran los números originales.",
        "Salvar perfil": "Guardar perfil",
        "Carregar perfil": "Cargar perfil",
        "Excluir perfil": "Eliminar perfil",
        "Nome do perfil:": "Nombre del perfil:",
        "Selecione um perfil:": "Selecciona un perfil:",
        "Nenhum perfil salvo ainda.": "Aún no hay perfiles guardados.",
        "Informe um nome para o perfil.": "Escribe un nombre para el perfil.",
        "O nome do perfil deve ter até 80 caracteres.": "El nombre del perfil debe tener 80 caracteres o menos.",
        "Já existe um perfil chamado '{name}'. Deseja substituí-lo?": "Ya existe un perfil llamado '{name}'. ¿Quieres reemplazarlo?",
        "O perfil '{name}' já existe, mas usa um esquema que esta versão não reconhece. Substituí-lo pode impedir que versões mais novas recuperem suas opções. Deseja continuar?": "El perfil '{name}' ya existe, pero esta versión no reconoce su esquema. Reemplazarlo puede impedir que versiones más nuevas recuperen sus opciones. ¿Quieres continuar?",
        "Lote pausado após {completed} de {total} arquivo(s).": "Lote en pausa tras {completed} de {total} archivo(s).",
        "Deseja excluir o perfil '{name}'?": "¿Quieres eliminar el perfil '{name}'?",
        "Perfil salvo: {name}": "Perfil guardado: {name}",
        "Perfil carregado: {name}": "Perfil cargado: {name}",
        "Perfil excluído: {name}": "Perfil eliminado: {name}",
        "Os perfis guardam somente as opções do fluxo; não incluem caminho do PDF nem senha.": "Los perfiles solo guardan opciones del flujo; no incluyen la ruta del PDF ni la contraseña.",
        "Não foi possível gerar miniaturas do PDF.": "No se pudieron generar las miniaturas del PDF.",
        "Visualize todas as páginas e arraste para definir a ordem final. Todas as páginas devem permanecer na lista.": "Visualiza todas las miniaturas y arrástralas al orden final. Deben permanecer todas las páginas en la lista.",
        "Exportar perfil": "Exportar perfil",
        "Importar perfil": "Importar perfil",
        "Arquivos JSON (*.json)": "Archivos JSON (*.json)",
        "Nenhum perfil salvo para exportar.": "No hay perfiles guardados para exportar.",
        "Selecione um perfil para exportar:": "Selecciona un perfil para exportar:",
        "Não foi possível salvar o arquivo de perfil. Verifique a pasta e as permissões.": "No se pudo guardar el archivo de perfil. Comprueba la carpeta y los permisos.",
        "Perfil exportado: {name}": "Perfil exportado: {name}",
        "Perfil importado: {name}": "Perfil importado: {name}",
        "O arquivo de perfil não contém um objeto JSON.": "El archivo de perfil no contiene un objeto JSON.",
        "O arquivo contém campos extras ou não reconhecidos.": "El archivo contiene campos adicionales o no reconocidos.",
        "A versão do perfil não é compatível.": "La versión del perfil no es compatible.",
        "O nome do perfil é inválido.": "El nombre del perfil no es válido.",
        "O perfil contém opções ausentes ou campos não reconhecidos.": "El perfil tiene opciones ausentes o campos no reconocidos.",
        "O perfil contém opções com tipos inválidos.": "El perfil contiene opciones con tipos no válidos.",
        "O ângulo de rotação do perfil é inválido.": "El ángulo de rotación del perfil no es válido.",
        "O perfil contém texto inválido ou longo demais.": "El perfil contiene texto no válido o demasiado largo.",
        "O modo de otimização do perfil é inválido.": "El modo de optimización del perfil no es válido.",
        "A qualidade do perfil deve ficar entre 50 e 95.": "La calidad del perfil debe estar entre 50 y 95.",
        "O arquivo de perfil excede o tamanho máximo permitido.": "El archivo de perfil supera el tamaño máximo permitido.",
        "O arquivo não é um perfil JSON válido do PDF Hub. Verifique a versão e as opções do arquivo.": "El archivo no es un perfil JSON válido de PDF Hub. Comprueba la versión y las opciones.",
        "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar.": "El PDF contiene una estructura no compatible o está dañado. Intenta guardar una copia nueva antes de procesarlo.",
        "A imagem não pôde ser processada. Verifique se o arquivo está íntegro e usa um formato compatível.": "No se pudo procesar la imagen. Comprueba que el archivo esté íntegro y tenga un formato compatible.",
        "Não foi possível renderizar o PDF. Ele pode usar recursos não suportados ou estar danificado.": "No se pudo renderizar el PDF. Puede usar funciones no compatibles o estar dañado.",
        "O perfil salvo contém opções inválidas e não pode ser exportado.": "El perfil guardado contiene opciones no válidas y no se puede exportar.",
        "Processar pasta": "Procesar carpeta",
        "Sufixo dos arquivos processados em pasta": "Sufijo de nombres de archivo al procesar carpetas",
        "Pasta de origem": "Carpeta de origen",
        "Pasta de saída": "Carpeta de salida",
        "Escolher pasta de origem": "Elegir carpeta de origen",
        "Escolher pasta de saída": "Elegir carpeta de salida",
        "Incluir subpastas": "Incluir subcarpetas",
        "Retomar lote interrompido, se aplicável": "Reanudar un lote interrumpido cuando sea posible",
        "Usa resultados salvos somente quando a origem, o destino, o perfil e a lista de PDFs não mudaram. Desmarque para iniciar do zero.": "Reutiliza resultados guardados solo si no cambiaron el origen, el destino, el perfil ni la lista de PDF. Desmarca para empezar desde cero.",
        "Concluído antes da interrupção; resultado reutilizado.": "Completado antes de la interrupción; se reutiliza este resultado.",
        "Reprocessar apenas falhas": "Reprocesar solo los PDF fallidos",
        "Não há PDFs com falha para reprocessar.": "No hay PDF fallidos para volver a procesar.",
        "Pausar lote": "Pausar lote",
        "Retomar lote": "Reanudar lote",
        "Cancelar lote": "Cancelar lote",
        "Pausa solicitada; o PDF atual será concluído antes de pausar.": "Pausa solicitada; el PDF actual terminará antes de pausar.",
        "Retomando lote…": "Reanudando lote…",
        "Cancelamento solicitado; o PDF atual será concluído antes de parar.": "Cancelación solicitada; el PDF actual terminará antes de detenerse.",
        "Lote cancelado com segurança após {completed} arquivo(s). O progresso foi preservado; execute novamente com a retomada ativada.": "Lote cancelado de forma segura tras {completed} archivo(s). Se guardó el progreso; vuelve a ejecutarlo con la reanudación activada.",
        "Processar PDFs de uma pasta": "Procesar PDFs de una carpeta",
        "Selecione a pasta de origem e o destino, depois escolha um perfil salvo. Os arquivos originais serão preservados; PDFs com erro não interrompem os demais.": "Elige una carpeta de origen y un destino, y después selecciona un perfil guardado. Se conservan los originales; un PDF con errores no detendrá los demás.",
        "Sufixo usado nos nomes dos PDFs de saída ao processar uma pasta com este perfil.": "Sufijo usado en los nombres de los PDF de salida al procesar una carpeta con este perfil.",
        "Quando ativado, preserva a estrutura de subpastas no destino.": "Si se activa, se conserva la estructura de subcarpetas en el destino.",
        "O perfil também define o sufixo dos arquivos de saída. PDFs que exigem senha serão registrados como falha, sem interromper o lote.": "El perfil también define el sufijo de los archivos de salida. Los PDF que requieran contraseña se registrarán como errores, sin interrumpir el lote.",
        "Aplicar perfil salvo à pasta": "Aplicar perfil guardado a la carpeta",
        "Salvar relatório CSV": "Guardar informe CSV",
        "Arquivo de origem": "Archivo de origen",
        "Resultado": "Resultado",
        "Detalhes": "Detalles",
        "Arquivo de saída": "Archivo de salida",
        "Sucesso": "Correcto",
        "Falha": "Error",
        "Processado com sucesso.": "Procesado correctamente.",
        "Selecione uma pasta de origem.": "Selecciona una carpeta de origen.",
        "A pasta selecionada não contém arquivos PDF.": "La carpeta seleccionada no contiene archivos PDF.",
        "A pasta de saída não pode ser a pasta de origem nem ficar dentro dela.": "La carpeta de salida no puede ser la carpeta de origen ni estar dentro de ella.",
        "Nenhum perfil salvo para aplicar.": "No hay ningún perfil guardado para aplicar.",
        "Selecione o perfil a aplicar:": "Selecciona el perfil que deseas aplicar:",
        "Histórico de relatórios": "Historial de informes",
        "Relatórios anteriores": "Informes anteriores",
        "Carregar relatório": "Cargar informe",
        "Excluir relatório selecionado": "Eliminar el informe seleccionado",
        "Não há relatórios salvos.": "No hay informes guardados.",
        "Selecione um relatório para carregar.": "Selecciona un informe para cargar.",
        "Relatório {date} — {total} PDF(s), {failed} falha(s) — perfil: {profile}": "Informe {date} — {total} PDF(s), {failed} fallos — perfil: {profile}",
        "Histórico de relatórios restaurado.": "Se restauró el historial de informes.",
        "Relatório histórico carregado.": "Informe histórico cargado.",
        "Relatório removido do histórico.": "Informe eliminado del historial.",
        "Não foi possível ler o relatório histórico.": "No se pudo leer el informe histórico.",
        "Não foi possível excluir o relatório histórico.": "No se pudo eliminar el informe histórico.",
        "Não foi possível armazenar o relatório no histórico local.": "No se pudo guardar el informe en el historial local.",
        "Processando arquivo {completed} de {total}: {name}": "Procesando archivo {completed} de {total}: {name}",
        "Lote concluído: {success} sucesso(s), {failed} falha(s) de {total} PDF(s).": "Lote completado: {success} correcto(s), {failed} error(es) de {total} PDF(s).",
        "Pronto. Selecione uma ferramenta no menu lateral.": "Listo. Elige una herramienta en el menú lateral.",
        "Não há relatório para exportar.": "No hay ningún informe para exportar.",
        "Relatório salvo: {path}": "Informe guardado: {path}",
        "Não foi possível salvar o relatório CSV. Verifique a pasta e as permissões.": "No se pudo guardar el informe CSV. Comprueba la carpeta y los permisos.",
        "Arquivos CSV (*.csv)": "Archivos CSV (*.csv)",
        "O sufixo de saída contém caracteres inválidos ou é longo demais.": "El sufijo de salida contiene caracteres no válidos o es demasiado largo.",
        "Não foi possível gerar o relatório individual do lote.": "No se pudo generar el informe individual del lote.",
        "Configurações": "Configuración",
        "Defina o idioma, o tema visual e as permissões dos arquivos gerados.": "Elige el idioma de la interfaz, el tema visual y los permisos de los archivos generados.",
        "As permissões de saída se aplicam aos arquivos que o PDF Hub cria. O modo 0600 é a opção mais restritiva.": "Los permisos de salida se aplican a los archivos creados por PDF Hub. El modo 0600 es la opción más restrictiva.",
        "Modo de aparência": "Apariencia",
        "Modo claro": "Modo claro",
        "Modo escuro": "Modo oscuro",
        "Sobre permissões de saída": "Acerca de los permisos de salida",
        "0600 permite leitura e escrita apenas pelo usuário atual. 0644 permite que outros usuários locais leiam o arquivo. Isso afeta os arquivos gerados em Linux/macOS; no Windows, as permissões são gerenciadas pelo sistema.": "0600 permite que solo el usuario actual lea y escriba el archivo. 0644 permite que otros usuarios locales lo lean. Esto afecta a los archivos creados en Linux/macOS; en Windows, los permisos los gestiona el sistema operativo.",
        "Arraste imagens para esta área ou use “Adicionar imagens”.": "Arrastra imágenes aquí o usa «Añadir imágenes».",
        "Resolução estimada automaticamente a partir das dimensões em pixels das imagens; você pode ajustá-la manualmente.": "Resolución estimada automáticamente a partir de las dimensiones en píxeles de las imágenes; puedes ajustarla manualmente.",
        "Calculando resolução a partir das imagens.": "Calculando la resolución a partir de las imágenes.",
        "Resolução recomendada calculada a partir das imagens.": "Resolución recomendada calculada a partir de las imágenes.",
    }
}


SUPPORTED_IMAGE_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif",
}


def create_app_icon() -> QIcon:
    """Draw a recognizable PDF-document icon without external image assets."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(size / 64.0, size / 64.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#172B4D"))
        painter.drawRoundedRect(2, 2, 60, 60, 12, 12)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(14, 7, 37, 48, 4, 4)
        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.drawLine(21, 18, 43, 18)
        painter.drawLine(21, 25, 43, 25)
        painter.drawLine(21, 32, 36, 32)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#DC2626"))
        painter.drawRoundedRect(11, 39, 42, 15, 3, 3)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(11, 39, 42, 15, Qt.AlignmentFlag.AlignCenter, "PDF")
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def create_reorder_pages_icon(theme: str = "light") -> QIcon:
    """Draw a high-contrast reorder glyph that stays visible in either theme."""
    color = QColor("#344054" if theme != "dark" else "#E5E7EB")
    icon = QIcon()
    for size in (18, 24, 36):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.scale(size / 24.0, size / 24.0)
        painter.setPen(QPen(color, 2))
        painter.drawLine(3, 5, 14, 5)
        painter.drawLine(3, 12, 14, 12)
        painter.drawLine(3, 19, 14, 19)
        painter.drawLine(16, 9, 20, 12)
        painter.drawLine(20, 12, 16, 15)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


TRANSLATIONS["en"].update({
    "Excluir páginas": "Delete pages",
    "Excluir páginas de um PDF": "Delete pages from a PDF",
    "Informe as páginas que deseja remover. O PDF original será preservado e o resultado será salvo em outro arquivo.": "Enter the pages to remove. The original PDF will be preserved and the result saved to a separate file.",
    "Páginas a excluir": "Pages to delete",
    "Ex.: 2, 4-6, 9": "e.g. 2, 4-6, 9",
    "Use números ou intervalos, como 2, 4-6. É necessário manter pelo menos uma página no PDF resultante.": "Enter page numbers or ranges, such as 2, 4-6. At least one page must remain in the output PDF.",
    "Escolher PDF para excluir páginas": "Choose PDF to delete pages",
    "Informe as páginas que deseja excluir.": "Enter the pages you want to delete.",
    "A exclusão precisa manter pelo menos uma página no PDF.": "At least one page must remain in the PDF.",    "PDF para imagens": "PDF to images",
    "Exportar páginas de PDF como imagens": "Export PDF pages as images",
    "Exporte todas as páginas ou apenas os intervalos escolhidos como arquivos PNG/JPEG.": "Export every page or selected ranges as PNG/JPEG image files.",
    "PDF de origem para exportar": "Source PDF to export",
    "Páginas (opcional)": "Pages (optional)",
    "Deixe vazio para exportar todas as páginas": "Leave blank to export every page",
    "Formato das imagens": "Image format",
    "Resolução de saída": "Output resolution",
    "Qualidade JPEG": "JPEG quality",
    "Senha do PDF (opcional)": "PDF password (optional)",
    "Pasta para salvar as imagens": "Folder to save images",
    "Exportar páginas": "Export pages",
    "Exportando páginas do PDF como imagens…": "Exporting PDF pages as images…",
    "Escolher PDF para exportar imagens": "Choose PDF to export as images",
    "Escolher pasta para salvar as imagens": "Choose folder to save images",
    "Informe páginas, por exemplo: 1-3, 5, 8-10.": "Enter pages, e.g. 1-3, 5, 8-10.",
    "A página {number} foi informada mais de uma vez.": "Page {number} was specified more than once.",
    "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta.": "Could not open the PDF. Check that the file is valid and the password is correct.",
    "A resolução precisa ficar entre 72 e 600 DPI.": "Resolution must be between 72 and 600 DPI.",
    "A qualidade JPEG precisa ficar entre 1 e 100.": "JPEG quality must be between 1 and 100.",
    "Escolha PNG ou JPEG para exportar as páginas.": "Choose PNG or JPEG for page export.",
    "Não foi possível renderizar a página {number}.": "Could not render page {number}.",
    "Exportadas {count} página(s) para imagens em {directory}.": "Exported {count} page(s) to images in {directory}.",
    "Modo de divisão": "Split method",
    "Um arquivo por página": "One file per page",
    "A cada N páginas": "Every N pages",
    "Páginas por arquivo": "Pages per file",
    "Após páginas específicas": "After selected pages",
    "Páginas após as quais dividir": "Pages after which to split",
    "Ex.: 2, 5, 10": "e.g. 2, 5, 10",
    "Após páginas pares": "After even pages",
    "Após páginas ímpares": "After odd pages",
    "Por tamanho aproximado": "By approximate size",
    "Tamanho alvo por arquivo": "Target size per file",
    "Por marcadores do sumário": "By bookmarks (outline)",
    "Nível do marcador": "Bookmark level",
    "Filtrar marcador (expressão regular, opcional)": "Filter bookmark title (optional regex)",
    "Filtro opcional; use uma expressão regular": "Optional filter; enter a regular expression",
    "Divida o PDF por página, grupos de páginas, tamanho aproximado ou marcadores do sumário.": "Split by page, page groups, approximate size or document bookmarks.",
    "O tamanho é aproximado; um PDF de uma única página pode exceder o limite.": "The size is approximate; a single-page PDF may exceed the target.",
    "O modo equilibrado recomprime imagens sem transparência; a qualidade visual pode diminuir. A redução depende do conteúdo do PDF.": "Balanced mode recompresses opaque images; visual quality may decrease. Reduction depends on PDF content.",
    "O modo sem perdas não altera a qualidade das imagens; use o modo equilibrado para aplicar este valor.": "Lossless mode does not change image quality; use balanced mode to apply this value.",
    "PDF otimizado: {old} → {new} ({percent}% menor)": "PDF optimized: {old} → {new} ({percent}% smaller)",
    "PDF otimizado: {old} → {new} ({percent}% maior)": "PDF optimized: {old} → {new} ({percent}% larger)",
    "PDF otimizado: {old} → {new} (tamanho igual)": "PDF optimized: {old} → {new} (same size)",
    "Modo de divisão inválido.": "Invalid split method.",
    "O número de páginas por arquivo deve ser positivo.": "Pages per file must be a positive number.",
    "Informe páginas após as quais dividir, por exemplo: 2, 5, 8.": "Enter page numbers after which to split, e.g. 2, 5, 8.",
    "O tamanho alvo precisa ser maior que zero.": "The target size must be greater than zero.",
    "O nível do marcador precisa ser um inteiro positivo.": "Bookmark level must be a positive integer.",
    "A expressão regular para filtrar marcadores é inválida.": "The bookmark filter is not a valid regular expression.",
    "O PDF não contém marcadores no nível solicitado (ou nenhum corresponde ao filtro).": "The PDF has no bookmarks at the selected level (or none match the filter).",
    "Não foi possível gerar divisões a partir das opções informadas.": "Could not create split files from the selected options.",
    "Dividindo PDF em arquivos…": "Splitting PDF into files…",
    "{count} arquivos criados em: {directory}": "{count} files created in: {directory}"
});
TRANSLATIONS["es"].update({
    "Excluir páginas": "Eliminar páginas",
    "Excluir páginas de um PDF": "Eliminar páginas de un PDF",
    "Informe as páginas que deseja remover. O PDF original será preservado e o resultado será salvo em outro arquivo.": "Indica las páginas que deseas eliminar. El PDF original se conservará y el resultado se guardará en otro archivo.",
    "Páginas a excluir": "Páginas que eliminar",
    "Ex.: 2, 4-6, 9": "Ej.: 2, 4-6, 9",
    "Use números ou intervalos, como 2, 4-6. É necessário manter pelo menos uma página no PDF resultante.": "Introduce números o intervalos, como 2, 4-6. Debe quedar al menos una página en el PDF resultante.",
    "Escolher PDF para excluir páginas": "Elegir PDF para eliminar páginas",
    "Informe as páginas que deseja excluir.": "Indica las páginas que deseas eliminar.",
    "A exclusão precisa manter pelo menos uma página no PDF.": "Debe quedar al menos una página en el PDF.",    "PDF para imagens": "PDF a imágenes",
    "Exportar páginas de PDF como imagens": "Exportar páginas PDF como imágenes",
    "Exporte todas as páginas ou apenas os intervalos escolhidos como arquivos PNG/JPEG.": "Exporta todas las páginas o solo los intervalos elegidos como archivos PNG/JPEG.",
    "PDF de origem para exportar": "PDF de origen para exportar",
    "Páginas (opcional)": "Páginas (opcional)",
    "Deixe vazio para exportar todas as páginas": "Déjalo vacío para exportar todas las páginas",
    "Formato das imagens": "Formato de imagen",
    "Resolução de saída": "Resolución de salida",
    "Qualidade JPEG": "Calidad JPEG",
    "Senha do PDF (opcional)": "Contraseña del PDF (opcional)",
    "Pasta para salvar as imagens": "Carpeta para guardar las imágenes",
    "Exportar páginas": "Exportar páginas",
    "Exportando páginas do PDF como imagens…": "Exportando páginas del PDF como imágenes…",
    "Escolher PDF para exportar imagens": "Elegir PDF para exportar imágenes",
    "Escolher pasta para salvar as imagens": "Elegir carpeta para guardar las imágenes",
    "Informe páginas, por exemplo: 1-3, 5, 8-10.": "Indica las páginas, por ejemplo: 1-3, 5, 8-10.",
    "A página {number} foi informada mais de uma vez.": "La página {number} se indicó más de una vez.",
    "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta.": "No se pudo abrir el PDF. Comprueba que el archivo sea válido y que la contraseña sea correcta.",
    "A resolução precisa ficar entre 72 e 600 DPI.": "La resolución debe estar entre 72 y 600 DPI.",
    "A qualidade JPEG precisa ficar entre 1 e 100.": "La calidad JPEG debe estar entre 1 y 100.",
    "Escolha PNG ou JPEG para exportar as páginas.": "Elige PNG o JPEG para exportar las páginas.",
    "Não foi possível renderizar a página {number}.": "No se pudo renderizar la página {number}.",
    "Exportadas {count} página(s) para imagens em {directory}.": "Se exportaron {count} página(s) como imágenes en {directory}.",
    "Modo de divisão": "Método de división",
    "Um arquivo por página": "Un archivo por página",
    "A cada N páginas": "Cada N páginas",
    "Páginas por arquivo": "Páginas por archivo",
    "Após páginas específicas": "Después de páginas concretas",
    "Páginas após as quais dividir": "Páginas después de las que dividir",
    "Ex.: 2, 5, 10": "Ej.: 2, 5, 10",
    "Após páginas pares": "Después de páginas pares",
    "Após páginas ímpares": "Después de páginas impares",
    "Por tamanho aproximado": "Por tamaño aproximado",
    "Tamanho alvo por arquivo": "Tamaño objetivo por archivo",
    "Por marcadores do sumário": "Por marcadores del índice",
    "Nível do marcador": "Nivel del marcador",
    "Filtrar marcador (expressão regular, opcional)": "Filtrar marcador (expresión regular, opcional)",
    "Filtro opcional; use uma expressão regular": "Filtro opcional; introduce una expresión regular",
    "Divida o PDF por página, grupos de páginas, tamanho aproximado ou marcadores do sumário.": "Divide por página, grupos de páginas, tamaño aproximado o marcadores del índice.",
    "O tamanho é aproximado; um PDF de uma única página pode exceder o limite.": "El tamaño es aproximado; un PDF de una sola página puede superar el límite.",
    "O modo equilibrado recomprime imagens sem transparência; a qualidade visual pode diminuir. A redução depende do conteúdo do PDF.": "El modo equilibrado recomprime imágenes opacas; la calidad visual puede disminuir. La reducción depende del contenido del PDF.",
    "O modo sem perdas não altera a qualidade das imagens; use o modo equilibrado para aplicar este valor.": "El modo sin pérdida no cambia la calidad de las imágenes; usa el modo equilibrado para aplicar este valor.",
    "PDF otimizado: {old} → {new} ({percent}% menor)": "PDF optimizado: {old} → {new} ({percent}% más pequeño)",
    "PDF otimizado: {old} → {new} ({percent}% maior)": "PDF optimizado: {old} → {new} ({percent}% más grande)",
    "PDF otimizado: {old} → {new} (tamanho igual)": "PDF optimizado: {old} → {new} (mismo tamaño)",
    "Modo de divisão inválido.": "Método de división no válido.",
    "O número de páginas por arquivo deve ser positivo.": "Las páginas por archivo deben ser un número positivo.",
    "Informe páginas após as quais dividir, por exemplo: 2, 5, 8.": "Indica las páginas después de las que dividir, por ejemplo: 2, 5, 8.",
    "O tamanho alvo precisa ser maior que zero.": "El tamaño objetivo debe ser mayor que cero.",
    "O nível do marcador precisa ser um inteiro positivo.": "El nivel del marcador debe ser un entero positivo.",
    "A expressão regular para filtrar marcadores é inválida.": "El filtro de marcadores no es una expresión regular válida.",
    "O PDF não contém marcadores no nível solicitado (ou nenhum corresponde ao filtro).": "El PDF no tiene marcadores en el nivel indicado (o ninguno coincide con el filtro).",
    "Não foi possível gerar divisões a partir das opções informadas.": "No se pudieron crear divisiones con las opciones seleccionadas.",
    "Dividindo PDF em arquivos…": "Dividiendo el PDF en archivos…",
    "{count} arquivos criados em: {directory}": "{count} archivos creados en: {directory}"
});

TRANSLATIONS["en"].update({
    "Para GIF/TIFF/WebP com vários quadros, a conversão usa somente o primeiro quadro.": "For GIF/TIFF/WebP files with multiple frames, conversion uses only the first frame.",
    "Perfis de fluxo": "Pipeline profiles",
    "Não foi possível alterar os perfis porque as configurações estão inválidas. Os dados existentes foram preservados.": "The profiles could not be changed because the settings are invalid. Existing data was preserved.",
    "Reordenar páginas": "Reorder pages",
    "Marca d'água e numeração": "Watermark and page numbers",
    "Otimizar PDF": "Optimize PDF",
    "Escolha um PDF para reorganizar suas páginas. Visualize todas as páginas e arraste para definir a ordem final; todas devem permanecer na lista.": "Choose a PDF to reorder. Preview all pages and drag to set their final order; all pages must remain in the list.",
    "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água. O conteúdo original não é rasterizado.": "Choose a document and set the watermark text, position, and opacity. Original content is not rasterized.",
    "Escolha entre preservar a qualidade (sem perdas) ou reduzir o tamanho recomprimindo imagens. O modo sem perdas comprime streams e remove objetos redundantes; o modo equilibrado também recomprime imagens opacas.": "Choose between preserving quality (lossless) or reducing file size by recompressing images. Lossless mode compresses streams and removes redundant objects; balanced mode also recompresses opaque images.",
    "Adicionar PDFs": "Add PDFs",
    "Escolher PDF para extrair páginas": "Choose PDF to extract pages",
    "Escolher PDF para girar": "Choose PDF to rotate",
    "Escolher PDF para dividir": "Choose PDF to split",
    "A marca d'água contém caracteres não suportados pela fonte padrão. Use caracteres latinos e símbolos compatíveis.": "The watermark contains characters unsupported by the built-in font. Use Latin characters and compatible symbols.",
    "O texto da marca d'água é longo demais para caber na página. Reduza o texto ou use uma posição central.": "The watermark is too long to fit on the page. Shorten the text or use a centered position.",
    "Não foi possível concluir a operação. Os detalhes internos foram ocultados.": "The operation could not be completed. Internal details were hidden.",
    "Um arquivo de destino já existe. Escolha outra pasta ou nome.": "A destination file already exists. Choose another folder or name.",
    "A senha do PDF está incorreta ou não foi informada.": "The PDF password is incorrect or was not provided.",
    "Não foi possível verificar se o PDF exige senha. O arquivo pode estar danificado.": "Could not determine whether the PDF requires a password. The file may be damaged.",
    "A página ultrapassa o limite seguro de pixels. Reduza a resolução de saída.": "The page exceeds the safe pixel limit. Reduce the output resolution.",
})
TRANSLATIONS["es"].update({
    "Para GIF/TIFF/WebP com vários quadros, a conversão usa somente o primeiro quadro.": "Para archivos GIF/TIFF/WebP con varios fotogramas, la conversión usa solo el primero.",
    "Perfis de fluxo": "Perfiles del flujo",
    "Não foi possível alterar os perfis porque as configurações estão inválidas. Os dados existentes foram preservados.": "No se pudieron modificar los perfiles porque la configuración no es válida. Se conservaron los datos existentes.",
    "Reordenar páginas": "Reordenar páginas",
    "Marca d'água e numeração": "Marca de agua y numeración",
    "Otimizar PDF": "Optimizar PDF",
    "Escolha um PDF para reorganizar suas páginas. Visualize todas as páginas e arraste para definir a ordem final; todas devem permanecer na lista.": "Elige un PDF para reordenarlo. Previsualiza todas las páginas y arrástralas para fijar el orden final; deben permanecer todas en la lista.",
    "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água. O conteúdo original não é rasterizado.": "Elige un documento y define el texto, la posición y la opacidad de la marca de agua. El contenido original no se rasteriza.",
    "Escolha entre preservar a qualidade (sem perdas) ou reduzir o tamanho recomprimindo imagens. O modo sem perdas comprime streams e remove objetos redundantes; o modo equilibrado também recomprime imagens opacas.": "Elige entre conservar la calidad (sin pérdida) o reducir el tamaño recomprimiendo imágenes. El modo sin pérdida comprime flujos y elimina objetos redundantes; el modo equilibrado también recomprime imágenes opacas.",
    "Adicionar PDFs": "Añadir PDF",
    "Escolher PDF para extrair páginas": "Elegir PDF para extraer páginas",
    "Escolher PDF para girar": "Elegir PDF para girar",
    "Escolher PDF para dividir": "Elegir PDF para dividir",
    "A marca d'água contém caracteres não suportados pela fonte padrão. Use caracteres latinos e símbolos compatíveis.": "La marca de agua contiene caracteres no compatibles con la fuente integrada. Usa caracteres latinos y símbolos compatibles.",
    "O texto da marca d'água é longo demais para caber na página. Reduza o texto ou use uma posição central.": "La marca de agua es demasiado larga para caber en la página. Acorta el texto o usa una posición centrada.",
    "Não foi possível concluir a operação. Os detalhes internos foram ocultados.": "No se pudo completar la operación. Se ocultaron los detalles internos.",
    "Um arquivo de destino já existe. Escolha outra pasta ou nome.": "Ya existe un archivo de destino. Elige otra carpeta o nombre.",
    "A senha do PDF está incorreta ou não foi informada.": "La contraseña del PDF es incorrecta o no se proporcionó.",
    "Não foi possível verificar se o PDF exige senha. O arquivo pode estar danificado.": "No se pudo determinar si el PDF requiere contraseña. El archivo puede estar dañado.",
    "A página ultrapassa o limite seguro de pixels. Reduza a resolução de saída.": "La página supera el límite seguro de píxeles. Reduce la resolución de salida.",
})

TRANSLATIONS["en"].update({
    "Arraste imagens para esta área ou use “Adicionar imagens”. Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.": "Drop images here or use “Add images”. Formats: JPG, PNG, BMP, WEBP, TIFF and GIF.",
    "Não houve redução de tamanho: {old} → {new}": "No size reduction: {old} → {new}",
    "O PDF foi alterado desde a seleção. Escolha o arquivo novamente antes de reordenar.": "The PDF has changed since it was selected. Choose the file again before reordering.",
    "Não foi possível acessar o PDF de origem. Escolha o arquivo novamente.": "The source PDF is no longer available. Choose the file again.",
    "Prévia indisponível para este PDF.": "Preview is unavailable for this PDF.",
})
TRANSLATIONS["es"].update({
    "Arraste imagens para esta área ou use “Adicionar imagens”. Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.": "Suelta imágenes aquí o usa “Añadir imágenes”. Formatos: JPG, PNG, BMP, WEBP, TIFF y GIF.",
    "Criando PDF a partir das imagens…": "Creando PDF a partir de las imágenes…",
    "Não houve redução de tamanho: {old} → {new}": "No se redujo el tamaño: {old} → {new}",
    "O PDF foi alterado desde a seleção. Escolha o arquivo novamente antes de reordenar.": "El PDF cambió desde que se seleccionó. Elige el archivo de nuevo antes de reordenarlo.",
    "Não foi possível acessar o PDF de origem. Escolha o arquivo novamente.": "El PDF de origen ya no está disponible. Elige el archivo de nuevo.",
    "Prévia indisponível para este PDF.": "La vista previa no está disponible para este PDF.",
})


TRANSLATIONS["en"].update({
        "O PDF não possui páginas.": "The PDF has no pages.",
        "Informe páginas, por exemplo: 1-3, 5, 8-10.": "Enter pages, for example: 1-3, 5, 8-10.",
        "O intervalo '{segment}' precisa estar entre 1 e {page_count}.": "Range '{segment}' must be between 1 and {page_count}.",
        "Há um item vazio na lista de páginas.": "The page list contains an empty item.",
        "Intervalo de páginas inválido: '{segment}'.": "Invalid page range: '{segment}'.",
        "O intervalo '{segment}' está invertido: a página inicial não pode ser maior que a final.": "Range '{segment}' is reversed: the first page cannot exceed the last.",
        "A página {page_number} foi informada mais de uma vez.": "Page {page_number} was specified more than once.",
        "Selecione pelo menos um arquivo de origem.": "Select at least one source file.",
        "O caminho de saída é uma pasta, não um arquivo PDF.": "The output path is a folder, not a PDF file.",
        "O arquivo de saída precisa ter a extensão .pdf.": "The output file must use the .pdf extension.",
        "A pasta de destino não existe.": "The destination folder does not exist.",
        "O arquivo de saída não pode substituir um arquivo de origem.": "The output file cannot replace a source file.",
        "Arquivo não encontrado: {missing[0]}": "File not found: {missing[0]}",
        "As permissões de saída devem ser 0600 (somente usuário) ou 0644 (compartilhadas).": "Output permissions must be 0600 (owner only) or 0644 (shared).",
        "O arquivo PDF temporário ficou vazio.": "The temporary PDF file is empty.",
        "A senha informada para o PDF '{path.name}' está incorreta.": "The password for PDF '{path.name}' is incorrect.",
        "O PDF '{path.name}' exige uma senha. Informe-a para continuar.": "PDF '{path.name}' requires a password. Enter it to continue.",
        "O PDF '{path.name}' não contém páginas.": "PDF '{path.name}' has no pages.",
        "Não foi possível verificar se o PDF exige senha. O arquivo pode estar danificado.": "Could not determine whether the PDF requires a password. The file may be damaged.",
        "As margens não deixam espaço suficiente na página.": "The margins do not leave enough space on the page.",
        "Adicione pelo menos uma imagem.": "Add at least one image.",
        "A resolução precisa ficar entre 72 e 600 DPI.": "Resolution must be between 72 and 600 DPI.",
        "A margem precisa ficar entre 0 e 40 mm.": "The margin must be between 0 and 40 mm.",
        "O arquivo de saída não pode substituir uma imagem de origem.": "The output file cannot replace a source image.",
        "Imagem não encontrada: {source}": "Image not found: {source}",
        "Formato de imagem não suportado: {source.name}": "Unsupported image format: {source.name}",
        "Selecione pelo menos dois PDFs para unir.": "Select at least two PDFs to merge.",
        "Informe uma senha por PDF ou deixe a senha como None.": "Enter a password for each PDF or leave it as None.",
        "Informe um intervalo de páginas por PDF ou deixe None para usar todas.": "Enter a page range for each PDF or leave it as None to use all pages.",
        "O número de páginas por bloco deve ser positivo.": "The number of pages per block must be positive.",
        "O intervalo entre inserções deve ser positivo.": "The insertion interval must be positive.",
        "O intervalo entre inserções não pode exceder o número de páginas do PDF de destino.": "The insertion interval cannot exceed the number of pages in the destination PDF.",
        "A exclusão precisa manter pelo menos uma página no PDF.": "Deleting pages must leave at least one page in the PDF.",
        "Escolha uma rotação de 90, 180 ou 270 graus.": "Choose a rotation of 90, 180, or 270 degrees.",
        "Modo de divisão inválido.": "Invalid split mode.",
        "O número de páginas por arquivo deve ser positivo.": "The number of pages per file must be positive.",
        "O tamanho alvo precisa ser um número finito maior que zero.": "The target size must be finite and greater than zero.",
        "O nível do marcador precisa ser um inteiro positivo.": "The bookmark level must be a positive integer.",
        "A expressão regular para filtrar marcadores é inválida.": "The regular expression for filtering bookmarks is invalid.",
        "PDF não encontrado: {source}": "PDF not found: {source}",
        "O arquivo de origem precisa ser PDF.": "The source file must be a PDF.",
        "Informe páginas após as quais dividir, por exemplo: 2, 5, 8.": "Enter the pages after which to split, for example: 2, 5, 8.",
        "Não foi possível estimar o tamanho armazenado da página {page_number}.": "Could not estimate the stored size of page {page_number}.",
        "O PDF não contém marcadores no nível solicitado (ou nenhum corresponde ao filtro).": "The PDF has no bookmarks at the requested level (or none match the filter).",
        "Não foi possível gerar divisões a partir das opções informadas.": "Could not create split files from the supplied options.",
        "Não foi possível criar a pasta de destino.": "Could not create the destination folder.",
        "A pasta já contém '{conflicts[0]}'. Escolha outra pasta ou remova os arquivos conflitantes.": "The folder already contains '{conflicts[0]}'. Choose another folder or remove conflicting files.",
        "Formato de saída não suportado: {output_format}": "Unsupported output format: {output_format}",
        "A extensão de saída não corresponde ao formato {image_format}.": "The output extension does not match format {image_format}.",
        "A largura máxima precisa ser maior que zero.": "Maximum width must be greater than zero.",
        "A altura máxima precisa ser maior que zero.": "Maximum height must be greater than zero.",
        "A qualidade precisa ficar entre 1 e 100.": "Quality must be between 1 and 100.",
        "O arquivo de imagem temporário ficou vazio.": "The temporary image file is empty.",
        "A ordem deve conter cada página uma única vez, de 1 a {count}.": "The order must contain every page exactly once, from 1 to {count}.",
        "A qualidade JPEG precisa ficar entre 50 e 95.": "JPEG quality must be between 50 and 95.",
        "O tamanho da fonte precisa ficar entre 8 e 120.": "Font size must be between 8 and 120.",
        "A opacidade precisa ficar entre 0,05 e 1.": "Opacity must be between 0.05 and 1.",
        "Posição de marca d'água inválida.": "Invalid watermark position.",
        "Posição de numeração inválida.": "Invalid page-number position.",
        "O texto da marca d'água é longo demais para caber na página. Reduza o texto ou use uma posição central.": "The watermark text is too long to fit on the page. Shorten it or use a centered position.",
        "Selecione pelo menos uma etapa para executar o fluxo em lote.": "Select at least one step to run the batch workflow.",
        "Escolha PNG ou JPEG para exportar as páginas.": "Choose PNG or JPEG to export pages.",
        "Escolha um arquivo PDF existente.": "Choose an existing PDF file.",
        "Escolha uma pasta de saída existente.": "Choose an existing output folder.",
        "A qualidade JPEG precisa ficar entre 1 e 100.": "JPEG quality must be between 1 and 100.",
        "A senha do PDF está incorreta ou não foi informada.": "The PDF password is incorrect or was not provided.",
        "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta.": "Could not open the PDF. Check that the file is valid and the password is correct.",
        "Não foi possível obter o tamanho da página {page_index + 1}.": "Could not get the size of page {page_index + 1}.",
        "A página ultrapassa o limite seguro de pixels. Reduza a resolução de saída.": "The page exceeds the safe pixel limit. Reduce the output resolution.",
        "Não foi possível renderizar a página {page_index + 1}.": "Could not render page {page_index + 1}.",
        "Não foi possível salvar a imagem da página {page_index + 1}.": "Could not save the image for page {page_index + 1}.",
        "Selecione uma pasta de origem.": "Select a source folder.",
        "A pasta de saída não pode ser a pasta de origem nem ficar dentro dela.": "The output folder cannot be the source folder or a folder inside it.",
        "Selecione pelo menos uma etapa do fluxo.": "Select at least one workflow step.",
        "A etapa de marca d'água precisa de um texto ou da numeração ativada.": "The watermark step requires text or enabled page numbering.",
        "A pasta selecionada não contém arquivos PDF.": "The selected folder contains no PDF files.",
        "Não há PDFs selecionados para reprocessar.": "No PDFs are selected for reprocessing.",
        "Identificador de relatório inválido.": "Invalid report identifier.",
        "O relatório do lote contém dados inválidos.": "The batch report contains invalid data.",
        "Criando PDF a partir das imagens": "Creating PDF from images",
        "Abra esta pasta manualmente:\n{path}": "Open this folder manually:\n{path}",
        "Escolha otimização sem perdas ou equilibrada.": "Choose lossless or balanced optimization.",
        "Processamento local:": "Local processing:",
        "Já existe um perfil chamado '{name}'. Deseja substituí-lo?": "A profile named '{name}' already exists. Replace it?",
        "Não foi possível concluir a operação: {message}": "Could not complete the operation: {message}",
        "Há um lote em andamento. Cancelar o lote e sair?": "A batch is running. Cancel the batch and exit?",
        "Falhas: {count}.": "Failures: {count}.",
})
TRANSLATIONS["es"].update({
        "O PDF não possui páginas.": "El PDF no tiene páginas.",
        "Informe páginas, por exemplo: 1-3, 5, 8-10.": "Indica páginas, por ejemplo: 1-3, 5, 8-10.",
        "O intervalo '{segment}' precisa estar entre 1 e {page_count}.": "El intervalo '{segment}' debe estar entre 1 y {page_count}.",
        "Há um item vazio na lista de páginas.": "La lista de páginas contiene un elemento vacío.",
        "Intervalo de páginas inválido: '{segment}'.": "Intervalo de páginas no válido: '{segment}'.",
        "O intervalo '{segment}' está invertido: a página inicial não pode ser maior que a final.": "El intervalo '{segment}' está invertido: la página inicial no puede ser mayor que la final.",
        "A página {page_number} foi informada mais de uma vez.": "La página {page_number} se indicó más de una vez.",
        "Selecione pelo menos um arquivo de origem.": "Selecciona al menos un archivo de origen.",
        "O caminho de saída é uma pasta, não um arquivo PDF.": "La ruta de salida es una carpeta, no un archivo PDF.",
        "O arquivo de saída precisa ter a extensão .pdf.": "El archivo de salida debe tener la extensión .pdf.",
        "A pasta de destino não existe.": "La carpeta de destino no existe.",
        "O arquivo de saída não pode substituir um arquivo de origem.": "El archivo de salida no puede reemplazar un archivo de origen.",
        "Arquivo não encontrado: {missing[0]}": "Archivo no encontrado: {missing[0]}",
        "As permissões de saída devem ser 0600 (somente usuário) ou 0644 (compartilhadas).": "Los permisos de salida deben ser 0600 (solo propietario) o 0644 (compartidos).",
        "O arquivo PDF temporário ficou vazio.": "El archivo PDF temporal está vacío.",
        "A senha informada para o PDF '{path.name}' está incorreta.": "La contraseña del PDF '{path.name}' es incorrecta.",
        "O PDF '{path.name}' exige uma senha. Informe-a para continuar.": "El PDF '{path.name}' requiere una contraseña. Indícala para continuar.",
        "O PDF '{path.name}' não contém páginas.": "El PDF '{path.name}' no contiene páginas.",
        "Não foi possível verificar se o PDF exige senha. O arquivo pode estar danificado.": "No se pudo comprobar si el PDF requiere contraseña. El archivo puede estar dañado.",
        "As margens não deixam espaço suficiente na página.": "Los márgenes no dejan suficiente espacio en la página.",
        "Adicione pelo menos uma imagem.": "Añade al menos una imagen.",
        "A resolução precisa ficar entre 72 e 600 DPI.": "La resolución debe estar entre 72 y 600 DPI.",
        "A margem precisa ficar entre 0 e 40 mm.": "El margen debe estar entre 0 y 40 mm.",
        "O arquivo de saída não pode substituir uma imagem de origem.": "El archivo de salida no puede reemplazar una imagen de origen.",
        "Imagem não encontrada: {source}": "Imagen no encontrada: {source}",
        "Formato de imagem não suportado: {source.name}": "Formato de imagen no compatible: {source.name}",
        "Selecione pelo menos dois PDFs para unir.": "Selecciona al menos dos PDF para unir.",
        "Informe uma senha por PDF ou deixe a senha como None.": "Indica una contraseña para cada PDF o déjala como None.",
        "Informe um intervalo de páginas por PDF ou deixe None para usar todas.": "Indica un intervalo de páginas para cada PDF o deja None para usar todas.",
        "O número de páginas por bloco deve ser positivo.": "El número de páginas por bloque debe ser positivo.",
        "O intervalo entre inserções deve ser positivo.": "El intervalo entre inserciones debe ser positivo.",
        "O intervalo entre inserções não pode exceder o número de páginas do PDF de destino.": "El intervalo entre inserciones no puede superar el número de páginas del PDF de destino.",
        "A exclusão precisa manter pelo menos uma página no PDF.": "La eliminación debe dejar al menos una página en el PDF.",
        "Escolha uma rotação de 90, 180 ou 270 graus.": "Elige una rotación de 90, 180 o 270 grados.",
        "Modo de divisão inválido.": "Modo de división no válido.",
        "O número de páginas por arquivo deve ser positivo.": "El número de páginas por archivo debe ser positivo.",
        "O tamanho alvo precisa ser um número finito maior que zero.": "El tamaño objetivo debe ser finito y mayor que cero.",
        "O nível do marcador precisa ser um inteiro positivo.": "El nivel del marcador debe ser un entero positivo.",
        "A expressão regular para filtrar marcadores é inválida.": "La expresión regular para filtrar marcadores no es válida.",
        "PDF não encontrado: {source}": "PDF no encontrado: {source}",
        "O arquivo de origem precisa ser PDF.": "El archivo de origen debe ser un PDF.",
        "Informe páginas após as quais dividir, por exemplo: 2, 5, 8.": "Indica las páginas después de las cuales dividir, por ejemplo: 2, 5, 8.",
        "Não foi possível estimar o tamanho armazenado da página {page_number}.": "No se pudo estimar el tamaño almacenado de la página {page_number}.",
        "O PDF não contém marcadores no nível solicitado (ou nenhum corresponde ao filtro).": "El PDF no contiene marcadores en el nivel solicitado (o ninguno coincide con el filtro).",
        "Não foi possível gerar divisões a partir das opções informadas.": "No se pudieron generar divisiones con las opciones indicadas.",
        "Não foi possível criar a pasta de destino.": "No se pudo crear la carpeta de destino.",
        "A pasta já contém '{conflicts[0]}'. Escolha outra pasta ou remova os arquivos conflitantes.": "La carpeta ya contiene '{conflicts[0]}'. Elige otra carpeta o elimina los archivos en conflicto.",
        "Formato de saída não suportado: {output_format}": "Formato de salida no compatible: {output_format}",
        "A extensão de saída não corresponde ao formato {image_format}.": "La extensión de salida no coincide con el formato {image_format}.",
        "A largura máxima precisa ser maior que zero.": "El ancho máximo debe ser mayor que cero.",
        "A altura máxima precisa ser maior que zero.": "La altura máxima debe ser mayor que cero.",
        "A qualidade precisa ficar entre 1 e 100.": "La calidad debe estar entre 1 y 100.",
        "O arquivo de imagem temporário ficou vazio.": "El archivo de imagen temporal está vacío.",
        "A ordem deve conter cada página uma única vez, de 1 a {count}.": "El orden debe contener cada página una sola vez, del 1 al {count}.",
        "A qualidade JPEG precisa ficar entre 50 e 95.": "La calidad JPEG debe estar entre 50 y 95.",
        "Qualidade JPEG precisa ficar entre 50 e 95.": "La calidad JPEG debe estar entre 50 y 95.",
        "O tamanho da fonte precisa ficar entre 8 e 120.": "El tamaño de fuente debe estar entre 8 y 120.",
        "A opacidade precisa ficar entre 0,05 e 1.": "La opacidad debe estar entre 0,05 y 1.",
        "Posição de marca d'água inválida.": "Posición de marca de agua no válida.",
        "Posição de numeração inválida.": "Posición de numeración no válida.",
        "O texto da marca d'água é longo demais para caber na página. Reduza o texto ou use uma posição central.": "El texto de la marca de agua es demasiado largo para caber en la página. Acórtalo o usa una posición central.",
        "Selecione pelo menos uma etapa para executar o fluxo em lote.": "Selecciona al menos una etapa para ejecutar el flujo por lotes.",
        "Escolha PNG ou JPEG para exportar as páginas.": "Elige PNG o JPEG para exportar las páginas.",
        "Escolha um arquivo PDF existente.": "Elige un archivo PDF existente.",
        "Escolha uma pasta de saída existente.": "Elige una carpeta de salida existente.",
        "A qualidade JPEG precisa ficar entre 1 e 100.": "La calidad JPEG debe estar entre 1 y 100.",
        "A senha do PDF está incorreta ou não foi informada.": "La contraseña del PDF es incorrecta o no se indicó.",
        "Não foi possível abrir o PDF. Verifique se o arquivo está válido e se a senha está correta.": "No se pudo abrir el PDF. Comprueba que el archivo sea válido y que la contraseña sea correcta.",
        "Não foi possível obter o tamanho da página {page_index + 1}.": "No se pudo obtener el tamaño de la página {page_index + 1}.",
        "A página ultrapassa o limite seguro de pixels. Reduza a resolução de saída.": "La página supera el límite seguro de píxeles. Reduce la resolución de salida.",
        "Não foi possível renderizar a página {page_index + 1}.": "No se pudo renderizar la página {page_index + 1}.",
        "Não foi possível salvar a imagem da página {page_index + 1}.": "No se pudo guardar la imagen de la página {page_index + 1}.",
        "Selecione uma pasta de origem.": "Selecciona una carpeta de origen.",
        "A pasta de saída não pode ser a pasta de origem nem ficar dentro dela.": "La carpeta de salida no puede ser la carpeta de origen ni estar dentro de ella.",
        "Selecione pelo menos uma etapa do fluxo.": "Selecciona al menos una etapa del flujo.",
        "A etapa de marca d'água precisa de um texto ou da numeração ativada.": "La etapa de marca de agua requiere texto o numeración activada.",
        "A pasta selecionada não contém arquivos PDF.": "La carpeta seleccionada no contiene archivos PDF.",
        "Não há PDFs selecionados para reprocessar.": "No hay PDF seleccionados para volver a procesar.",
        "Identificador de relatório inválido.": "Identificador de informe no válido.",
        "O relatório do lote contém dados inválidos.": "El informe del lote contiene datos no válidos.",
        "Criando PDF a partir das imagens": "Creando PDF a partir de las imágenes",
        "Abra esta pasta manualmente:\n{path}": "Abre esta carpeta manualmente:\n{path}",
        "Escolha otimização sem perdas ou equilibrada.": "Elige optimización sin pérdida o equilibrada.",
        "Processamento local:": "Procesamiento local:",
        "Já existe um perfil chamado '{name}'. Deseja substituí-lo?": "Ya existe un perfil llamado '{name}'. ¿Quieres reemplazarlo?",
        "Não foi possível concluir a operação: {message}": "No se pudo completar la operación: {message}",
        "Há um lote em andamento. Cancelar o lote e sair?": "Hay un lote en curso. ¿Cancelar el lote y salir?",
        "Falhas: {count}.": "Fallos: {count}.",
})

TRANSLATIONS["en"].update({
    "Criando PDF a partir das imagens…": "Creating PDF from images…",
    "Escolha uma senha por PDF ou deixe a senha como None.": "Choose a password for each PDF or leave it as None.",
})
TRANSLATIONS["es"].update({
    "Criando PDF a partir das imagens…": "Creando PDF a partir de las imágenes…",
    "Escolha uma senha por PDF ou deixe a senha como None.": "Elige una contraseña para cada PDF o déjala como None.",
})

for _language, _table in TRANSLATIONS.items():
    _clean_table = {}
    for _key, _value in _table.items():
        _clean_key = _key.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").replace("\ufeff", "").strip()
        if _clean_key != _key:
            _leading = _key[:len(_key) - len(_key.lstrip())]
            _trailing = _key[len(_key.rstrip()):]
            _clean_value = _leading + _value.strip() + _trailing
        else:
            _clean_value = _value
        _clean_table[_clean_key] = _clean_value
    TRANSLATIONS[_language] = _clean_table

class ReorderPageDelegate(QStyledItemDelegate):
    """Keep each page thumbnail above its readable caption."""

    def initStyleOption(self, option, index) -> None:  # noqa: N802 - Qt override
        super().initStyleOption(option, index)
        option.decorationPosition = QStyleOptionViewItem.Position.Top
        option.decorationAlignment = Qt.AlignmentFlag.AlignHCenter
        option.displayAlignment = Qt.AlignmentFlag.AlignHCenter


class ReorderablePageList(QListWidget):
    """Thumbnail grid with explicit, same-widget drag-and-drop reordering."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dragged_item: QListWidgetItem | None = None
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setMovement(QListWidget.Movement.Static)

    def move_page_to_row(self, source_row: int, target_row: int) -> None:
        """Move one item to its final zero-based row, preserving its page identity."""
        if source_row < 0 or source_row >= self.count():
            return
        target_row = max(0, min(target_row, self.count() - 1))
        if source_row == target_row:
            return
        item = self.takeItem(source_row)
        self.insertItem(target_row, item)
        self.setCurrentItem(item)

    def startDrag(self, supportedActions) -> None:  # noqa: N802 - Qt override
        """Use a custom drag so Qt cannot remove a page after our manual drop."""
        item = self.currentItem()
        if item is None:
            selected = self.selectedItems()
            item = selected[0] if len(selected) == 1 else None
        if item is None:
            return

        self._dragged_item = item
        drag = QDrag(self)
        mime_data = QMimeData()
        page_number = item.data(Qt.ItemDataRole.UserRole)
        mime_data.setText(str(page_number if page_number is not None else item.text()))
        drag.setMimeData(mime_data)
        preview = item.icon().pixmap(self.iconSize())
        if not preview.isNull():
            drag.setPixmap(preview)
            drag.setHotSpot(QPoint(preview.width() // 2, preview.height() // 2))
        try:
            # QListWidget.startDrag performs post-drop source cleanup, which can
            # remove the same item that dropEvent has just repositioned.
            drag.exec(Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        finally:
            self._dragged_item = None

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        # Let QListWidget handle its native drop indicator and autoscroll. The
        # custom dropEvent still performs the final move without Qt's source cleanup.
        if event.source() is self and self.count() > 0:
            try:
                super().dragMoveEvent(event)
            except TypeError:
                # Unit tests and third-party integrations may provide a lightweight
                # event adapter instead of a native QDragMoveEvent.
                event.acceptProposedAction()
            else:
                if not event.isAccepted():
                    event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.source() is not self:
            event.ignore()
            return
        item = self._dragged_item
        if item is None or self.row(item) < 0:
            selected = self.selectedItems()
            item = selected[0] if len(selected) == 1 else None
        if item is None:
            event.ignore()
            return
        source_row = self.row(item)
        target_row = self.indexAt(event.position().toPoint()).row()
        if target_row < 0:
            target_row = self.count() - 1
        self.move_page_to_row(source_row, target_row)
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()


class ImageDropList(QListWidget):
    """Image list that accepts external images while retaining internal reordering."""

    filesDropped = Signal(list)

    @staticmethod
    def _paths_from_mime(mime_data, *, check_exists: bool = True) -> list[str]:
        if not mime_data.hasUrls():
            return []
        paths: list[str] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile()).expanduser()
            supported = path.suffix.casefold() in SUPPORTED_IMAGE_SUFFIXES
            if supported and (not check_exists or path.is_file()):
                paths.append(str(path))
        return paths

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event) -> None:
        if self._paths_from_mime(event.mimeData(), check_exists=False):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._paths_from_mime(event.mimeData(), check_exists=False):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        paths = self._paths_from_mime(event.mimeData(), check_exists=True)
        if paths:
            self.filesDropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class SideNavigationWidget(QWidget):
    """Persistent left-side navigation with scrollable content pages."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._labels: list[str] = []
        self._buttons: list[QPushButton] = []
        self._reorder_pages_button: QPushButton | None = None
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidePanel")
        self.sidebar.setMinimumWidth(276)
        self.sidebar.setMaximumWidth(310)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(6, 8, 6, 8)

        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("navigationScroll")
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_widget = QWidget()
        self.nav_widget.setObjectName("navigationContent")
        self.nav_layout = QVBoxLayout(self.nav_widget)
        self.nav_layout.setContentsMargins(2, 2, 2, 2)
        self.nav_layout.setSpacing(3)
        self.nav_layout.addStretch(1)
        nav_scroll.setWidget(self.nav_widget)
        sidebar_layout.addWidget(nav_scroll, 1)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        outer.addWidget(self.sidebar)
        outer.addWidget(self.stack, 1)

    def setDocumentMode(self, _enabled: bool) -> None:
        """Compatibility no-op; navigation is not rendered as a tab bar."""

    def addTab(self, widget: QWidget, label: str) -> int:
        index = self.stack.count()
        scroll = QScrollArea()
        scroll.setObjectName("contentScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        self.stack.addWidget(scroll)

        button = QPushButton(label.strip())
        button.setObjectName("navButton")
        icon_by_label = {
            "Imagens para PDF": QStyle.StandardPixmap.SP_FileDialogNewFolder,
            "Unir PDFs": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "Misturar PDFs": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "Inserir páginas": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "Extrair páginas": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "Excluir páginas": QStyle.StandardPixmap.SP_TrashIcon,
            "Girar páginas": QStyle.StandardPixmap.SP_BrowserReload,
            "Dividir PDF": QStyle.StandardPixmap.SP_FileDialogListView,
            "Reordenar páginas": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "Marca d'água e numeração": QStyle.StandardPixmap.SP_DialogApplyButton,
            "Otimizar PDF": QStyle.StandardPixmap.SP_ComputerIcon,
            "Fluxo em lote": QStyle.StandardPixmap.SP_MediaPlay,
            "Processar pasta": QStyle.StandardPixmap.SP_DirOpenIcon,
            "PDF para imagens": QStyle.StandardPixmap.SP_FileDialogInfoView,
            "Converter imagens": QStyle.StandardPixmap.SP_FileIcon,
            "Configurações": QStyle.StandardPixmap.SP_ComputerIcon,
        }
        icon_kind = icon_by_label.get(label.strip(), QStyle.StandardPixmap.SP_FileIcon)
        button.setIcon(self.style().standardIcon(icon_kind))
        if label.strip() == "Reordenar páginas":
            self._reorder_pages_button = button
            button.setIcon(create_reorder_pages_icon("light"))
        button.setIconSize(QSize(18, 18))
        button.setCheckable(True)
        button.setMinimumHeight(38)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.clicked.connect(lambda _checked=False, current=index: self.setCurrentIndex(current))
        self.nav_layout.insertWidget(max(0, self.nav_layout.count() - 1), button)
        self._buttons.append(button)
        self._labels.append(label.strip())
        if index == 0:
            self.setCurrentIndex(0)
        return index

    def count(self) -> int:
        return len(self._labels)

    def tabText(self, index: int) -> str:
        return self._labels[index]

    def setTabText(self, index: int, label: str) -> None:
        value = label.strip()
        self._labels[index] = value
        self._buttons[index].setText(value)

    def setTabEnabled(self, index: int, enabled: bool) -> None:
        self._buttons[index].setEnabled(enabled)
        self.stack.widget(index).setEnabled(enabled)

    def setCurrentIndex(self, index: int) -> None:
        if not 0 <= index < self.count():
            return
        self.stack.setCurrentIndex(index)
        for current, button in enumerate(self._buttons):
            button.setChecked(current == index)

    def currentIndex(self) -> int:
        return self.stack.currentIndex()

    def set_theme(self, theme: str) -> None:
        """Update the custom reorder icon to preserve contrast in both themes."""
        if self._reorder_pages_button is not None:
            self._reorder_pages_button.setIcon(create_reorder_pages_icon(theme))


class PageThumbnailWorker(QThread):
    """Render small page previews without blocking the GUI thread."""

    thumbnail_ready = Signal(int, QImage)
    failed = Signal(str)

    def __init__(self, path: str, password: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self._path = path
        self._password = password

    def run(self) -> None:
        document = QPdfDocument()
        try:
            if self._password:
                document.setPassword(self._password)
            document.load(self._path)
            count = document.pageCount()
            if count < 1:
                self.failed.emit("Não foi possível gerar miniaturas do PDF.")
                return
            for page_index in range(count):
                if self.isInterruptionRequested():
                    break
                point_size = document.pagePointSize(page_index)
                width_points = float(point_size.width())
                height_points = float(point_size.height())
                if width_points <= 0 or height_points <= 0:
                    continue
                scale = min(76 / width_points, 96 / height_points)
                render_size = QSize(
                    max(1, round(width_points * scale)),
                    max(1, round(height_points * scale)),
                )
                image = document.render(page_index, render_size)
                if not image.isNull():
                    self.thumbnail_ready.emit(page_index + 1, image)
        except Exception:
            self.failed.emit("Não foi possível gerar miniaturas do PDF.")
        finally:
            document.close()


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
        return friendly_error_message(error)


class BatchFolderWorker(QThread):
    """Process a folder in the background with retryable per-file results."""
    progress = Signal(int, int, str)
    succeeded = Signal(object, bool)
    failed = Signal(str)

    def __init__(
        self, source_directory: str, output_directory: str, profile: dict[str, object],
        *, recursive: bool, file_mode: int, resume: bool, control: BatchControl,
        only_sources: list[str] | None = None,
        initial_results: list[BatchFileResult] | None = None,
    ) -> None:
        super().__init__()
        self._source_directory = source_directory
        self._output_directory = output_directory
        self._profile = profile
        self._recursive = recursive
        self._file_mode = file_mode
        self._resume = resume
        self._control = control
        self._only_sources = only_sources
        self._initial_results = initial_results

    def run(self) -> None:
        try:
            results = process_pdf_folder(
                self._source_directory, self._output_directory, self._profile,
                recursive=self._recursive, file_mode=self._file_mode,
                progress_callback=lambda done, total, name: self.progress.emit(done, total, name),
                resume=self._resume,
                control=self._control,
                only_sources=self._only_sources,
                initial_results=self._initial_results,
            )
        except Exception as error:
            self.failed.emit(friendly_error_message(error))
            return
        self.succeeded.emit(results, self._control.was_stopped)


class DocumentToolsWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        # Respect the usable desktop while preventing a resize that hides controls.
        minimum_width = min(1120, available.width()) if available is not None else 1120
        minimum_height = min(700, available.height()) if available is not None else 700
        initial_width = min(1160, available.width()) if available is not None else 1160
        initial_height = min(810, available.height()) if available is not None else 810
        self.setMinimumSize(minimum_width, minimum_height)
        self.resize(initial_width, initial_height)
        self.settings = QSettings("PDFHub", "PDF Hub")
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self._batch_history_directory = Path(app_data or (Path.home() / ".pdf-hub")) / "batch-reports"
        self._batch_history: dict[str, dict[str, object]] = {}
        saved_theme = str(self.settings.value("theme", "light"))
        self._theme = saved_theme if saved_theme in {"light", "dark"} else "light"
        self._language = "pt"
        self._original_ui_texts: dict[QWidget, str] = {}
        self._original_tooltips: dict[QWidget, str] = {}
        self._original_placeholders: dict[QLineEdit, str] = {}
        self._original_combo_items: dict[QComboBox, list[str]] = {}
        self._original_tab_titles: list[str] = []
        self._worker: QThread | None = None
        self._batch_control: BatchControl | None = None
        self._folder_batch_running = False
        self._close_when_idle = False
        self._folder_batch_tab_index = -1
        self._last_batch_profile: dict[str, object] | None = None
        self._last_batch_profile_name: str | None = None
        self._pending_batch_context: dict[str, object] | None = None
        self._last_batch_source_directory: str | None = None
        self._last_batch_output_directory: str | None = None
        self._last_batch_recursive = False
        self._last_batch_file_mode = 0o600
        self._pending_output_directory: Path | None = None
        self._pending_output_location: Path | None = None
        self._split_custom_directory = False
        self.reorder_thumbnail_worker: PageThumbnailWorker | None = None
        self._retired_thumbnail_workers: list[PageThumbnailWorker] = []
        self._reorder_generation = 0
        self._reorder_source_signature: tuple[int, int] | None = None
        self._reorder_items_by_page: dict[int, QListWidgetItem] = {}

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(16, 14, 16, 12)
        central_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("headerCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(14)

        self.setWindowIcon(create_app_icon())
        brand_mark = QLabel()
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(48, 48)
        brand_mark.setPixmap(self.windowIcon().pixmap(48, 48))
        header_layout.addWidget(brand_mark)

        brand_text = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        subtitle = QLabel(
            self._t("PDF e imagens • v{version} • organizado, seguro e local").format(
                version=__version__
            )
        )
        subtitle.setObjectName("subtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        header_layout.addLayout(brand_text, 1)
        central_layout.addWidget(header)

        self.tabs = SideNavigationWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_image_pdf_tab(), "  Imagens para PDF  ")
        self.tabs.addTab(self._build_merge_tab(), "  Unir PDFs  ")
        self.tabs.addTab(self._build_mix_tab(), "  Misturar PDFs  ")
        self.tabs.addTab(self._build_insert_pages_tab(), "  Inserir páginas  ")
        self.tabs.addTab(self._build_extract_tab(), "  Extrair páginas  ")
        self.tabs.addTab(self._build_delete_pages_tab(), "  Excluir páginas  ")
        self.tabs.addTab(self._build_rotate_tab(), "  Girar páginas  ")
        self.tabs.addTab(self._build_split_tab(), "  Dividir PDF  ")
        self.tabs.addTab(self._build_reorder_tab(), "  Reordenar páginas  ")
        self.tabs.addTab(self._build_stamp_tab(), "  Marca d'água e numeração  ")
        self.tabs.addTab(self._build_optimize_tab(), "  Otimizar PDF  ")
        self.tabs.addTab(self._build_pipeline_tab(), "  Fluxo em lote  ")
        self._folder_batch_tab_index = self.tabs.addTab(self._build_folder_batch_tab(), "  Processar pasta  ")
        self.tabs.addTab(self._build_pdf_to_images_tab(), "  PDF para imagens  ")
        self.tabs.addTab(self._build_convert_tab(), "  Converter imagens  ")
        self.settings_tab_index = self.tabs.addTab(self._build_settings_tab(), "Configurações")
        central_layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.status_label = QLabel("Pronto. Selecione uma ferramenta no menu lateral.")
        self._status_source: tuple[str, dict[str, object]] = ("Pronto. Selecione uma ferramenta no menu lateral.", {})
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
        self.setStyleSheet(self._stylesheet(self._theme))
        self.tabs.set_theme(self._theme)
        self._capture_ui_texts()
        saved_language = str(self.settings.value("language", "pt"))
        language_index = self.language_combo.findData(saved_language)
        self.language_combo.setCurrentIndex(language_index if language_index >= 0 else 0)
        self.language_combo.currentIndexChanged.connect(self._change_language)
        theme_index = self.theme_combo.findData(self._theme)
        self.theme_combo.setCurrentIndex(theme_index if theme_index >= 0 else 0)
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        self._apply_language(str(self.language_combo.currentData()))
        self._load_batch_history()

    def _t(self, text: str) -> str:
        """Translate Brazilian Portuguese messages and their rendered translations."""
        leading = text[:len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()):]
        core = text.strip()
        if core.startswith("PDF e imagens • v") and core.endswith("organizado, seguro e local"):
            version = core.split(" • ")[1]
            translated = {
                "en": f"PDFs and images • {version} • organized, safe and local",
                "es": f"PDF e imágenes • {version} • organizado, seguro y local",
            }.get(self._language, core)
            return leading + translated + trailing
        mapping = TRANSLATIONS.get(self._language, {})
        if core in mapping:
            return leading + mapping[core] + trailing
        # Translate dynamic messages by matching the original template and preserving values.
        source_templates = dict.fromkeys((*TRANSLATIONS["en"].keys(), *TRANSLATIONS["es"].keys()))
        for source_template in source_templates:
            if "{" not in source_template:
                continue
            captures = _match_template(core, source_template)
            if captures is not None:
                target_template = source_template if self._language == "pt" else mapping.get(source_template)
                if target_template is not None:
                    return leading + _fill_template(target_template, captures) + trailing
            for source_language in ("en", "es"):
                translated_source = TRANSLATIONS[source_language].get(source_template)
                if not translated_source:
                    continue
                captures = _match_template(core, translated_source)
                if captures is not None:
                    target_template = source_template if self._language == "pt" else mapping.get(source_template)
                    if target_template is not None:
                        return leading + _fill_template(target_template, captures) + trailing
        # Allow switching between non-Portuguese languages when a status is already translated.
        for language in ("en", "es"):
            reverse = {translated: source for source, translated in TRANSLATIONS[language].items()}
            if core in reverse:
                source = reverse[core]
                return leading + mapping.get(source, source) + trailing
        # Translate dynamic operation summaries while preserving file paths and filenames.
        dynamic_prefixes = {
            "en": [
                ("PDF criado: ", "PDF created: "),
                ("PDFs unidos: ", "PDFs merged: "),
                ("PDFs misturados: ", "PDFs mixed: "),
                ("PDF com páginas inseridas: ", "PDF with inserted pages: "),
                ("Páginas extraídas: ", "Pages extracted: "),
                ("Páginas removidas: ", "Pages removed: "),
                ("PDF rotacionado: ", "PDF rotated: "),
                ("Unindo os PDFs…", "Merging PDFs…"),
                ("Extraindo páginas…", "Extracting pages…"),
                ("Excluindo páginas…", "Deleting pages…"),
                ("Girando páginas…", "Rotating pages…"),
                ("Dividindo PDF em arquivos de página única…", "Splitting PDF into single-page files…"),
                ("Convertendo imagens…", "Converting images…"),
            ],
            "es": [
                ("PDF criado: ", "PDF creado: "),
                ("PDFs unidos: ", "PDFs unidos: "),
                ("PDFs misturados: ", "PDF mezclados: "),
                ("PDF com páginas inseridas: ", "PDF con páginas insertadas: "),
                ("Páginas extraídas: ", "Páginas extraídas: "),
                ("Páginas removidas: ", "Páginas eliminadas: "),
                ("PDF rotacionado: ", "PDF girado: "),
                ("Unindo os PDFs…", "Uniendo los PDF…"),
                ("Extraindo páginas…", "Extrayendo páginas…"),
                ("Excluindo páginas…", "Eliminando páginas…"),
                ("Girando páginas…", "Girando páginas…"),
                ("Dividindo PDF em arquivos de página única…", "Dividiendo el PDF en archivos de una página…"),
                ("Convertendo imagens…", "Convirtiendo imágenes…"),
            ],
        }
        for source_prefix, translated_prefix in dynamic_prefixes.get(self._language, []):
            if core.startswith(source_prefix):
                return leading + translated_prefix + core[len(source_prefix):] + trailing
        page_range = re.match(r"^O intervalo '(.+)' precisa estar entre 1 e (\d+)\.$", core)
        if page_range:
            return self._t("O intervalo '{range}' precisa estar entre 1 e {count}.").format(
                range=page_range.group(1), count=page_range.group(2)
            )
        duplicate_page = re.match(r"^A página (\d+) foi informada mais de uma vez\.$", core)
        if duplicate_page:
            return self._t("A página {number} foi informada mais de uma vez.").format(
                number=duplicate_page.group(1)
            )
        invalid_range = re.match(r"^Intervalo de páginas inválido: '(.+)'\.$", core)
        if invalid_range:
            return self._t("Intervalo de páginas inválido: '{range}'.").format(
                range=invalid_range.group(1)
            )
        wrong_password = re.match(r"^A senha informada para o PDF '(.+)' está incorreta\.$", core)
        if wrong_password:
            return self._t("A senha informada para o PDF '{name}' está incorreta.").format(
                name=wrong_password.group(1)
            )
        required_password = re.match(r"^O PDF '(.+)' exige uma senha\. Informe-a para continuar\.$", core)
        if required_password:
            return self._t("O PDF '{name}' exige uma senha. Informe-a para continuar.").format(
                name=required_password.group(1)
            )
        conflict = re.match(r"^A pasta já contém '(.+)'\. Escolha outra pasta ou remova os arquivos conflitantes\.$", core)
        if conflict:
            return self._t("A pasta já contém '{name}'. Escolha outra pasta ou remova os arquivos conflitantes.").format(
                name=conflict.group(1)
            )
        for source, translated in mapping.items():
            if "{message}" in source and core.startswith(source.split("{message}")[0]):
                prefix = source.split("{message}")[0]
                return leading + translated.split("{message}")[0] + core[len(prefix):] + trailing
        return text

    def _render_status(self) -> None:
        if not hasattr(self, "status_label"):
            return
        source_text, values = self._status_source
        translated = self._t(source_text)
        if values:
            formatted_values = {
                key: (self._t(value) if key == "message" and isinstance(value, str) else value)
                for key, value in values.items()
            }
            translated = translated.format(**formatted_values)
        self.status_label.setText(translated)

    def _set_status(self, source_text: str, **values: object) -> None:
        """Store the source message so it can be translated again later."""
        self._status_source = (source_text, dict(values))
        self._render_status()

    def _capture_ui_texts(self) -> None:
        for widget in self.findChildren(QWidget):
            if widget is self.language_combo:
                continue
            if (
                widget is self.status_label
                or widget is getattr(self, "reorder_preview", None)
                or widget is getattr(self, "batch_pause_button", None)
            ):
                continue
            if isinstance(widget, (QLabel, QPushButton, QCheckBox, QToolButton)):
                self._original_ui_texts[widget] = widget.text()
            if widget.toolTip():
                self._original_tooltips[widget] = widget.toolTip()
            if isinstance(widget, QLineEdit) and widget.placeholderText():
                self._original_placeholders[widget] = widget.placeholderText()
            if isinstance(widget, QComboBox) and widget is not self.language_combo:
                self._original_combo_items[widget] = [
                    widget.itemText(index) for index in range(widget.count())
                ]
        self._original_tab_titles = [
            self.tabs.tabText(index) for index in range(self.tabs.count())
        ]

    def _change_language(self) -> None:
        language = str(self.language_combo.currentData())
        self.settings.setValue("language", language)
        self._apply_language(language)

    def _apply_language(self, language: str) -> None:
        self._language = language if language in {"pt", "en", "es"} else "pt"
        for widget, original in self._original_ui_texts.items():
            try:
                translated = self._t(original)
                if isinstance(widget, (QLabel, QPushButton, QCheckBox, QToolButton)):
                    widget.setText(translated)
            except RuntimeError:
                continue
        for widget, original in self._original_tooltips.items():
            try:
                widget.setToolTip(self._t(original))
            except RuntimeError:
                continue
        for widget, original in self._original_placeholders.items():
            try:
                widget.setPlaceholderText(self._t(original))
            except RuntimeError:
                continue
        for widget, original_items in self._original_combo_items.items():
            try:
                current = widget.currentIndex()
                for index, original in enumerate(original_items):
                    widget.setItemText(index, self._t(original))
                widget.setCurrentIndex(current)
            except RuntimeError:
                continue
        for index, original in enumerate(self._original_tab_titles):
            self.tabs.setTabText(index, self._t(original))
        if hasattr(self, "_reorder_items_by_page"):
            for page_number, item in self._reorder_items_by_page.items():
                item.setText(
                    self._t("Página {number}").format(number=f"{page_number:02d}")
                )
        if hasattr(self, "batch_results_table"):
            self.batch_results_table.setHorizontalHeaderLabels([
                self._t("Arquivo de origem"), self._t("Resultado"),
                self._t("Detalhes"), self._t("Arquivo de saída"),
            ])
        # Refresh the current status text too, so switching language does not leave stale Portuguese text.
        if self.status_label.text():
            self._render_status()
        if hasattr(self, "reorder_list") and hasattr(self, "reorder_preview"):
            self._preview_reorder_page(self.reorder_list.currentRow())
        if hasattr(self, "batch_pause_button"):
            control = getattr(self, "_batch_control", None)
            self.batch_pause_button.setText(
                self._t("Retomar lote" if control is not None and control.is_paused else "Pausar lote")
            )
        if hasattr(self, "batch_history_combo"):
            selected = self.batch_history_combo.currentData()
            self._refresh_batch_history_combo(selected if isinstance(selected, str) else None)

    @staticmethod
    def _stylesheet(theme: str = "light") -> str:
        palettes = {
            "light": {
                "WINDOW": "#F3F6FB", "PANEL": "#FFFFFF", "TEXT": "#172B4D",
                "MUTED": "#5B6B82", "BORDER": "#D8E0EC", "INPUT": "#FFFFFF",
                "BUTTON": "#F1F4F9", "BUTTON_TEXT": "#344054", "HOVER": "#E6ECF5",
                "PRESSED": "#DCE5F3", "DISABLED": "#F4F6F9", "NAV_SELECTED": "#E8EEFF",
                "NAV_SELECTED_TEXT": "#3346A8", "LIST_SELECTED": "#E8EEFF",
                "LIST_SELECTED_TEXT": "#263E9C", "PRIMARY": "#4263EB",
                "PRIMARY_HOVER": "#3354DD", "SECONDARY": "#EEF2FF",
                "SECONDARY_TEXT": "#3346A8", "PROGRESS_BG": "#E3EAF4",
                "FOCUS": "#7C92F3", "HEADER": "#172B4D", "HEADER_TEXT": "#FFFFFF",
                "HEADER_MUTED": "#C8D5E8", "TOOLTIP": "#172B4D", "TOOLTIP_TEXT": "#FFFFFF",
            },
            "dark": {
                "WINDOW": "#111827", "PANEL": "#1F2937", "TEXT": "#E5E7EB",
                "MUTED": "#A7B3C6", "BORDER": "#374151", "INPUT": "#111827",
                "BUTTON": "#374151", "BUTTON_TEXT": "#E5E7EB", "HOVER": "#4B5563",
                "PRESSED": "#596579", "DISABLED": "#252E3D", "NAV_SELECTED": "#263755",
                "NAV_SELECTED_TEXT": "#DBEAFE", "LIST_SELECTED": "#263755",
                "LIST_SELECTED_TEXT": "#DBEAFE", "PRIMARY": "#4766F0",
                "PRIMARY_HOVER": "#3F5FE0", "SECONDARY": "#263755",
                "SECONDARY_TEXT": "#DBEAFE", "PROGRESS_BG": "#374151",
                "FOCUS": "#8BA3FF", "HEADER": "#0B1220", "HEADER_TEXT": "#FFFFFF",
                "HEADER_MUTED": "#CBD5E1", "TOOLTIP": "#263244", "TOOLTIP_TEXT": "#FFFFFF",
            },
        }
        palette = palettes.get(theme, palettes["light"])
        style = """
        QMainWindow, QWidget {
            background: $WINDOW;
            color: $TEXT;
            font-family: "Segoe UI", "Inter", sans-serif;
            font-size: 13px;
        }
        QLabel { background: transparent; }
        QFrame#headerCard { background: $HEADER; border: none; border-radius: 10px; }
        QLabel#brandMark { background: transparent; }
        QLabel#appTitle { color: $HEADER_TEXT; font-size: 20px; font-weight: 700; }
        QLabel#subtitle { color: $HEADER_MUTED; font-size: 12px; }
        QLabel#muted, QLabel#intro { color: $MUTED; }
        QFrame#sidePanel {
            background: $PANEL;
            border: 1px solid $BORDER;
            border-radius: 10px;
        }
        QScrollArea#navigationScroll, QScrollArea#contentScrollArea,
        QStackedWidget#pageStack, QWidget#navigationContent { background: transparent; border: none; }
        QPushButton#navButton {
            background: transparent; color: $MUTED; border: none;
            border-radius: 8px; padding: 10px 12px; text-align: left; font-weight: 600;
        }
        QPushButton#navButton:hover:!checked { background: $BUTTON; color: $TEXT; }
        QPushButton#navButton:checked {
            background: $NAV_SELECTED; color: $NAV_SELECTED_TEXT; font-weight: 700;
        }
        QLabel#sectionTitle { color: $TEXT; font-size: 17px; font-weight: 700; }
        QListWidget {
            background: $INPUT; color: $TEXT; border: 1px solid $BORDER;
            border-radius: 8px; padding: 6px; outline: none;
        }
        QListWidget::item {
            background: transparent; padding: 8px 10px; margin: 2px 0; border-radius: 7px;
        }
        QListWidget::item:selected { background: $LIST_SELECTED; color: $LIST_SELECTED_TEXT; }
        QListWidget::item:hover:!selected { background: $BUTTON; }
        QListWidget#reorderPageList::item {
            background: #FFFFFF; color: #172B4D; border: 1px solid $BORDER;
            border-radius: 6px; padding: 6px; margin: 3px;
        }
        QListWidget#reorderPageList::item:selected {
            background: #FFFFFF; color: #172B4D; border: 2px solid $PRIMARY;
        }
        QLabel#pagePreview {
            background: #FFFFFF; color: #172B4D; border: 1px solid $BORDER;
            border-radius: 8px; padding: 8px;
        }
        QPushButton {
            background: $BUTTON; color: $BUTTON_TEXT; border: 1px solid $BORDER;
            border-radius: 6px; padding: 9px 11px; font-weight: 600;
        }
        QPushButton:hover { background: $HOVER; }
        QPushButton:pressed { background: $PRESSED; }
        QPushButton:disabled { color: $MUTED; background: $DISABLED; }
        QPushButton#primaryButton {
            background: $PRIMARY; color: #FFFFFF; border-color: $PRIMARY;
            padding: 11px 14px; font-weight: 700;
        }
        QPushButton#primaryButton:hover { background: $PRIMARY_HOVER; border-color: $PRIMARY_HOVER; }
        QPushButton#secondaryButton {
            background: $SECONDARY; color: $SECONDARY_TEXT; border-color: $BORDER;
        }
        QPushButton#primaryButton:disabled, QPushButton#secondaryButton:disabled {
            background: $DISABLED; color: $MUTED; border-color: $BORDER;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background: $INPUT; color: $TEXT; border: 1px solid $BORDER;
            border-radius: 6px; padding: 8px 9px; min-height: 18px;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: $FOCUS;
        }
        QComboBox QAbstractItemView {
            background: $PANEL; color: $TEXT;
            selection-background-color: $NAV_SELECTED;
            selection-color: $NAV_SELECTED_TEXT; border: 1px solid $BORDER;
        }
        QToolButton#infoButton {
            color: $MUTED; background: $BUTTON; border: 1px solid $BORDER;
            border-radius: 14px; min-width: 28px; min-height: 28px; font-weight: 700;
        }
        QLabel#statusLabel { color: $MUTED; font-size: 12px; }
        QProgressBar { border: none; background: $PROGRESS_BG; border-radius: 4px; height: 7px; }
        QProgressBar::chunk { background: $PRIMARY; border-radius: 4px; }
        QToolTip { color: $TOOLTIP_TEXT; background: $TOOLTIP; border: 1px solid $BORDER; padding: 5px; }
        QTableWidget { background: $INPUT; color: $TEXT; gridline-color: $BORDER; border: 1px solid $BORDER; }
        QHeaderView::section { background: $PANEL; color: $TEXT; border: 1px solid $BORDER; padding: 5px; }
        """
        # Replace complete palette tokens only. Plain str.replace("$TEXT", ...) also
        # corrupts longer tokens such as $HEADER_TEXT and $BUTTON_TEXT.
        style = re.sub(
            r"\$([A-Z_]+)",
            lambda match: palette.get(match.group(1), match.group(0)),
            style,
        )
        return style

    def _new_page(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        title_label.setWordWrap(True)
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
            os.path.normcase(
                str(Path(list_widget.item(index).data(Qt.ItemDataRole.UserRole)).resolve())
            )
            for index in range(list_widget.count())
        }
        added = 0
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            resolved = str(path.resolve())
            key = os.path.normcase(resolved)
            if not path.is_file() or key in known:
                continue
            item = QListWidgetItem(path.name)
            item.setToolTip(resolved)
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            list_widget.addItem(item)
            known.add(key)
            added += 1
        return added

    @staticmethod
    def _all_paths(list_widget: QListWidget) -> list[str]:
        return [
            str(list_widget.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(list_widget.count())
        ]

    def _choose_multiple(self, title: str, file_filter: str) -> list[str]:
        paths, _ = QFileDialog.getOpenFileNames(self, self._t(title), "", file_filter)
        return paths

    def _choose_pdf(self, title: str = "Escolher PDF") -> str | None:
        path, _ = QFileDialog.getOpenFileName(self, self._t(title), "", PDF_FILTER)
        return path or None

    def _desktop_directory(self) -> Path:
        raw_desktop = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        desktop = Path(raw_desktop).expanduser() if raw_desktop else Path.home() / "Desktop"
        return desktop if desktop.is_dir() else Path.home()

    def _default_save_path(self, filename: str) -> str:
        return str(self._desktop_directory() / filename)

    def _choose_output_file(
        self,
        title: str,
        suggested_name: str,
        suffix: str,
        file_filter: str,
    ) -> Path | None:
        """Normalize the final filename before checking whether it already exists."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self._t(title),
            self._default_save_path(suggested_name),
            self._t(file_filter),
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not filename:
            return None
        output = Path(filename).expanduser()
        normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        if output.suffix.casefold() != normalized_suffix.casefold():
            output = _ensure_suffix(output, normalized_suffix)
        output = output.resolve()
        if output.exists():
            answer = QMessageBox.question(
                self,
                self._t("Confirmar substituição"),
                self._t("O arquivo “{name}” já existe. Deseja substituí-lo?").format(name=output.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._set_status("Operação cancelada. O arquivo existente foi preservado.")
                return None
        return output

    def _choose_output_pdf(
        self,
        suggested_name: str,
        *,
        source_paths: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        desktop = self._desktop_directory()
        dialog = QFileDialog(
            self, self._t("Salvar PDF resultante"), str(desktop), PDF_FILTER
        )
        dialog.setDirectory(str(desktop))
        dialog.selectFile(suggested_name)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setDefaultSuffix("pdf")
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
        if dialog.exec() != QFileDialog.DialogCode.Accepted or not dialog.selectedFiles():
            return None

        output = Path(dialog.selectedFiles()[0]).expanduser()
        if output.suffix.lower() != ".pdf":
            output = _ensure_suffix(output, ".pdf")
        output = output.resolve()
        sources = {Path(item).expanduser().resolve() for item in source_paths}
        if any(_same_existing_file(output, source) for source in sources):
            QMessageBox.warning(
                self,
                self._t("Escolha outro nome"),
                self._t("O arquivo de saída não pode substituir um dos arquivos de origem."),
            )
            return None

        if output.exists():
            answer = QMessageBox.question(
                self,
                self._t("Confirmar substituição"),
                self._t("O arquivo “{name}” já existe. Deseja substituí-lo?").format(name=output.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._set_status("Operação cancelada. O arquivo existente foi preservado.")
                return None
        return str(output)

    def _choose_directory(self, title: str) -> str | None:
        path = QFileDialog.getExistingDirectory(self, self._t(title), str(self._desktop_directory()))
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
        self._set_status(description)
        self.open_directory_button.hide()
        self.progress.show()
        self.tabs.setEnabled(False)
        if output_location is None:
            self._pending_output_directory = None
            self._pending_output_location = None
        else:
            self._pending_output_location = Path(output_location).expanduser().resolve()
            self._pending_output_directory = None

        worker = OperationWorker(task)
        self._worker = worker
        worker.succeeded.connect(self._operation_succeeded)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(self._operation_finished)
        worker.start()

    def _operation_succeeded(self, message: str) -> None:
        self._set_status(message)
        location = self._pending_output_location
        if location is not None:
            self._pending_output_directory = (
                location if location.is_dir() else location.parent
            )
        self.open_directory_button.setVisible(
            self._pending_output_directory is not None
            and self._pending_output_directory.is_dir()
        )

    def _operation_failed(self, message: str) -> None:
        self.open_directory_button.hide()
        self._set_status("Não foi possível concluir a operação: {message}", message=message)
        QMessageBox.warning(self, self._t("Operação não concluída"), self._t(message))

    def _operation_finished(self) -> None:
        self.progress.hide()
        if self._folder_batch_running:
            for tab_index in range(self.tabs.count()):
                self.tabs.setTabEnabled(tab_index, True)
            self.batch_run_button.setEnabled(True)
            self.batch_choose_source_button.setEnabled(True)
            self.batch_choose_output_button.setEnabled(True)
            self.batch_include_subfolders.setEnabled(True)
            self.batch_resume_checkbox.setEnabled(True)
            self.batch_history_combo.setEnabled(True)
            self.batch_history_load_button.setEnabled(True)
            self.batch_history_delete_button.setEnabled(True)
            self.batch_pause_button.setText(self._t("Pausar lote"))
            self.batch_pause_button.setEnabled(False)
            self.batch_cancel_button.setEnabled(False)
            self.batch_reprocess_failures_button.setEnabled(
                any(not item.success for item in self.batch_results)
                and self._last_batch_profile is not None
            )
            self._folder_batch_running = False
            self._batch_control = None
            # If the worker failed before emitting a result, discard the staged context
            # and keep the previous successful batch available for failure-only retry.
            self._pending_batch_context = None
        else:
            self.tabs.setEnabled(True)
        worker = self._worker
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        self._worker = None
        if self._close_when_idle:
            self._close_when_idle = False
            QTimer.singleShot(0, self.close)

    def _open_output_directory(self) -> None:
        directory = self._pending_output_directory
        if directory is None or not directory.is_dir():
            self._set_status("A pasta de saída não está disponível.")
            self.open_directory_button.hide()
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            QMessageBox.information(self, APP_NAME, self._t("Abra esta pasta manualmente:\n{path}").format(path=directory))

    def closeEvent(self, event: QCloseEvent) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            if self._folder_batch_running and self._batch_control is not None:
                answer = QMessageBox.question(
                    self, APP_NAME,
                    self._t("Há um lote em andamento. Cancelar o lote e sair?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self._batch_control.cancel()
                    self._close_when_idle = True
                    self._set_status("Cancelamento solicitado; o lote será encerrado assim que for seguro.")
                event.ignore()
                return
            QMessageBox.information(
                self,
                APP_NAME,
                self._t("Uma operação está em andamento. Aguarde a conclusão antes de fechar o aplicativo."),
            )
            event.ignore()
            return
        if worker is not None:
            worker.wait()
            worker.deleteLater()
            self._worker = None
        thumbnail_workers = list(self._retired_thumbnail_workers)
        if (
            self.reorder_thumbnail_worker is not None
            and self.reorder_thumbnail_worker not in thumbnail_workers
        ):
            thumbnail_workers.append(self.reorder_thumbnail_worker)
        for thumbnail_worker in thumbnail_workers:
            thumbnail_worker.requestInterruption()
        for thumbnail_worker in thumbnail_workers:
            thumbnail_worker.wait()
            thumbnail_worker.deleteLater()
        self._retired_thumbnail_workers.clear()
        self.reorder_thumbnail_worker = None
        if getattr(self, "reorder_document", None) is not None:
            self.reorder_document.close()
            self.reorder_document = None
        event.accept()

    def _require_output_pdf(
        self,
        suggested_name: str,
        *,
        source_paths: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        return self._choose_output_pdf(suggested_name, source_paths=source_paths)

    def _save_output_permissions(self) -> None:
        self.settings.setValue("output_file_mode", int(self.output_permissions.currentData()))

    def _output_file_mode(self) -> int:
        return int(self.output_permissions.currentData())

    def _build_settings_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Configurações",
            "Defina o idioma, o tema visual e as permissões dos arquivos gerados.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.language_combo = QComboBox()
        self.language_combo.addItem("Português (Brasil)", "pt")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Español", "es")
        form.addRow("Idioma / Language", self.language_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Modo claro", "light")
        self.theme_combo.addItem("Modo escuro", "dark")
        form.addRow("Modo de aparência", self.theme_combo)

        permissions_row = QHBoxLayout()
        self.output_permissions = QComboBox()
        self.output_permissions.addItem("Somente usuário (0600)", 0o600)
        self.output_permissions.addItem("Compartilhado (0644)", 0o644)
        try:
            saved_mode = int(self.settings.value("output_file_mode", 0o600))
        except (TypeError, ValueError):
            saved_mode = 0o600
        saved_index = self.output_permissions.findData(saved_mode)
        self.output_permissions.setCurrentIndex(saved_index if saved_index >= 0 else 0)
        self.output_permissions.currentIndexChanged.connect(self._save_output_permissions)
        self.output_permissions.setToolTip(
            "0600: somente o usuário atual. 0644: outros usuários do sistema podem ler os arquivos."
        )
        permissions_row.addWidget(self.output_permissions, 1)
        self.output_permissions_info = QToolButton()
        self.output_permissions_info.setObjectName("infoButton")
        self.output_permissions_info.setText("ⓘ")
        self.output_permissions_info.setToolTip("Sobre permissões de saída")
        self.output_permissions_info.setAccessibleName("Sobre permissões de saída")
        self.output_permissions_info.clicked.connect(self._show_output_permissions_info)
        permissions_row.addWidget(self.output_permissions_info)
        permissions_container = QWidget()
        permissions_container.setLayout(permissions_row)
        form.addRow("Permissões de saída (Linux/macOS)", permissions_container)

        layout.addLayout(form)
        explanation = QLabel(
            "As permissões de saída se aplicam aos arquivos que o PDF Hub cria. "
            "O modo 0600 é a opção mais restritiva."
        )
        explanation.setObjectName("muted")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        layout.addStretch(1)
        return page

    def _show_output_permissions_info(self) -> None:
        QMessageBox.information(
            self,
            self._t("Sobre permissões de saída"),
            self._t(
                "0600 permite leitura e escrita apenas pelo usuário atual. 0644 permite que outros usuários locais leiam o arquivo. Isso afeta os arquivos gerados em Linux/macOS; no Windows, as permissões são gerenciadas pelo sistema."
            ),
        )

    def _change_theme(self) -> None:
        selected = str(self.theme_combo.currentData())
        self._theme = selected if selected in {"light", "dark"} else "light"
        self.settings.setValue("theme", self._theme)
        self.setStyleSheet(self._stylesheet(self._theme))
        self.tabs.set_theme(self._theme)

    def _build_image_pdf_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Transformar imagens em um documento",
            "Adicione as imagens e organize a sequência. Cada arquivo será colocado em uma página A4 sem distorcer a proporção.",
        )
        list_widget = ImageDropList()
        self.image_list = list_widget
        list_widget.filesDropped.connect(self._handle_dropped_images)
        list_widget.setToolTip("Arraste imagens para esta área ou use “Adicionar imagens”.")
        layout.addWidget(list_widget, 1)

        buttons = QGridLayout()
        add = QPushButton("+  Adicionar imagens")
        add.setObjectName("secondaryButton")
        add.clicked.connect(self._add_images)
        remove = QPushButton("Remover selecionadas")
        remove.clicked.connect(self._remove_image_inputs)
        up = QPushButton("↑  Subir")
        up.clicked.connect(lambda: self._move_selected(list_widget, -1))
        down = QPushButton("↓  Descer")
        down.clicked.connect(lambda: self._move_selected(list_widget, 1))
        duplicate = QPushButton("Duplicar selecionadas")
        duplicate.clicked.connect(lambda: self._duplicate_selected(list_widget))
        buttons.addWidget(add, 0, 0)
        buttons.addWidget(remove, 0, 1)
        buttons.addWidget(duplicate, 0, 2)
        buttons.addWidget(up, 1, 1)
        buttons.addWidget(down, 1, 2)
        buttons.setColumnStretch(0, 1)
        buttons.setColumnStretch(1, 1)
        buttons.setColumnStretch(2, 1)
        layout.addLayout(buttons)

        options = QHBoxLayout()
        options.addWidget(QLabel("Resolução:"))
        self._image_dpi_auto = 150
        self.image_dpi = QSpinBox()
        self.image_dpi.setRange(72, 600)
        self.image_dpi.setValue(150)
        self.image_dpi.setSuffix(" DPI")
        self.image_dpi.setToolTip(
            "Resolução estimada automaticamente a partir das dimensões em pixels das imagens; você pode ajustá-la manualmente."
        )
        options.addWidget(self.image_dpi)
        options.addSpacing(18)
        options.addWidget(QLabel("Margem:"))
        self.image_margin = QDoubleSpinBox()
        self.image_margin.setRange(0, 40)
        self.image_margin.setDecimals(1)
        self.image_margin.setValue(0)
        self.image_margin.setSuffix(" mm")
        self.image_margin.valueChanged.connect(
            lambda _value: self._update_image_dpi_from_sources()
        )
        options.addWidget(self.image_margin)
        options.addStretch(1)
        layout.addLayout(options)

        self.image_all_frames = QCheckBox("Incluir todas as páginas/quadros de imagens multipágina ou animadas")
        self.image_all_frames.setChecked(True)
        self.image_all_frames.setToolTip("Quando desmarcado, usa somente a primeira página ou o primeiro quadro de cada arquivo.")
        layout.addWidget(self.image_all_frames)

        bottom = QHBoxLayout()
        hint = QLabel(
            self._t("Arraste imagens para esta área ou use “Adicionar imagens”. Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.")
        )
        self.image_pdf_hint = hint
        hint.setObjectName("muted")
        hint.setWordWrap(True)
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
        if added:
            self._update_image_dpi_from_sources()
        if added:
            self._set_status("{added} imagem(ns) adicionada(s).", added=added)
        else:
            self._set_status("Nenhuma imagem nova adicionada.")

    def _handle_dropped_images(self, paths: list[str]) -> None:
        accepted = [path for path in paths if Path(path).suffix.casefold() in SUPPORTED_IMAGE_SUFFIXES]
        added = self._add_paths(self.image_list, accepted)
        if added:
            self._update_image_dpi_from_sources()
        if added:
            self._set_status("{added} imagem(ns) adicionada(s).", added=added)
        else:
            self._set_status("Nenhuma imagem nova adicionada.")

    def _update_image_dpi_from_sources(self) -> None:
        sources = self._all_paths(self.image_list)
        previous_auto = self._image_dpi_auto
        if not sources:
            self._image_dpi_auto = 150
            self.image_dpi.setValue(150)
            return

        recommended = recommend_dpi_from_images(
            sources, margin_mm=self.image_margin.value()
        )
        if recommended is None:
            if self.image_dpi.value() == previous_auto:
                self.image_dpi.setValue(150)
            self._image_dpi_auto = 150
            return

        # Only overwrite the control while it still contains the previous automatic
        # suggestion; a different value belongs to the user's manual choice.
        if self.image_dpi.value() == previous_auto:
            self.image_dpi.setValue(recommended)
            self._set_status("Resolução recomendada calculada a partir das imagens.")
        self._image_dpi_auto = recommended

    def _remove_image_inputs(self) -> None:
        self._remove_selected(self.image_list)
        self._update_image_dpi_from_sources()

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
            duplicate.setData(Qt.ItemDataRole.UserRole + 1, original.data(Qt.ItemDataRole.UserRole + 1))
            list_widget.insertItem(row + 1, duplicate)
            duplicate.setSelected(True)

    @staticmethod
    def _move_selected(list_widget: QListWidget, offset: int) -> None:
        if offset not in (-1, 1):
            raise ValueError("A lista só pode ser movida uma posição por vez.")
        if not list_widget.selectedItems():
            return

        current_item = list_widget.currentItem()
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

        if current_item is not None and list_widget.row(current_item) >= 0:
            list_widget.setCurrentItem(
                current_item, QItemSelectionModel.SelectionFlag.NoUpdate
            )

    def _create_pdf_from_images(self) -> None:
        sources = self._all_paths(self.image_list)
        if not sources:
            QMessageBox.information(self, self._t("Adicionar imagens"), self._t("Adicione pelo menos uma imagem primeiro."))
            return
        output = self._require_output_pdf("imagens.pdf", source_paths=sources)
        if not output:
            return
        dpi = self.image_dpi.value()
        margin_mm = self.image_margin.value()
        all_frames = self.image_all_frames.isChecked()
        file_mode = self._output_file_mode()
        self._run_task(
            "Criando PDF a partir das imagens…",
            lambda: f"PDF criado: {images_to_pdf(sources, output, dpi=dpi, margin_mm=margin_mm, all_frames=all_frames, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_merge_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Reunir documentos em um único arquivo",
            "A ordem dos PDFs na lista será a ordem dos documentos no arquivo final.",
        )
        self.pdf_list = self._new_list(extended=True)
        layout.addWidget(self.pdf_list, 1)

        self.merge_page_ranges = QLineEdit()
        self.merge_page_ranges.setEnabled(False)
        self.merge_page_ranges.setPlaceholderText(
            "Deixe em branco para usar todas as páginas; exemplo: 1-3, 5."
        )
        merge_ranges_form = QFormLayout()
        merge_ranges_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        merge_ranges_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        merge_ranges_form.setHorizontalSpacing(12)
        merge_ranges_form.addRow("Páginas do PDF selecionado (opcional)", self.merge_page_ranges)
        layout.addLayout(merge_ranges_form)
        self.pdf_list.currentItemChanged.connect(self._load_merge_selected_range)
        self.merge_page_ranges.textEdited.connect(self._save_merge_selected_range)

        buttons = QGridLayout()
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
        buttons.addWidget(add, 0, 0)
        buttons.addWidget(remove, 0, 1)
        buttons.addWidget(duplicate, 0, 2)
        buttons.addWidget(up, 1, 1)
        buttons.addWidget(down, 1, 2)
        buttons.setColumnStretch(0, 1)
        buttons.setColumnStretch(1, 1)
        buttons.setColumnStretch(2, 1)
        layout.addLayout(buttons)

        bottom = QHBoxLayout()
        hint = QLabel("Selecione pelo menos dois PDFs.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
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
        if added and self.pdf_list.currentRow() < 0 and self.pdf_list.count():
            self.pdf_list.setCurrentRow(0)
        if added:
            self._set_status("{added} PDF(s) adicionado(s).", added=added)
        else:
            self._set_status("Nenhum PDF novo adicionado.")

    def _load_merge_selected_range(self, current, _previous=None) -> None:
        self.merge_page_ranges.setEnabled(current is not None)
        self.merge_page_ranges.setText(
            str(current.data(Qt.ItemDataRole.UserRole + 1) or "") if current is not None else ""
        )

    def _save_merge_selected_range(self, value: str) -> None:
        current = self.pdf_list.currentItem()
        if current is not None:
            current.setData(Qt.ItemDataRole.UserRole + 1, value.strip())

    def _merge_pdfs(self) -> None:
        sources = self._all_paths(self.pdf_list)
        if len(sources) < 2:
            QMessageBox.information(self, self._t("Unir PDFs"), self._t("Adicione pelo menos dois PDFs."))
            return
        output = self._require_output_pdf("documentos-unidos.pdf", source_paths=sources)
        if not output:
            return
        passwords: list[str | None] = [None] * len(sources)
        validated_passwords: dict[str, str] = {}
        try:
            for index, source in enumerate(sources):
                password_key = os.path.normcase(str(Path(source).resolve()))
                if password_key in validated_passwords:
                    passwords[index] = validated_passwords[password_key]
                    continue
                if not pdf_requires_user_password(source):
                    continue

                for _attempt in range(3):
                    password, accepted = QInputDialog.getText(
                        self,
                        self._t("Senha do PDF"),
                        self._t("O arquivo '{name}' está protegido. Digite a senha:").format(name=Path(source).name),
                        QLineEdit.EchoMode.Password,
                    )
                    if not accepted:
                        return
                    if not password:
                        QMessageBox.information(
                            self,
                            self._t("Senha necessária"),
                            self._t("Informe uma senha não vazia para continuar."),
                        )
                        continue
                    try:
                        pdf_page_count(source, password=password)
                    except Exception as password_error:
                        QMessageBox.warning(
                            self,
                            self._t("Não foi possível verificar o PDF"),
                            self._t(friendly_error_message(password_error)),
                        )
                        continue
                    validated_passwords[password_key] = password
                    passwords[index] = password
                    break
                else:
                    return
        except Exception as error:
            QMessageBox.warning(
                self,
                self._t("Não foi possível verificar o PDF"),
                self._t(friendly_error_message(error)),
            )
            return
        page_ranges = [
            str(self.pdf_list.item(index).data(Qt.ItemDataRole.UserRole + 1) or "").strip() or None
            for index in range(self.pdf_list.count())
        ]
        file_mode = self._output_file_mode()
        self._run_task(
            "Unindo os PDFs…",
            lambda: f"PDFs unidos: {merge_pdfs(sources, output, passwords=passwords, page_ranges=page_ranges, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_mix_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Combinar páginas de dois PDFs alternadamente",
            "Escolha os documentos e defina quantas páginas de cada arquivo serão usadas em cada bloco.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.mix_first_path = QLineEdit()
        self.mix_first_path.setReadOnly(True)
        first_browse = QPushButton("Escolher PDF")
        first_browse.clicked.connect(self._select_mix_first_pdf)
        first_row = QHBoxLayout()
        first_row.setContentsMargins(0, 0, 0, 0)
        first_row.addWidget(self.mix_first_path, 1)
        first_row.addWidget(first_browse)
        first_container = QWidget()
        first_container.setLayout(first_row)
        form.addRow("Primeiro PDF", first_container)

        self.mix_second_path = QLineEdit()
        self.mix_second_path.setReadOnly(True)
        second_browse = QPushButton("Escolher PDF")
        second_browse.clicked.connect(self._select_mix_second_pdf)
        second_row = QHBoxLayout()
        second_row.setContentsMargins(0, 0, 0, 0)
        second_row.addWidget(self.mix_second_path, 1)
        second_row.addWidget(second_browse)
        second_container = QWidget()
        second_container.setLayout(second_row)
        form.addRow("Segundo PDF", second_container)

        self.mix_first_ranges = QLineEdit()
        self.mix_first_ranges.setPlaceholderText("Deixe em branco para usar todas as páginas; exemplo: 1-3, 5.")
        form.addRow("Páginas do primeiro PDF (opcional)", self.mix_first_ranges)
        self.mix_second_ranges = QLineEdit()
        self.mix_second_ranges.setPlaceholderText("Deixe em branco para usar todas as páginas; exemplo: 1-3, 5.")
        form.addRow("Páginas do segundo PDF (opcional)", self.mix_second_ranges)

        self.mix_first_password = QLineEdit()
        self.mix_first_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mix_first_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do primeiro PDF (opcional)", self.mix_first_password)
        self.mix_second_password = QLineEdit()
        self.mix_second_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mix_second_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do segundo PDF (opcional)", self.mix_second_password)

        self.mix_first_pace = QSpinBox()
        self.mix_first_pace.setRange(1, 1000)
        self.mix_first_pace.setValue(1)
        form.addRow("Páginas do primeiro PDF por bloco", self.mix_first_pace)
        self.mix_second_pace = QSpinBox()
        self.mix_second_pace.setRange(1, 1000)
        self.mix_second_pace.setValue(1)
        form.addRow("Páginas do segundo PDF por bloco", self.mix_second_pace)
        self.mix_reverse_second = QCheckBox("Inverter a ordem das páginas do segundo PDF")
        form.addRow("", self.mix_reverse_second)

        layout.addLayout(form)
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        mix_button = QPushButton("Misturar PDFs")
        mix_button.setObjectName("primaryButton")
        mix_button.clicked.connect(self._mix_pdfs)
        actions.addWidget(mix_button)
        layout.addLayout(actions)
        return page

    def _select_mix_first_pdf(self) -> None:
        path = self._choose_pdf("Escolher o primeiro PDF.")
        if path:
            self.mix_first_path.setText(path)

    def _select_mix_second_pdf(self) -> None:
        path = self._choose_pdf("Escolher o segundo PDF.")
        if path:
            self.mix_second_path.setText(path)

    def _mix_pdfs(self) -> None:
        first = self.mix_first_path.text().strip()
        second = self.mix_second_path.text().strip()
        if not first:
            QMessageBox.information(self, self._t("Misturar PDFs"), self._t("Escolha o primeiro PDF."))
            return
        if not second:
            QMessageBox.information(self, self._t("Misturar PDFs"), self._t("Escolha o segundo PDF."))
            return
        output = self._require_output_pdf(
            f"{Path(first).stem}-misturado.pdf", source_paths=[first, second]
        )
        if not output:
            return

        first_ranges = self.mix_first_ranges.text().strip() or None
        second_ranges = self.mix_second_ranges.text().strip() or None
        first_password = self.mix_first_password.text() or None
        second_password = self.mix_second_password.text() or None
        first_pace = self.mix_first_pace.value()
        second_pace = self.mix_second_pace.value()
        reverse_second = self.mix_reverse_second.isChecked()
        self.mix_first_password.clear()
        self.mix_second_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Misturando PDFs…",
            lambda: f"PDFs misturados: {mix_pdfs(first, second, output, first_page_ranges=first_ranges, second_page_ranges=second_ranges, reverse_second=reverse_second, first_pace=first_pace, second_pace=second_pace, first_password=first_password, second_password=second_password, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_insert_pages_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Inserir páginas de um PDF repetidamente dentro de outro",
            "Escolha o PDF de destino e o arquivo que contém as páginas a inserir.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.insert_target_path = QLineEdit()
        self.insert_target_path.setReadOnly(True)
        target_browse = QPushButton("Escolher PDF")
        target_browse.clicked.connect(self._select_insert_target_pdf)
        target_row = QHBoxLayout()
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.addWidget(self.insert_target_path, 1)
        target_row.addWidget(target_browse)
        target_container = QWidget()
        target_container.setLayout(target_row)
        form.addRow("PDF de destino", target_container)

        self.insert_source_path = QLineEdit()
        self.insert_source_path.setReadOnly(True)
        source_browse = QPushButton("Escolher PDF")
        source_browse.clicked.connect(self._select_insert_source_pdf)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.insert_source_path, 1)
        source_row.addWidget(source_browse)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("PDF com páginas a inserir", source_container)

        self.insert_ranges = QLineEdit()
        self.insert_ranges.setPlaceholderText("Deixe em branco para usar todas as páginas; exemplo: 1-3, 5.")
        form.addRow("Páginas a inserir (opcional)", self.insert_ranges)
        self.insert_every_n = QSpinBox()
        self.insert_every_n.setRange(1, 100000)
        self.insert_every_n.setValue(1)
        form.addRow("Inserir após cada N páginas", self.insert_every_n)

        self.insert_target_password = QLineEdit()
        self.insert_target_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.insert_target_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF de destino (opcional)", self.insert_target_password)
        self.insert_source_password = QLineEdit()
        self.insert_source_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.insert_source_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF a inserir (opcional)", self.insert_source_password)

        layout.addLayout(form)
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        insert_button = QPushButton("Inserir páginas")
        insert_button.setObjectName("primaryButton")
        insert_button.clicked.connect(self._insert_pages_repeatedly)
        actions.addWidget(insert_button)
        layout.addLayout(actions)
        return page

    def _select_insert_target_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF de destino.")
        if path:
            self.insert_target_path.setText(path)

    def _select_insert_source_pdf(self) -> None:
        path = self._choose_pdf("Escolher o PDF que contém as páginas a inserir.")
        if path:
            self.insert_source_path.setText(path)

    def _insert_pages_repeatedly(self) -> None:
        target = self.insert_target_path.text().strip()
        source = self.insert_source_path.text().strip()
        if not target:
            QMessageBox.information(self, self._t("Inserir páginas"), self._t("Escolha o PDF de destino."))
            return
        if not source:
            QMessageBox.information(
                self, self._t("Inserir páginas"), self._t("Escolha o PDF que contém as páginas a inserir.")
            )
            return
        output = self._require_output_pdf(
            f"{Path(target).stem}-com-paginas-inseridas.pdf", source_paths=[target, source]
        )
        if not output:
            return

        ranges = self.insert_ranges.text().strip() or None
        every_n_pages = self.insert_every_n.value()
        target_password = self.insert_target_password.text() or None
        insert_password = self.insert_source_password.text() or None
        self.insert_target_password.clear()
        self.insert_source_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Inserindo páginas…",
            lambda: f"PDF com páginas inseridas: {insert_pages_repeatedly(target, source, output, every_n_pages=every_n_pages, insert_page_ranges=ranges, target_password=target_password, insert_password=insert_password, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_extract_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Salvar somente as páginas necessárias",
            "Escolha o documento e informe os números das páginas ou intervalos que deseja manter.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.extract_path = QLineEdit()
        self.extract_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_extract_pdf)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.extract_path, 1)
        source_row.addWidget(browse)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("Arquivo de origem", source_container)

        self.extract_ranges = QLineEdit("1-3")
        self.extract_ranges.setPlaceholderText("Ex.: 1-3, 5, 8-10")
        form.addRow("Páginas", self.extract_ranges)
        self.extract_password = QLineEdit()
        self.extract_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.extract_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.extract_password)
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
            QMessageBox.information(self, self._t("Escolher PDF"), self._t("Escolha o PDF de origem."))
            return
        output = self._require_output_pdf(f"{Path(source).stem}-paginas.pdf", source_paths=[source])
        if not output:
            return
        allow_duplicates = self.extract_allow_duplicates.isChecked()
        password = self.extract_password.text() or None
        self.extract_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Extraindo páginas…",
            lambda: f"Páginas extraídas: {extract_pages(source, ranges, output, allow_duplicates=allow_duplicates, password=password, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_delete_pages_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Excluir páginas de um PDF",
            "Informe as páginas que deseja remover. O PDF original será preservado e o resultado será salvo em outro arquivo.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.delete_pages_path = QLineEdit()
        self.delete_pages_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_delete_pages_pdf)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.delete_pages_path, 1)
        source_row.addWidget(browse)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("Arquivo de origem", source_container)

        self.delete_pages_ranges = QLineEdit()
        self.delete_pages_ranges.setPlaceholderText("Ex.: 2, 4-6, 9")
        form.addRow("Páginas a excluir", self.delete_pages_ranges)

        self.delete_pages_password = QLineEdit()
        self.delete_pages_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.delete_pages_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.delete_pages_password)

        helper = QLabel(
            "Use números ou intervalos, como 2, 4-6. É necessário manter pelo menos uma página no PDF resultante."
        )
        helper.setObjectName("muted")
        helper.setWordWrap(True)
        layout.addLayout(form)
        layout.addWidget(helper)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        delete_button = QPushButton("Excluir páginas")
        delete_button.setObjectName("primaryButton")
        delete_button.clicked.connect(self._delete_pdf_pages)
        button_row.addWidget(delete_button)
        layout.addLayout(button_row)
        return page

    def _select_delete_pages_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para excluir páginas")
        if path:
            self.delete_pages_path.setText(path)

    def _delete_pdf_pages(self) -> None:
        source = self.delete_pages_path.text().strip()
        ranges = self.delete_pages_ranges.text().strip()
        if not source:
            QMessageBox.information(
                self, self._t("Excluir páginas"), self._t("Escolha o PDF de origem.")
            )
            return
        if not ranges:
            QMessageBox.information(
                self, self._t("Excluir páginas"), self._t("Informe as páginas que deseja excluir.")
            )
            return

        output = self._require_output_pdf(
            f"{Path(source).stem}-sem-paginas.pdf", source_paths=[source]
        )
        if not output:
            return
        password = self.delete_pages_password.text() or None
        self.delete_pages_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Excluindo páginas…",
            lambda: f"Páginas removidas: {delete_pages(source, ranges, output, password=password, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_rotate_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Corrigir a orientação das páginas",
            "Gire todas as páginas do documento ou informe um intervalo específico. Os conteúdos não são rasterizados.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.rotate_path = QLineEdit()
        self.rotate_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_rotate_pdf)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
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
        self.rotate_password = QLineEdit()
        self.rotate_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.rotate_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.rotate_password)
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
            QMessageBox.information(self, self._t("Escolher PDF"), self._t("Escolha o PDF de origem."))
            return
        angle = (90, 180, 270)[self.rotate_angle.currentIndex()]
        ranges = self.rotate_ranges.text().strip() or None
        output = self._require_output_pdf(f"{Path(source).stem}-rotacionado.pdf", source_paths=[source])
        if not output:
            return
        password = self.rotate_password.text() or None
        self.rotate_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Girando páginas…",
            lambda: f"PDF rotacionado: {rotate_pdf(source, output, angle, ranges, password=password, file_mode=file_mode)}",
            output_location=output,
        )

    def _build_split_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Dividir o PDF em arquivos menores",
            "Divida o PDF por página, grupos de páginas, tamanho aproximado ou marcadores do sumário.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.split_path = QLineEdit()
        self.split_path.setReadOnly(True)
        self._split_custom_directory = False
        browse_pdf = QPushButton("Escolher PDF")
        browse_pdf.clicked.connect(self._select_split_pdf)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
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
        directory_row.setContentsMargins(0, 0, 0, 0)
        directory_row.addWidget(self.split_directory, 1)
        directory_row.addWidget(browse_dir)
        directory_container = QWidget()
        directory_container.setLayout(directory_row)
        form.addRow("Pasta de saída", directory_container)

        self.split_mode = QComboBox()
        for label, data in [
            ("Um arquivo por página", "each_page"),
            ("A cada N páginas", "every_n_pages"),
            ("Após páginas específicas", "after_pages"),
            ("Após páginas pares", "after_even_pages"),
            ("Após páginas ímpares", "after_odd_pages"),
            ("Por tamanho aproximado", "by_size"),
            ("Por marcadores do sumário", "by_bookmarks"),
        ]:
            self.split_mode.addItem(label, data)
        self.split_mode.currentIndexChanged.connect(self._update_split_mode_controls)
        form.addRow("Modo de divisão", self.split_mode)

        self.split_pages_per_file = QSpinBox()
        self.split_pages_per_file.setRange(1, 10000)
        self.split_pages_per_file.setValue(10)
        form.addRow("Páginas por arquivo", self.split_pages_per_file)
        self.split_after_pages = QLineEdit()
        self.split_after_pages.setPlaceholderText("Ex.: 2, 5, 10")
        form.addRow("Páginas após as quais dividir", self.split_after_pages)
        self.split_target_mb = QDoubleSpinBox()
        self.split_target_mb.setDecimals(1)
        self.split_target_mb.setRange(0.1, 1000.0)
        self.split_target_mb.setSingleStep(0.5)
        self.split_target_mb.setValue(10.0)
        self.split_target_mb.setSuffix(" MB")
        form.addRow("Tamanho alvo por arquivo", self.split_target_mb)
        self.split_bookmark_level = QSpinBox()
        self.split_bookmark_level.setRange(1, 10)
        self.split_bookmark_level.setValue(1)
        form.addRow("Nível do marcador", self.split_bookmark_level)
        self.split_bookmark_pattern = QLineEdit()
        self.split_bookmark_pattern.setPlaceholderText("Filtro opcional; use uma expressão regular")
        form.addRow("Filtrar marcador (expressão regular, opcional)", self.split_bookmark_pattern)
        self.split_password = QLineEdit()
        self.split_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.split_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.split_password)
        self._split_form = form
        layout.addLayout(form)
        note = QLabel("O tamanho é aproximado; um PDF de uma única página pode exceder o limite.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        split = QPushButton("Dividir PDF")
        split.setObjectName("primaryButton")
        split.clicked.connect(self._split_pdf)
        actions.addWidget(split)
        layout.addLayout(actions)
        self._update_split_mode_controls()
        return page

    def _update_split_mode_controls(self, *_args) -> None:
        mode = str(self.split_mode.currentData())
        rows = (
            (self.split_pages_per_file, mode == "every_n_pages"),
            (self.split_after_pages, mode == "after_pages"),
            (self.split_target_mb, mode == "by_size"),
            (self.split_bookmark_level, mode == "by_bookmarks"),
            (self.split_bookmark_pattern, mode == "by_bookmarks"),
        )
        for widget, visible in rows:
            widget.setVisible(visible)
            label = self._split_form.labelForField(widget)
            if label is not None:
                label.setVisible(visible)

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
            QMessageBox.information(self, self._t("Dividir PDF"), self._t("Escolha o PDF e uma pasta de saída."))
            return
        mode = str(self.split_mode.currentData())
        password = self.split_password.text() or None
        self.split_password.clear()
        arguments = {
            "mode": mode,
            "pages_per_file": self.split_pages_per_file.value(),
            "split_after_pages": self.split_after_pages.text().strip() or None,
            "target_size_mb": self.split_target_mb.value(),
            "bookmark_level": self.split_bookmark_level.value(),
            "bookmark_pattern": self.split_bookmark_pattern.text().strip() or None,
            "password": password,
            "file_mode": self._output_file_mode(),
        }
        self._run_task(
            self._t("Dividindo PDF em arquivos…"),
            lambda: self._t("{count} arquivos criados em: {directory}").format(
                count=len(split_pdf(source, directory, **arguments)),
                directory=directory,
            ),
            output_location=directory,
        )

    def _select_reorder_pdf(self) -> None:
        path = self._choose_pdf(self._t("Reordenar PDF"))
        if not path:
            return
        password: str | None = None
        try:
            if pdf_requires_user_password(path):
                password, accepted = QInputDialog.getText(
                    self,
                    self._t("Senha do PDF"),
                    self._t("O arquivo '{name}' está protegido. Digite a senha:").format(name=Path(path).name),
                    QLineEdit.EchoMode.Password,
                )
                if not accepted:
                    return
                if not password:
                    QMessageBox.information(
                        self,
                        self._t("Senha necessária"),
                        self._t("Informe uma senha não vazia para continuar."),
                    )
                    return
            count = pdf_page_count(path, password=password or None)
            source_stat = Path(path).stat()
        except Exception as error:
            QMessageBox.warning(
                self,
                self._t("Não foi possível abrir o PDF"),
                self._t(friendly_error_message(error)),
            )
            return
        # Invalidate queued signals from the previous PDF and retire its render
        # worker without blocking the GUI thread on a large document.
        self._reorder_generation += 1
        thumbnail_worker = self.reorder_thumbnail_worker
        if thumbnail_worker is not None:
            self._retired_thumbnail_workers.append(thumbnail_worker)
            thumbnail_worker.finished.connect(
                self._cleanup_retired_thumbnail_worker
            )
            thumbnail_worker.requestInterruption()
            if not thumbnail_worker.isRunning():
                self._cleanup_retired_thumbnail_worker_for(thumbnail_worker)
            self.reorder_thumbnail_worker = None
        self._reorder_source_signature = (
            source_stat.st_size, source_stat.st_mtime_ns
        )
        self._reorder_items_by_page.clear()
        self.reorder_path.setText(path)
        self.reorder_password = password or None
        if self.reorder_document is not None:
            self.reorder_document.close()
            self.reorder_document.deleteLater()
        self.reorder_document = QPdfDocument(self)
        if password:
            self.reorder_document.setPassword(password)
        self.reorder_document.load(path)
        if self.reorder_document.pageCount() != count:
            self.reorder_document.close()
            self.reorder_document.deleteLater()
            self.reorder_document = None
        self.reorder_list.clear()
        for page_number in range(1, count + 1):
            item = QListWidgetItem(
                self._t("Página {number}").format(number=f"{page_number:02d}")
            )
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setSizeHint(QSize(116, 172))
            self.reorder_list.addItem(item)
            self._reorder_items_by_page[page_number] = item
        if count:
            self.reorder_list.setCurrentRow(0)
            thumbnail_worker = PageThumbnailWorker(path, password or None, self)
            generation = self._reorder_generation
            thumbnail_worker.thumbnail_ready.connect(
                lambda number, image, current=generation:
                    self._set_reorder_thumbnail(number, image, current)
            )
            thumbnail_worker.failed.connect(
                lambda message, current=generation:
                    self._thumbnail_render_failed(message, current)
            )
            self.reorder_thumbnail_worker = thumbnail_worker
            thumbnail_worker.start()
        self._set_status("{count} páginas carregadas. Arraste para reorganizar.", count=count)

    def _cleanup_retired_thumbnail_worker_for(
        self, worker: PageThumbnailWorker
    ) -> None:
        if worker not in self._retired_thumbnail_workers:
            return
        self._retired_thumbnail_workers.remove(worker)
        worker.deleteLater()

    def _cleanup_retired_thumbnail_worker(self) -> None:
        worker = self.sender()
        if isinstance(worker, PageThumbnailWorker):
            self._cleanup_retired_thumbnail_worker_for(worker)

    def _set_reorder_thumbnail(
        self, page_number: int, image: QImage, generation: int | None = None
    ) -> None:
        """Assign a thumbnail only when it belongs to the currently selected PDF."""
        if generation is not None and generation != self._reorder_generation:
            return
        item = self._reorder_items_by_page.get(page_number)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(image)))

    def _thumbnail_render_failed(
        self, message: str, generation: int | None = None
    ) -> None:
        if generation is not None and generation != self._reorder_generation:
            return
        self._set_status(message)

    def _preview_reorder_page(self, row: int) -> None:
        document = self.reorder_document
        item = self.reorder_list.item(row) if row >= 0 else None
        if item is None:
            self.reorder_preview.setPixmap(QPixmap())
            self.reorder_preview.setText(self._t("Selecione uma página para visualizar."))
            return
        if document is None:
            self.reorder_preview.setPixmap(QPixmap())
            self.reorder_preview.setText(self._t("Prévia indisponível para este PDF."))
            return
        original_page_number = int(item.data(Qt.ItemDataRole.UserRole))
        page_index = original_page_number - 1
        if page_index < 0 or page_index >= document.pageCount():
            self.reorder_preview.setPixmap(QPixmap())
            self.reorder_preview.setText(self._t("Não foi possível gerar a prévia desta página."))
            return
        try:
            point_size = document.pagePointSize(page_index)
            if point_size.width() <= 0 or point_size.height() <= 0:
                raise ValueError("Page dimensions are not available")
            scale = min(320 / point_size.width(), 440 / point_size.height())
            render_size = QSize(
                max(1, round(point_size.width() * scale)),
                max(1, round(point_size.height() * scale)),
            )
            page_image = document.render(page_index, render_size)
            if page_image.isNull():
                raise ValueError("The PDF renderer returned an empty image")
            pixmap = QPixmap.fromImage(page_image)
            self.reorder_preview.setText("")
            self.reorder_preview.setPixmap(
                pixmap.scaled(
                    self.reorder_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.reorder_preview.setToolTip(
                self._t("Página {number}").format(number=original_page_number)
            )
        except Exception:
            self.reorder_preview.setPixmap(QPixmap())
            self.reorder_preview.setText(
                self._t("Não foi possível gerar a prévia desta página.")
            )

    def _reorder_pdf(self) -> None:
        source = self.reorder_path.text().strip()
        if not source or not self.reorder_list.count():
            QMessageBox.information(self, self._t("Reordenar PDF"), self._t("Escolha um PDF para reorganizar suas páginas."))
            return
        try:
            current_stat = Path(source).stat()
        except OSError:
            QMessageBox.warning(
                self,
                self._t("Reordenar PDF"),
                self._t("Não foi possível acessar o PDF de origem. Escolha o arquivo novamente."),
            )
            return
        current_signature = (current_stat.st_size, current_stat.st_mtime_ns)
        if self._reorder_source_signature is None or current_signature != self._reorder_source_signature:
            QMessageBox.warning(
                self,
                self._t("Reordenar PDF"),
                self._t("O PDF foi alterado desde a seleção. Escolha o arquivo novamente antes de reordenar."),
            )
            return
        order = [
            int(self.reorder_list.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self.reorder_list.count())
        ]
        output = self._require_output_pdf(f"{Path(source).stem}-reordenado.pdf", source_paths=[source])
        if not output:
            return
        file_mode = self._output_file_mode()
        password = self.reorder_password
        self._run_task(
            self._t("Reordenar PDF"),
            lambda: self._t("PDF reordenado: {path}").format(
                path=reorder_pdf_pages(source, order, output, password=password, file_mode=file_mode)
            ),
            output_location=output,
        )

    def _build_reorder_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Reordenar páginas",
            "Escolha um PDF para reorganizar suas páginas. Visualize todas as páginas e arraste para definir a ordem final; todas devem permanecer na lista.",
        )
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        self.reorder_path = QLineEdit()
        self.reorder_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_reorder_pdf)
        path_row.addWidget(self.reorder_path, 1)
        path_row.addWidget(browse)
        path_container = QWidget()
        path_container.setLayout(path_row)
        layout.addWidget(path_container)
        self.reorder_list = ReorderablePageList()
        self.reorder_list.setObjectName("reorderPageList")
        self.reorder_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.reorder_list.setAlternatingRowColors(False)
        self.reorder_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.reorder_list.setFlow(QListWidget.Flow.LeftToRight)
        self.reorder_list.setWrapping(True)
        # Single-pass responsive layout avoids batched thumbnail recycling
        # while a custom drag/drop reorders model rows and adapts to window resizes.
        self.reorder_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.reorder_list.setMovement(QListWidget.Movement.Static)
        self.reorder_list.setLayoutMode(QListWidget.LayoutMode.SinglePass)
        self.reorder_list.setIconSize(QSize(76, 96))
        self.reorder_list.setGridSize(QSize(124, 184))
        self.reorder_list.setItemDelegate(ReorderPageDelegate(self.reorder_list))
        self.reorder_list.setWordWrap(True)
        self.reorder_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.reorder_list.setUniformItemSizes(True)
        self.reorder_list.setDragEnabled(True)
        self.reorder_list.setAcceptDrops(True)
        self.reorder_list.setDropIndicatorShown(True)
        # This class performs its own row move in dropEvent; use DragDrop
        # instead of Qt's native InternalMove post-drop source cleanup.
        self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.reorder_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.reorder_list.currentRowChanged.connect(self._preview_reorder_page)
        reorder_controls = QHBoxLayout()
        reorder_controls.setContentsMargins(0, 0, 0, 0)
        move_up = QPushButton("↑  Subir")
        move_up.clicked.connect(lambda: self._move_selected(self.reorder_list, -1))
        move_down = QPushButton("↓  Descer")
        move_down.clicked.connect(lambda: self._move_selected(self.reorder_list, 1))
        reorder_controls.addWidget(move_up)
        reorder_controls.addWidget(move_down)
        reorder_controls.addStretch(1)
        layout.addLayout(reorder_controls)
        preview_row = QHBoxLayout()
        preview_row.setContentsMargins(0, 0, 0, 0)
        preview_row.addWidget(self.reorder_list, 1)
        preview_column = QVBoxLayout()
        preview_title = QLabel("Prévia da página selecionada")
        preview_title.setObjectName("sectionTitle")
        preview_column.addWidget(preview_title)
        self.reorder_preview = QLabel("Selecione uma página para visualizar.")
        self.reorder_preview.setObjectName("pagePreview")
        self.reorder_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reorder_preview.setMinimumSize(250, 320)
        self.reorder_preview.setMaximumWidth(380)
        self.reorder_preview.setWordWrap(True)
        preview_column.addWidget(self.reorder_preview, 1)
        preview_container = QWidget()
        preview_container.setLayout(preview_column)
        preview_row.addWidget(preview_container, 1)
        layout.addLayout(preview_row, 1)
        self.reorder_document: QPdfDocument | None = None
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        self.reorder_password = None
        note = QLabel("Arraste as miniaturas para organizar as páginas. Os números indicam as páginas originais.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        actions.addWidget(note, 1)
        save = QPushButton("Salvar PDF reordenado")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._reorder_pdf)
        actions.addWidget(save)
        layout.addLayout(actions)
        return page

    def _build_stamp_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Marca d'água e numeração",
            "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água. O conteúdo original não é rasterizado.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.stamp_path = QLineEdit()
        self.stamp_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_stamp_pdf)
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.addWidget(self.stamp_path, 1)
        file_row.addWidget(browse)
        file_container = QWidget()
        file_container.setLayout(file_row)
        form.addRow("PDF de origem", file_container)
        self.stamp_text = QLineEdit()
        self.stamp_text.setPlaceholderText("Ex.: CONFIDENCIAL")
        form.addRow("Texto da marca d'água", self.stamp_text)
        self.stamp_numbering = QCheckBox("Adicionar numeração de páginas")
        form.addRow("", self.stamp_numbering)
        self.stamp_ranges = QLineEdit()
        self.stamp_ranges.setPlaceholderText("Deixe vazio para aplicar em todas as páginas")
        self.stamp_ranges.setToolTip(
            "O texto e a numeração serão aplicados apenas às páginas selecionadas. A numeração conserva o número original da página."
        )
        form.addRow("Páginas (opcional)", self.stamp_ranges)
        self.stamp_watermark_position = QComboBox()
        self.stamp_watermark_position.addItem("Diagonal (centro)", "diagonal")
        self.stamp_watermark_position.addItem("Centralizada", "center")
        self.stamp_watermark_position.addItem("Rodapé central", "bottom-center")
        form.addRow("Posição da marca d'água", self.stamp_watermark_position)
        self.stamp_number_position = QComboBox()
        self.stamp_number_position.addItem("Rodapé direito", "bottom-right")
        self.stamp_number_position.addItem("Rodapé centralizado", "bottom-center")
        form.addRow("Posição da numeração", self.stamp_number_position)
        self.stamp_font_size = QSpinBox()
        self.stamp_font_size.setRange(8, 120)
        self.stamp_font_size.setValue(34)
        form.addRow("Tamanho do texto", self.stamp_font_size)
        self.stamp_opacity = QDoubleSpinBox()
        self.stamp_opacity.setRange(0.05, 1.0)
        self.stamp_opacity.setSingleStep(0.05)
        self.stamp_opacity.setValue(0.22)
        form.addRow("Opacidade", self.stamp_opacity)
        self.stamp_password = QLineEdit()
        self.stamp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.stamp_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.stamp_password)
        layout.addLayout(form)
        actions = QHBoxLayout()
        actions.addStretch(1)
        apply_button = QPushButton("Aplicar marca d'água/numeração")
        apply_button.setObjectName("primaryButton")
        apply_button.clicked.connect(self._apply_stamp)
        actions.addWidget(apply_button)
        layout.addLayout(actions)
        return page

    def _select_stamp_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para marca d'água/numeração")
        if path:
            self.stamp_path.setText(path)

    def _apply_stamp(self) -> None:
        source = self.stamp_path.text().strip()
        if not source:
            QMessageBox.information(self, self._t("Escolher PDF"), self._t("Escolha o PDF de origem."))
            return
        text = self.stamp_text.text().strip()
        numbering = self.stamp_numbering.isChecked()
        if not text and not numbering:
            QMessageBox.information(
                self, self._t("Marca d'água e numeração"),
                self._t("Informe o texto da marca d'água ou ative a numeração de páginas."),
            )
            return
        output = self._require_output_pdf(f"{Path(source).stem}-marcado.pdf", source_paths=[source])
        if not output:
            return
        password = self.stamp_password.text() or None
        self.stamp_password.clear()
        file_mode = self._output_file_mode()
        watermark_position = str(self.stamp_watermark_position.currentData())
        page_number_position = str(self.stamp_number_position.currentData())
        page_ranges = self.stamp_ranges.text().strip() or None
        font_size = self.stamp_font_size.value()
        opacity = self.stamp_opacity.value()
        self._run_task(
            self._t("Aplicar marca d'água/numeração"),
            lambda: self._t("PDF carimbado: {path}").format(
                path=stamp_pdf(
                    source, output,
                    watermark_text=text or None,
                    page_numbering=numbering,
                    page_ranges=page_ranges,
                    watermark_position=watermark_position,
                    page_number_position=page_number_position,
                    font_size=font_size,
                    opacity=opacity,
                    password=password,
                    file_mode=file_mode,
                )
            ),
            output_location=output,
        )

    def _build_optimize_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Otimizar PDF",
            "Escolha entre preservar a qualidade (sem perdas) ou reduzir o tamanho recomprimindo imagens. O modo sem perdas comprime streams e remove objetos redundantes; o modo equilibrado também recomprime imagens opacas.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.optimize_path = QLineEdit()
        self.optimize_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_optimize_pdf)
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.addWidget(self.optimize_path, 1)
        file_row.addWidget(browse)
        file_container = QWidget()
        file_container.setLayout(file_row)
        form.addRow("PDF de origem para otimizar", file_container)
        self.optimize_mode = QComboBox()
        self.optimize_mode.addItem("Sem perdas (mais conservador)", "lossless")
        self.optimize_mode.addItem("Equilibrada (recomprimir imagens)", "balanced")
        self.optimize_mode.setCurrentIndex(self.optimize_mode.findData("balanced"))
        form.addRow("Modo de otimização", self.optimize_mode)
        self.optimize_quality = QSpinBox()
        self.optimize_quality.setRange(50, 95)
        self.optimize_quality.setValue(82)
        self.optimize_quality.setSuffix(" / 100")
        self.optimize_quality.setToolTip("O modo sem perdas não altera a qualidade das imagens; use o modo equilibrado para aplicar este valor.")
        form.addRow("Qualidade das imagens", self.optimize_quality)
        self.optimize_password = QLineEdit()
        self.optimize_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.optimize_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.optimize_password)
        warning = QLabel("O modo equilibrado recomprime imagens sem transparência; a qualidade visual pode diminuir. A redução depende do conteúdo do PDF.")
        warning.setObjectName("muted")
        warning.setWordWrap(True)
        layout.addLayout(form)
        layout.addWidget(warning)
        actions = QHBoxLayout()
        actions.addStretch(1)
        optimize = QPushButton("Reduzir tamanho do PDF")
        optimize.setObjectName("primaryButton")
        optimize.clicked.connect(self._optimize_pdf)
        actions.addWidget(optimize)
        layout.addLayout(actions)
        self.optimize_mode.currentIndexChanged.connect(self._update_optimize_quality_state)
        self._update_optimize_quality_state()
        return page

    def _update_optimize_quality_state(self) -> None:
        self.optimize_quality.setEnabled(self.optimize_mode.currentData() == "balanced")

    def _select_optimize_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para otimizar")
        if path:
            self.optimize_path.setText(path)

    @staticmethod
    def _format_size(size: int) -> str:
        units = ("B", "KB", "MB", "GB")
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} GB"

    def _optimize_pdf(self) -> None:
        source = self.optimize_path.text().strip()
        if not source:
            QMessageBox.information(self, self._t("Otimizar PDF"), self._t("Escolha o PDF de origem."))
            return
        output = self._require_output_pdf(f"{Path(source).stem}-otimizado.pdf", source_paths=[source])
        if not output:
            return
        mode = str(self.optimize_mode.currentData())
        quality = self.optimize_quality.value()
        password = self.optimize_password.text() or None
        self.optimize_password.clear()
        file_mode = self._output_file_mode()

        def task() -> str:
            result = optimize_pdf(
                source, output, mode=mode, quality=quality,
                password=password, file_mode=file_mode,
            )
            old_size = Path(source).stat().st_size
            new_size = result.stat().st_size
            if new_size < old_size:
                percent = round((old_size - new_size) / old_size * 100) if old_size else 0
                template = "PDF otimizado: {old} → {new} ({percent}% menor)"
            else:
                percent = 0
                template = "Não houve redução de tamanho: {old} → {new}"
            message = self._t(template).format(
                old=self._format_size(old_size),
                new=self._format_size(new_size),
                percent=percent,
            )
            mode_label = "Otimização equilibrada" if mode == "balanced" else "Otimização sem perdas"
            return message + " — " + self._t(mode_label)

        self._run_task(self._t("Reduzir tamanho do PDF"), task, output_location=output)

    def _build_pipeline_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Processar um PDF em várias etapas",
            "Etapas executadas nesta ordem: rotação, marca d'água/numeração e otimização. O arquivo original é preservado.",
        )
        profile_actions = QGridLayout()
        save_profile = QPushButton("Salvar perfil")
        save_profile.clicked.connect(self._save_pipeline_profile)
        load_profile = QPushButton("Carregar perfil")
        load_profile.clicked.connect(self._load_pipeline_profile)
        delete_profile = QPushButton("Excluir perfil")
        delete_profile.clicked.connect(self._delete_pipeline_profile)
        export_profile = QPushButton("Exportar perfil")
        export_profile.clicked.connect(self._export_pipeline_profile)
        import_profile = QPushButton("Importar perfil")
        import_profile.clicked.connect(self._import_pipeline_profile)
        profile_actions.addWidget(save_profile, 0, 0)
        profile_actions.addWidget(load_profile, 0, 1)
        profile_actions.addWidget(delete_profile, 1, 0)
        profile_actions.addWidget(export_profile, 1, 1)
        profile_actions.addWidget(import_profile, 2, 0, 1, 2)
        profile_actions.setColumnStretch(0, 1)
        profile_actions.setColumnStretch(1, 1)
        layout.addLayout(profile_actions)
        profile_note = QLabel(
            "Os perfis guardam somente as opções do fluxo; não incluem caminho do PDF nem senha."
        )
        profile_note.setObjectName("muted")
        profile_note.setWordWrap(True)
        layout.addWidget(profile_note)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.pipeline_path = QLineEdit()
        self.pipeline_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_pipeline_pdf)
        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
        file_row.addWidget(self.pipeline_path, 1)
        file_row.addWidget(browse)
        file_container = QWidget()
        file_container.setLayout(file_row)
        form.addRow("PDF de origem", file_container)

        self.pipeline_password = QLineEdit()
        self.pipeline_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pipeline_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.pipeline_password)

        self.pipeline_rotate_enabled = QCheckBox("Aplicar rotação")
        form.addRow("", self.pipeline_rotate_enabled)
        self.pipeline_rotate_angle = QComboBox()
        self.pipeline_rotate_angle.addItem("90° no sentido horário", 90)
        self.pipeline_rotate_angle.addItem("180°", 180)
        self.pipeline_rotate_angle.addItem("270° no sentido horário", 270)
        form.addRow("Rotação", self.pipeline_rotate_angle)
        self.pipeline_rotate_ranges = QLineEdit()
        self.pipeline_rotate_ranges.setPlaceholderText("Deixe vazio para girar todas as páginas")
        form.addRow("Páginas (opcional)", self.pipeline_rotate_ranges)

        self.pipeline_stamp_enabled = QCheckBox("Aplicar marca d'água/numeração")
        form.addRow("", self.pipeline_stamp_enabled)
        self.pipeline_stamp_text = QLineEdit()
        self.pipeline_stamp_text.setPlaceholderText("Ex.: CONFIDENCIAL")
        form.addRow("Texto da marca d'água (opcional)", self.pipeline_stamp_text)
        self.pipeline_numbering = QCheckBox("Adicionar numeração de páginas")
        form.addRow("", self.pipeline_numbering)
        self.pipeline_stamp_ranges = QLineEdit()
        self.pipeline_stamp_ranges.setPlaceholderText("Deixe vazio para aplicar em todas as páginas")
        self.pipeline_stamp_ranges.setToolTip(
            "O texto e a numeração serão aplicados apenas às páginas selecionadas. A numeração conserva o número original da página."
        )
        form.addRow("Páginas (opcional)", self.pipeline_stamp_ranges)

        self.pipeline_optimize_enabled = QCheckBox("Aplicar otimização")
        form.addRow("", self.pipeline_optimize_enabled)
        self.pipeline_optimize_mode = QComboBox()
        self.pipeline_optimize_mode.addItem("Sem perdas (mais conservador)", "lossless")
        self.pipeline_optimize_mode.addItem("Equilibrada (recomprimir imagens)", "balanced")
        form.addRow("Modo de otimização", self.pipeline_optimize_mode)
        self.pipeline_optimize_quality = QSpinBox()
        self.pipeline_optimize_quality.setRange(50, 95)
        self.pipeline_optimize_quality.setValue(82)
        self.pipeline_optimize_quality.setSuffix(" / 100")
        form.addRow("Qualidade das imagens", self.pipeline_optimize_quality)
        self.pipeline_output_suffix = QLineEdit("-processado")
        self.pipeline_output_suffix.setPlaceholderText("-processado")
        self.pipeline_output_suffix.setToolTip(
            "Sufixo usado nos nomes dos PDFs de saída ao processar uma pasta com este perfil."
        )
        form.addRow("Sufixo dos arquivos processados em pasta", self.pipeline_output_suffix)

        layout.addLayout(form)
        note = QLabel("Qualquer etapa selecionada será executada na sequência indicada acima.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        actions = QHBoxLayout()
        actions.addStretch(1)
        run_button = QPushButton("Executar fluxo em lote")
        run_button.setObjectName("primaryButton")
        run_button.clicked.connect(self._run_pipeline)
        actions.addWidget(run_button)
        layout.addLayout(actions)

        self.pipeline_rotate_enabled.toggled.connect(self._update_pipeline_controls)
        self.pipeline_stamp_enabled.toggled.connect(self._update_pipeline_controls)
        self.pipeline_optimize_enabled.toggled.connect(self._update_pipeline_controls)
        self.pipeline_optimize_mode.currentIndexChanged.connect(self._update_pipeline_controls)
        self._update_pipeline_controls()
        return page

    def _read_pipeline_profiles(self) -> dict[str, dict[str, object]]:
        raw = self.settings.value("pipeline_profiles", "{}")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        normalized: dict[str, dict[str, object]] = {}
        changed = False
        invalid_entries = False
        for name, profile in parsed.items():
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
                invalid_entries = True
                continue
            try:
                current_profile = migrate_local_profile(profile)
            except ValueError:
                invalid_entries = True
                continue
            normalized[name.strip()] = current_profile
            changed = changed or current_profile != profile
        # Avoid rewriting settings when any unknown/invalid profile is present.
        if changed and not invalid_entries:
            self.settings.setValue(
                "pipeline_profiles", json.dumps(normalized, ensure_ascii=False, sort_keys=True)
            )
        return normalized

    def _stored_profile_names(self) -> set[str]:
        """Return raw stored profile names, including entries this version cannot parse."""
        raw = self.settings.value("pipeline_profiles", "{}")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            return set()
        if not isinstance(parsed, dict):
            return set()
        return {
            name.strip()
            for name in parsed
            if isinstance(name, str) and name.strip() and len(name.strip()) <= 80
        }

    def _confirm_pipeline_profile_replacement(
        self, name: str, profiles: dict[str, dict[str, object]], title: str
    ) -> bool:
        stored_names = self._stored_profile_names()
        if name not in profiles and name not in stored_names:
            return True
        prompt = (
            self._t("Já existe um perfil chamado '{name}'. Deseja substituí-lo?").format(name=name)
            if name in profiles
            else self._t(
                "O perfil '{name}' já existe, mas usa um esquema que esta versão não reconhece. "
                "Substituí-lo pode impedir que versões mais novas recuperem suas opções. Deseja continuar?"
            ).format(name=name)
        )
        answer = QMessageBox.question(
            self,
            self._t(title),
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _write_pipeline_profiles(self, profiles: dict[str, dict[str, object]]) -> bool:
        """Persist recognized profiles without deleting entries from newer/unknown schemas."""
        raw = self.settings.value("pipeline_profiles", "{}")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            # Do not replace malformed settings automatically; that could destroy data
            # which a newer application version may still be able to recover.
            return False
        if not isinstance(parsed, dict):
            return False

        preserved: dict[str, object] = {}
        for name, profile in parsed.items():
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
                preserved[name] = profile
                continue
            try:
                migrate_local_profile(profile)
            except ValueError:
                # If the user explicitly confirmed replacement, discard the unknown
                # schema under that normalized name instead of leaving two entries.
                if name.strip() not in profiles:
                    preserved[name] = profile

        preserved.update(profiles)
        self.settings.setValue(
            "pipeline_profiles", json.dumps(preserved, ensure_ascii=False, sort_keys=True)
        )
        return True

    def _capture_pipeline_profile(self) -> dict[str, object]:
        """Capture only processing options; never store a PDF path or password."""
        return {
            "rotate_enabled": self.pipeline_rotate_enabled.isChecked(),
            "rotate_angle": int(self.pipeline_rotate_angle.currentData()),
            "rotate_ranges": self.pipeline_rotate_ranges.text(),
            "stamp_enabled": self.pipeline_stamp_enabled.isChecked(),
            "stamp_text": self.pipeline_stamp_text.text(),
            "page_numbering": self.pipeline_numbering.isChecked(),
            "stamp_ranges": self.pipeline_stamp_ranges.text(),
            "optimize_enabled": self.pipeline_optimize_enabled.isChecked(),
            "optimize_mode": str(self.pipeline_optimize_mode.currentData()),
            "quality": self.pipeline_optimize_quality.value(),
            "output_suffix": self.pipeline_output_suffix.text(),
        }

    def _apply_pipeline_profile(self, profile: dict[str, object]) -> None:
        """Apply saved settings defensively, ignoring unknown or invalid values."""
        def boolean(key: str, default: bool) -> bool:
            value = profile.get(key, default)
            return value if isinstance(value, bool) else default

        def string(key: str, default: str = "") -> str:
            value = profile.get(key, default)
            return value if isinstance(value, str) else default

        self.pipeline_rotate_enabled.setChecked(boolean("rotate_enabled", False))
        rotate_angle = profile.get("rotate_angle", 90)
        if not isinstance(rotate_angle, int) or isinstance(rotate_angle, bool):
            rotate_angle = 90
        angle_index = self.pipeline_rotate_angle.findData(rotate_angle)
        self.pipeline_rotate_angle.setCurrentIndex(angle_index if angle_index >= 0 else 0)
        self.pipeline_rotate_ranges.setText(string("rotate_ranges"))

        self.pipeline_stamp_enabled.setChecked(boolean("stamp_enabled", False))
        self.pipeline_stamp_text.setText(string("stamp_text"))
        self.pipeline_numbering.setChecked(boolean("page_numbering", False))
        self.pipeline_stamp_ranges.setText(string("stamp_ranges"))

        self.pipeline_optimize_enabled.setChecked(boolean("optimize_enabled", False))
        optimize_mode = string("optimize_mode", "lossless")
        mode_index = self.pipeline_optimize_mode.findData(optimize_mode)
        self.pipeline_optimize_mode.setCurrentIndex(mode_index if mode_index >= 0 else 0)
        quality = profile.get("quality", 82)
        if isinstance(quality, int) and not isinstance(quality, bool):
            self.pipeline_optimize_quality.setValue(quality)
        self.pipeline_output_suffix.setText(string("output_suffix", "-processado"))
        self._update_pipeline_controls()

    def _save_pipeline_profile(self) -> None:
        name, accepted = QInputDialog.getText(
            self, self._t("Salvar perfil"), self._t("Nome do perfil:")
        )
        if not accepted:
            return
        name = name.strip()
        if not name:
            QMessageBox.information(
                self, self._t("Salvar perfil"), self._t("Informe um nome para o perfil.")
            )
            return
        if len(name) > 80:
            QMessageBox.information(
                self, self._t("Salvar perfil"), self._t("O nome do perfil deve ter até 80 caracteres.")
            )
            return
        profiles = self._read_pipeline_profiles()
        if not self._confirm_pipeline_profile_replacement(name, profiles, "Salvar perfil"):
            return
        try:
            profile = migrate_local_profile(self._capture_pipeline_profile())
        except ValueError as error:
            QMessageBox.information(self, self._t("Salvar perfil"), self._t(str(error)))
            return
        profiles[name] = profile
        if not self._write_pipeline_profiles(profiles):
            QMessageBox.warning(
                self,
                self._t("Perfis de fluxo"),
                self._t("Não foi possível alterar os perfis porque as configurações estão inválidas. Os dados existentes foram preservados."),
            )
            return
        self._set_status("Perfil salvo: {name}", name=name)

    def _load_pipeline_profile(self) -> None:
        profiles = self._read_pipeline_profiles()
        if not profiles:
            QMessageBox.information(
                self, self._t("Carregar perfil"), self._t("Nenhum perfil salvo ainda.")
            )
            return
        names = sorted(profiles, key=str.casefold)
        name, accepted = QInputDialog.getItem(
            self, self._t("Carregar perfil"), self._t("Selecione um perfil:"), names, 0, False
        )
        if not accepted:
            return
        profile = profiles.get(name)
        if profile is None:
            return
        self._apply_pipeline_profile(profile)
        self._set_status("Perfil carregado: {name}", name=name)

    def _delete_pipeline_profile(self) -> None:
        profiles = self._read_pipeline_profiles()
        if not profiles:
            QMessageBox.information(
                self, self._t("Excluir perfil"), self._t("Nenhum perfil salvo ainda.")
            )
            return
        names = sorted(profiles, key=str.casefold)
        name, accepted = QInputDialog.getItem(
            self, self._t("Excluir perfil"), self._t("Selecione um perfil:"), names, 0, False
        )
        if not accepted:
            return
        if name not in profiles:
            return
        answer = QMessageBox.question(
            self,
            self._t("Excluir perfil"),
            self._t("Deseja excluir o perfil '{name}'?").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        profiles.pop(name, None)
        if not self._write_pipeline_profiles(profiles):
            QMessageBox.warning(
                self,
                self._t("Perfis de fluxo"),
                self._t("Não foi possível alterar os perfis porque as configurações estão inválidas. Os dados existentes foram preservados."),
            )
            return
        self._set_status("Perfil excluído: {name}", name=name)

    @staticmethod
    def _validate_pipeline_profile_document(document: object) -> tuple[str, dict[str, object]]:
        """Validate a profile and migrate recognized older JSON schemas."""
        return validate_profile_document(document)

    def _export_pipeline_profile(self) -> None:
        profiles = self._read_pipeline_profiles()
        if not profiles:
            QMessageBox.information(
                self, self._t("Exportar perfil"), self._t("Nenhum perfil salvo para exportar.")
            )
            return
        names = sorted(profiles, key=str.casefold)
        name, accepted = QInputDialog.getItem(
            self, self._t("Exportar perfil"), self._t("Selecione um perfil para exportar:"), names, 0, False
        )
        if not accepted or name not in profiles:
            return
        suggested_stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip().replace(" ", "-")
        if not suggested_stem:
            suggested_stem = "pdf-hub-profile"
        output = self._choose_output_file(
            "Exportar perfil", f"{suggested_stem}.json", ".json", "Arquivos JSON (*.json)"
        )
        if output is None:
            return
        try:
            safe_name, safe_profile = self._validate_pipeline_profile_document({
                "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
                "name": name,
                "profile": profiles[name],
            })
        except ValueError:
            QMessageBox.warning(
                self,
                self._t("Exportar perfil"),
                self._t("O perfil salvo contém opções inválidas e não pode ser exportado."),
            )
            return
        document = {
            "schema_version": CURRENT_PROFILE_SCHEMA_VERSION,
            "name": safe_name,
            "profile": safe_profile,
        }
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(output.parent),
                prefix=".pdf-hub-profile-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                json.dump(document, stream, ensure_ascii=True, indent=2, sort_keys=True)
                stream.write("\n")
            temporary.replace(output)
        except OSError:
            QMessageBox.warning(
                self,
                self._t("Exportar perfil"),
                self._t("Não foi possível salvar o arquivo de perfil. Verifique a pasta e as permissões."),
            )
            return
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        self._set_status("Perfil exportado: {name}", name=name)

    def _import_pipeline_profile(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, self._t("Importar perfil"), "", self._t("Arquivos JSON (*.json)")
        )
        if not filename:
            return
        source = Path(filename).expanduser()
        try:
            if source.stat().st_size > 128 * 1024:
                raise ValueError("O arquivo de perfil excede o tamanho máximo permitido.")
            document = json.loads(source.read_text(encoding="utf-8"))
            name, profile = self._validate_pipeline_profile_document(document)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            QMessageBox.warning(
                self,
                self._t("Importar perfil"),
                self._t("O arquivo não é um perfil JSON válido do PDF Hub. Verifique a versão e as opções do arquivo."),
            )
            return
        profiles = self._read_pipeline_profiles()
        if not self._confirm_pipeline_profile_replacement(name, profiles, "Importar perfil"):
            return
        profiles[name] = profile
        if not self._write_pipeline_profiles(profiles):
            QMessageBox.warning(
                self,
                self._t("Perfis de fluxo"),
                self._t("Não foi possível alterar os perfis porque as configurações estão inválidas. Os dados existentes foram preservados."),
            )
            return
        self._set_status("Perfil importado: {name}", name=name)

    def _update_pipeline_controls(self) -> None:
        rotate_enabled = self.pipeline_rotate_enabled.isChecked()
        self.pipeline_rotate_angle.setEnabled(rotate_enabled)
        self.pipeline_rotate_ranges.setEnabled(rotate_enabled)
        stamp_enabled = self.pipeline_stamp_enabled.isChecked()
        self.pipeline_stamp_text.setEnabled(stamp_enabled)
        self.pipeline_numbering.setEnabled(stamp_enabled)
        self.pipeline_stamp_ranges.setEnabled(stamp_enabled)
        optimize_enabled = self.pipeline_optimize_enabled.isChecked()
        self.pipeline_optimize_mode.setEnabled(optimize_enabled)
        self.pipeline_optimize_quality.setEnabled(
            optimize_enabled and self.pipeline_optimize_mode.currentData() == "balanced"
        )

    def _select_pipeline_pdf(self) -> None:
        path = self._choose_pdf("Escolher PDF para fluxo em lote")
        if path:
            self.pipeline_path.setText(path)

    def _run_pipeline(self) -> None:
        source = self.pipeline_path.text().strip()
        if not source:
            QMessageBox.information(
                self, self._t("Fluxo em lote"), self._t("Escolha o PDF de origem.")
            )
            return
        rotate_enabled = self.pipeline_rotate_enabled.isChecked()
        stamp_enabled = self.pipeline_stamp_enabled.isChecked()
        optimize_enabled = self.pipeline_optimize_enabled.isChecked()
        if not (rotate_enabled or stamp_enabled or optimize_enabled):
            QMessageBox.information(
                self, self._t("Fluxo em lote"), self._t("Selecione pelo menos uma etapa do fluxo.")
            )
            return
        watermark_text = self.pipeline_stamp_text.text().strip()
        page_numbering = self.pipeline_numbering.isChecked()
        if stamp_enabled and not watermark_text and not page_numbering:
            QMessageBox.information(
                self,
                self._t("Fluxo em lote"),
                self._t("A etapa de marca d'água precisa de um texto ou da numeração ativada."),
            )
            return

        output = self._require_output_pdf(
            f"{Path(source).stem}-processado.pdf", source_paths=[source]
        )
        if not output:
            return

        password = self.pipeline_password.text() or None
        self.pipeline_password.clear()
        file_mode = self._output_file_mode()
        rotate_angle = int(self.pipeline_rotate_angle.currentData()) if rotate_enabled else None
        rotate_ranges = self.pipeline_rotate_ranges.text().strip() or None
        stamp_ranges = self.pipeline_stamp_ranges.text().strip() or None
        optimize_mode = str(self.pipeline_optimize_mode.currentData()) if optimize_enabled else None
        quality = self.pipeline_optimize_quality.value()
        if not stamp_enabled:
            watermark_text = ""
            page_numbering = False
            stamp_ranges = None

        def task() -> str:
            result = process_pdf_pipeline(
                source, output,
                rotate_angle=rotate_angle,
                rotate_ranges=rotate_ranges,
                watermark_text=watermark_text or None,
                page_numbering=page_numbering,
                stamp_ranges=stamp_ranges,
                optimize_mode=optimize_mode,
                quality=quality,
                password=password,
                file_mode=file_mode,
            )
            return self._t("Fluxo em lote concluído: {path}").format(path=result)

        self._run_task(
            self._t("Executando fluxo em lote…"), task, output_location=output
        )

    def _build_folder_batch_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Processar PDFs de uma pasta",
            "Selecione a pasta de origem e o destino, depois escolha um perfil salvo. Os arquivos originais serão preservados; PDFs com erro não interrompem os demais.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.batch_source_directory = QLineEdit()
        self.batch_source_directory.setReadOnly(True)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.batch_source_directory, 1)
        self.batch_choose_source_button = QPushButton("Escolher pasta de origem")
        self.batch_choose_source_button.clicked.connect(self._select_batch_source_directory)
        source_row.addWidget(self.batch_choose_source_button)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("Pasta de origem", source_container)

        self.batch_output_directory = QLineEdit()
        self.batch_output_directory.setReadOnly(True)
        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.addWidget(self.batch_output_directory, 1)
        self.batch_choose_output_button = QPushButton("Escolher pasta de saída")
        self.batch_choose_output_button.clicked.connect(self._select_batch_output_directory)
        output_row.addWidget(self.batch_choose_output_button)
        output_container = QWidget()
        output_container.setLayout(output_row)
        form.addRow("Pasta de saída", output_container)

        self.batch_include_subfolders = QCheckBox("Incluir subpastas")
        self.batch_include_subfolders.setChecked(False)
        self.batch_include_subfolders.setToolTip("Quando ativado, preserva a estrutura de subpastas no destino.")
        form.addRow("", self.batch_include_subfolders)
        self.batch_resume_checkbox = QCheckBox("Retomar lote interrompido, se aplicável")
        self.batch_resume_checkbox.setChecked(True)
        self.batch_resume_checkbox.setToolTip(
            "Usa resultados salvos somente quando a origem, o destino, o perfil e a lista de PDFs não mudaram. Desmarque para iniciar do zero."
        )
        form.addRow("", self.batch_resume_checkbox)
        layout.addLayout(form)
        note = QLabel(
            "O perfil também define o sufixo dos arquivos de saída. PDFs que exigem senha serão registrados como falha, sem interromper o lote."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        actions = QGridLayout()
        self.batch_run_button = QPushButton("Aplicar perfil salvo à pasta")
        self.batch_run_button.setObjectName("primaryButton")
        self.batch_run_button.clicked.connect(self._run_pipeline_folder)
        actions.addWidget(self.batch_run_button, 0, 0)
        self.batch_reprocess_failures_button = QPushButton("Reprocessar apenas falhas")
        self.batch_reprocess_failures_button.setEnabled(False)
        self.batch_reprocess_failures_button.clicked.connect(self._rerun_failed_batch_files)
        actions.addWidget(self.batch_reprocess_failures_button, 0, 1)
        self.batch_pause_button = QPushButton("Pausar lote")
        self.batch_pause_button.setEnabled(False)
        self.batch_pause_button.clicked.connect(self._toggle_batch_pause)
        actions.addWidget(self.batch_pause_button, 1, 0)
        self.batch_cancel_button = QPushButton("Cancelar lote")
        self.batch_cancel_button.setEnabled(False)
        self.batch_cancel_button.clicked.connect(self._cancel_batch)
        actions.addWidget(self.batch_cancel_button, 1, 1)
        self.batch_report_button = QPushButton("Salvar relatório CSV")
        self.batch_report_button.setEnabled(False)
        self.batch_report_button.clicked.connect(self._export_batch_report)
        actions.addWidget(self.batch_report_button, 2, 0, 1, 2)
        actions.setColumnStretch(0, 1)
        actions.setColumnStretch(1, 1)
        layout.addLayout(actions)

        history_layout = QVBoxLayout()
        history_layout.setSpacing(6)
        history_layout.addWidget(QLabel("Relatórios anteriores"))
        history_row = QGridLayout()
        self.batch_history_combo = QComboBox()
        self.batch_history_combo.setMinimumWidth(100)
        history_row.addWidget(self.batch_history_combo, 0, 0, 1, 2)
        self.batch_history_load_button = QPushButton("Carregar relatório")
        self.batch_history_load_button.clicked.connect(self._load_selected_batch_history)
        history_row.addWidget(self.batch_history_load_button, 1, 0)
        self.batch_history_delete_button = QPushButton("Excluir relatório selecionado")
        self.batch_history_delete_button.clicked.connect(self._delete_selected_batch_history)
        history_row.addWidget(self.batch_history_delete_button, 1, 1)
        history_row.setColumnStretch(0, 1)
        history_row.setColumnStretch(1, 1)
        history_layout.addLayout(history_row)
        layout.addLayout(history_layout)

        self.batch_results_table = QTableWidget(0, 4)
        self.batch_results_table.setHorizontalHeaderLabels([
            "Arquivo de origem", "Resultado", "Detalhes", "Arquivo de saída"
        ])
        self.batch_results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.batch_results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.batch_results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.batch_results_table.setAlternatingRowColors(True)
        self.batch_results_table.setWordWrap(True)
        self.batch_results_table.verticalHeader().setVisible(False)
        header = self.batch_results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.batch_results_table.setMinimumHeight(180)
        self.batch_results_table.setMaximumHeight(280)
        layout.addWidget(self.batch_results_table, 1)
        self.batch_results: list[BatchFileResult] = []
        return page

    def _select_batch_source_directory(self) -> None:
        path = self._choose_directory("Escolher pasta de origem")
        if path:
            self.batch_source_directory.setText(path)

    def _select_batch_output_directory(self) -> None:
        path = self._choose_directory("Escolher pasta de saída")
        if path:
            self.batch_output_directory.setText(path)

    def _run_pipeline_folder(self) -> None:
        source = self.batch_source_directory.text().strip()
        output = self.batch_output_directory.text().strip()
        if not source:
            QMessageBox.information(self, self._t("Processar PDFs de uma pasta"), self._t("Selecione uma pasta de origem."))
            return
        if not output or not Path(output).is_dir():
            QMessageBox.information(self, self._t("Processar PDFs de uma pasta"), self._t("Escolha uma pasta de saída existente."))
            return
        profiles = self._read_pipeline_profiles()
        if not profiles:
            QMessageBox.information(self, self._t("Aplicar perfil salvo à pasta"), self._t("Nenhum perfil salvo para aplicar."))
            return
        names = sorted(profiles, key=str.casefold)
        name, accepted = QInputDialog.getItem(
            self, self._t("Aplicar perfil salvo à pasta"),
            self._t("Selecione o perfil a aplicar:"), names, 0, False,
        )
        if not accepted or name not in profiles:
            return

        source_path = str(Path(source).expanduser().resolve())
        output_path = str(Path(output).expanduser().resolve())
        profile = dict(profiles[name])
        recursive = self.batch_include_subfolders.isChecked()
        file_mode = self._output_file_mode()
        self._pending_batch_context = {
            "profile": profile,
            "profile_name": name,
            "source_directory": source_path,
            "output_directory": output_path,
            "recursive": recursive,
            "file_mode": file_mode,
        }
        self._start_folder_batch(
            source_path,
            output_path,
            profile,
            recursive=recursive,
            file_mode=file_mode,
            resume=self.batch_resume_checkbox.isChecked(),
        )

    def _rerun_failed_batch_files(self) -> None:
        failed_sources = [item.source_path for item in self.batch_results if not item.success]
        if not failed_sources:
            QMessageBox.information(
                self, self._t("Reprocessar apenas falhas"),
                self._t("Não há PDFs com falha para reprocessar."),
            )
            return
        if (
            self._last_batch_profile is None
            or self._last_batch_source_directory is None
            or self._last_batch_output_directory is None
            or not Path(self._last_batch_source_directory).is_dir()
            or not Path(self._last_batch_output_directory).is_dir()
        ):
            QMessageBox.warning(
                self, self._t("Reprocessar apenas falhas"),
                self._t("A pasta original ou de saída não está disponível. Selecione as pastas e execute o lote novamente."),
            )
            return
        self._start_folder_batch(
            self._last_batch_source_directory,
            self._last_batch_output_directory,
            dict(self._last_batch_profile),
            recursive=self._last_batch_recursive,
            file_mode=self._last_batch_file_mode,
            resume=True,
            only_sources=failed_sources,
            initial_results=list(self.batch_results),
        )

    def _start_folder_batch(
        self,
        source: str,
        output: str,
        profile: dict[str, object],
        *,
        recursive: bool,
        file_mode: int,
        resume: bool,
        only_sources: list[str] | None = None,
        initial_results: list[BatchFileResult] | None = None,
    ) -> None:
        self._batch_control = BatchControl()
        worker = BatchFolderWorker(
            source, output, profile,
            recursive=recursive,
            file_mode=file_mode,
            resume=resume,
            control=self._batch_control,
            only_sources=only_sources,
            initial_results=initial_results,
        )
        self._worker = worker
        self._folder_batch_running = True
        self._pending_output_directory = Path(output).expanduser().resolve()
        self.open_directory_button.hide()
        self._set_status("Executando fluxo em lote…")
        self.progress.setRange(0, 0)
        self.progress.show()
        for tab_index in range(self.tabs.count()):
            self.tabs.setTabEnabled(tab_index, tab_index == self._folder_batch_tab_index)
        self.batch_run_button.setEnabled(False)
        self.batch_reprocess_failures_button.setEnabled(False)
        self.batch_choose_source_button.setEnabled(False)
        self.batch_choose_output_button.setEnabled(False)
        self.batch_include_subfolders.setEnabled(False)
        self.batch_resume_checkbox.setEnabled(False)
        self.batch_report_button.setEnabled(False)
        self.batch_history_combo.setEnabled(False)
        self.batch_history_load_button.setEnabled(False)
        self.batch_history_delete_button.setEnabled(False)
        self.batch_pause_button.setText(self._t("Pausar lote"))
        self.batch_pause_button.setEnabled(True)
        self.batch_cancel_button.setEnabled(True)
        worker.progress.connect(self._batch_progress_changed)
        worker.succeeded.connect(self._batch_operation_succeeded)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(self._operation_finished)
        worker.start()

    def _toggle_batch_pause(self) -> None:
        control = self._batch_control
        if control is None or not self._folder_batch_running:
            return
        if control.is_paused:
            control.resume()
            self.batch_pause_button.setText(self._t("Pausar lote"))
            self._set_status("Retomando lote…")
        else:
            control.pause()
            self.batch_pause_button.setText(self._t("Retomar lote"))
            self._set_status("Pausa solicitada; o PDF atual será concluído antes de pausar.")

    def _cancel_batch(self) -> None:
        control = self._batch_control
        if control is None or not self._folder_batch_running:
            return
        control.cancel()
        self.batch_pause_button.setEnabled(False)
        self.batch_cancel_button.setEnabled(False)
        self._set_status("Cancelamento solicitado; o PDF atual será concluído antes de parar.")

    def _batch_progress_changed(self, completed: int, total: int, filename: str) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(completed)
        control = self._batch_control
        if control is not None and control.is_paused:
            self._set_status("Lote pausado após {completed} de {total} arquivo(s).", completed=completed, total=total)
            return
        self._set_status("Processando arquivo {completed} de {total}: {name}", completed=completed, total=total, name=filename)

    def _render_batch_results(self, results: list[BatchFileResult]) -> None:
        self.batch_results = results
        self.batch_results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            source_item = QTableWidgetItem(Path(result.source_path).name)
            source_item.setToolTip(result.source_path)
            self.batch_results_table.setItem(row, 0, source_item)
            status_item = QTableWidgetItem(self._t("Sucesso" if result.success else "Falha"))
            status_item.setToolTip(result.message)
            self.batch_results_table.setItem(row, 1, status_item)
            self.batch_results_table.setItem(row, 2, QTableWidgetItem(self._t(result.message)))
            output_item = QTableWidgetItem(result.output_path)
            output_item.setToolTip(result.output_path)
            self.batch_results_table.setItem(row, 3, output_item)
        self.batch_report_button.setEnabled(bool(results))
        self.batch_reprocess_failures_button.setEnabled(
            any(not item.success for item in results) and self._last_batch_profile is not None
        )

    def _save_current_batch_history(self, results: list[BatchFileResult], *, cancelled: bool) -> None:
        if not self._last_batch_source_directory or not self._last_batch_output_directory:
            return
        report = save_batch_report(
            self._batch_history_directory,
            source_directory=self._last_batch_source_directory,
            output_directory=self._last_batch_output_directory,
            profile_name=self._last_batch_profile_name or "",
            profile=self._last_batch_profile or {},
            recursive=self._last_batch_recursive,
            file_mode=self._last_batch_file_mode,
            results=results,
            cancelled=cancelled,
        )
        self._batch_history[str(report["id"])] = report
        self._batch_history = {
            str(item["id"]): item for item in load_batch_history(self._batch_history_directory)
        }
        self._refresh_batch_history_combo(str(report["id"]))

    def _refresh_batch_history_combo(self, selected_id: str | None = None) -> None:
        if not hasattr(self, "batch_history_combo"):
            return
        records = sorted(
            self._batch_history.values(),
            key=lambda item: (float(item.get("created_timestamp", 0)), str(item.get("id", ""))),
            reverse=True,
        )
        combo = self.batch_history_combo
        combo.blockSignals(True)
        combo.clear()
        if not records:
            combo.addItem(self._t("Não há relatórios salvos."), None)
        else:
            for report in records:
                raw_results = report.get("results", [])
                results = raw_results if isinstance(raw_results, list) else []
                total = len(results)
                failures = sum(
                    1 for item in results
                    if isinstance(item, dict) and item.get("success") is False
                )
                created_at = str(report.get("created_at", "")).replace("T", " ")
                label = self._t(
                    "Relatório {date} — {total} PDF(s), {failed} falha(s) — perfil: {profile}"
                ).format(
                    date=created_at, total=total, failed=failures,
                    profile=str(report.get("profile_name", "")) or "—",
                )
                combo.addItem(label, str(report["id"]))
        if selected_id:
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)
        has_reports = bool(records) and not self._folder_batch_running
        combo.setEnabled(has_reports)
        self.batch_history_load_button.setEnabled(has_reports)
        self.batch_history_delete_button.setEnabled(has_reports)

    def _load_batch_history(self) -> None:
        self._batch_history = {
            str(report["id"]): report
            for report in load_batch_history(self._batch_history_directory)
        }
        self._refresh_batch_history_combo()
        if self._batch_history:
            newest = max(
                self._batch_history.values(),
                key=lambda item: (float(item.get("created_timestamp", 0)), str(item.get("id", ""))),
            )
            self._restore_batch_history_report(newest, activate_tab=False)
            self._set_status("Histórico de relatórios restaurado.")

    def _restore_batch_history_report(
        self, report: dict[str, object], *, activate_tab: bool
    ) -> None:
        raw_results = report.get("results", [])
        if not isinstance(raw_results, list):
            QMessageBox.warning(
                self, self._t("Histórico de relatórios"),
                self._t("Não foi possível ler o relatório histórico."),
            )
            return
        results: list[BatchFileResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            try:
                results.append(BatchFileResult(
                    source_path=str(item["source_path"]),
                    success=bool(item["success"]),
                    output_path=str(item["output_path"]),
                    message=str(item["message"]),
                ))
            except (KeyError, TypeError):
                continue

        source = str(report.get("source_directory", ""))
        output = str(report.get("output_directory", ""))
        raw_profile = report.get("profile", {})
        profile = dict(raw_profile) if isinstance(raw_profile, dict) else {}
        self._last_batch_profile = profile
        self._last_batch_profile_name = str(report.get("profile_name", ""))
        self._last_batch_source_directory = source
        self._last_batch_output_directory = output
        self._last_batch_recursive = bool(report.get("recursive", False))
        file_mode = report.get("file_mode", 0o600)
        self._last_batch_file_mode = file_mode if file_mode in (0o600, 0o644) else 0o600
        self.batch_source_directory.setText(source)
        self.batch_output_directory.setText(output)
        self.batch_include_subfolders.setChecked(self._last_batch_recursive)
        self.batch_resume_checkbox.setChecked(True)
        self._pending_output_directory = Path(output).expanduser() if output else None
        self._render_batch_results(results)
        self.open_directory_button.setVisible(
            self._pending_output_directory is not None and self._pending_output_directory.is_dir()
        )
        self._set_status("Relatório histórico carregado.")
        if activate_tab:
            self.tabs.setCurrentIndex(self._folder_batch_tab_index)

    def _load_selected_batch_history(self) -> None:
        report_id = self.batch_history_combo.currentData()
        if not isinstance(report_id, str) or report_id not in self._batch_history:
            QMessageBox.information(
                self, self._t("Histórico de relatórios"),
                self._t("Selecione um relatório para carregar."),
            )
            return
        self._restore_batch_history_report(self._batch_history[report_id], activate_tab=True)

    def _delete_selected_batch_history(self) -> None:
        report_id = self.batch_history_combo.currentData()
        if not isinstance(report_id, str):
            return
        try:
            deleted = delete_batch_report(self._batch_history_directory, report_id)
        except ValueError:
            deleted = False
        except OSError:
            QMessageBox.warning(
                self, self._t("Histórico de relatórios"),
                self._t("Não foi possível excluir o relatório histórico."),
            )
            return
        self._batch_history.pop(report_id, None)
        self._refresh_batch_history_combo()
        if deleted:
            self._set_status("Relatório removido do histórico.")

    def _batch_operation_succeeded(self, results: object, cancelled: bool = False) -> None:
        if not isinstance(results, list) or not all(isinstance(item, BatchFileResult) for item in results):
            self._operation_failed("Não foi possível gerar o relatório individual do lote.")
            return
        if self._pending_batch_context is not None:
            context = self._pending_batch_context
            self._last_batch_profile = dict(context["profile"])  # type: ignore[arg-type]
            self._last_batch_profile_name = str(context["profile_name"])
            self._last_batch_source_directory = str(context["source_directory"])
            self._last_batch_output_directory = str(context["output_directory"])
            self._last_batch_recursive = bool(context["recursive"])
            self._last_batch_file_mode = int(context["file_mode"])
            self._pending_batch_context = None
        self._render_batch_results(results)
        successes = sum(int(item.success) for item in results)
        failures = len(results) - successes
        if cancelled:
            self._set_status(
                "Lote cancelado com segurança após {completed} arquivo(s). O progresso foi preservado; execute novamente com a retomada ativada.",
                completed=len(results),
            )
        else:
            self._set_status(
                "Lote concluído: {success} sucesso(s), {failed} falha(s) de {total} PDF(s).",
                success=successes, failed=failures, total=len(results),
            )
        self.open_directory_button.setVisible(
            self._pending_output_directory is not None and self._pending_output_directory.is_dir()
        )
        try:
            self._save_current_batch_history(results, cancelled=cancelled)
        except (OSError, ValueError):
            QMessageBox.warning(
                self, self._t("Histórico de relatórios"),
                self._t("Não foi possível armazenar o relatório no histórico local."),
            )

    def _export_batch_report(self) -> None:
        if not self.batch_results:
            QMessageBox.information(self, self._t("Salvar relatório CSV"), self._t("Não há relatório para exportar."))
            return
        output = self._choose_output_file(
            "Salvar relatório CSV",
            "relatorio-pdf-hub.csv",
            ".csv",
            "Arquivos CSV (*.csv)",
        )
        if output is None:
            return
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8-sig",
                errors="replace",
                newline="",
                dir=str(output.parent),
                prefix=".batch-report-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                delimiter = ";" if self._language in {"pt", "es"} else ","
                writer = csv.writer(stream, delimiter=delimiter)
                writer.writerow([
                    self._t("Arquivo de origem"), self._t("Resultado"),
                    self._t("Detalhes"), self._t("Arquivo de saída"),
                ])
                for result in self.batch_results:
                    writer.writerow([
                        result.source_path, self._t("Sucesso" if result.success else "Falha"),
                        self._t(result.message), result.output_path,
                    ])
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(output)
            temporary = None
        except (OSError, ValueError):
            QMessageBox.warning(
                self,
                self._t("Salvar relatório CSV"),
                self._t("Não foi possível salvar o relatório CSV. Verifique a pasta e as permissões."),
            )
            return
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        self._set_status("Relatório salvo: {path}", path=str(output.resolve()))

    def _choose_pdf_to_images_source(self) -> None:
        path = self._choose_pdf("Escolher PDF para exportar imagens")
        if path:
            self.pdf_to_images_path.setText(path)

    def _choose_pdf_to_images_directory(self) -> None:
        path = self._choose_directory("Escolher pasta para salvar as imagens")
        if path:
            self.pdf_to_images_directory.setText(path)

    def _export_pdf_pages(self) -> None:
        source = self.pdf_to_images_path.text().strip()
        directory_text = self.pdf_to_images_directory.text().strip()
        if not source:
            QMessageBox.information(
                self, self._t("PDF para imagens"), self._t("Escolha o PDF de origem.")
            )
            return
        if not directory_text or not Path(directory_text).is_dir():
            QMessageBox.information(
                self, self._t("PDF para imagens"), self._t("Escolha uma pasta de saída existente.")
            )
            return

        output_directory = Path(directory_text)
        page_specification = self.pdf_to_images_pages.text().strip()
        image_format = str(self.pdf_to_images_format.currentData())
        dpi = self.pdf_to_images_dpi.value()
        quality = self.pdf_to_images_quality.value()
        password = self.pdf_to_images_password.text()
        self.pdf_to_images_password.clear()

        def task() -> str:
            images = export_pdf_pages_to_images(
                source,
                output_directory,
                image_format=image_format,
                dpi=dpi,
                quality=quality,
                pages=page_specification,
                password=password,
            )
            return self._t("Exportadas {count} página(s) para imagens em {directory}.").format(
                count=len(images), directory=output_directory
            )

        self._run_task(
            "Exportando páginas do PDF como imagens…",
            task,
            output_location=output_directory,
        )

    def _build_pdf_to_images_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Exportar páginas de PDF como imagens",
            "Exporte todas as páginas ou apenas os intervalos escolhidos como arquivos PNG/JPEG.",
        )
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.pdf_to_images_path = QLineEdit()
        self.pdf_to_images_path.setReadOnly(True)
        choose_pdf = QPushButton("Escolher PDF")
        choose_pdf.clicked.connect(self._choose_pdf_to_images_source)
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.pdf_to_images_path, 1)
        source_row.addWidget(choose_pdf)
        source_container = QWidget()
        source_container.setLayout(source_row)
        form.addRow("PDF de origem para exportar", source_container)

        self.pdf_to_images_pages = QLineEdit()
        self.pdf_to_images_pages.setPlaceholderText("Deixe vazio para exportar todas as páginas")
        form.addRow("Páginas (opcional)", self.pdf_to_images_pages)

        self.pdf_to_images_password = QLineEdit()
        self.pdf_to_images_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.pdf_to_images_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.pdf_to_images_password)

        self.pdf_to_images_format = QComboBox()
        self.pdf_to_images_format.addItem("PNG", "PNG")
        self.pdf_to_images_format.addItem("JPEG", "JPEG")
        form.addRow("Formato das imagens", self.pdf_to_images_format)

        self.pdf_to_images_dpi = QSpinBox()
        self.pdf_to_images_dpi.setRange(72, 600)
        self.pdf_to_images_dpi.setValue(150)
        self.pdf_to_images_dpi.setSuffix(" DPI")
        form.addRow("Resolução de saída", self.pdf_to_images_dpi)

        self.pdf_to_images_quality = QSpinBox()
        self.pdf_to_images_quality.setRange(1, 100)
        self.pdf_to_images_quality.setValue(90)
        self.pdf_to_images_quality.setSuffix(" / 100")
        self.pdf_to_images_quality.setEnabled(False)
        self.pdf_to_images_format.currentIndexChanged.connect(
            lambda _index: self.pdf_to_images_quality.setEnabled(
                self.pdf_to_images_format.currentData() == "JPEG"
            )
        )
        form.addRow("Qualidade JPEG", self.pdf_to_images_quality)

        self.pdf_to_images_directory = QLineEdit()
        self.pdf_to_images_directory.setReadOnly(True)
        choose_directory = QPushButton("Escolher pasta")
        choose_directory.clicked.connect(self._choose_pdf_to_images_directory)
        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.addWidget(self.pdf_to_images_directory, 1)
        output_row.addWidget(choose_directory)
        output_container = QWidget()
        output_container.setLayout(output_row)
        form.addRow("Pasta para salvar as imagens", output_container)

        layout.addLayout(form)
        layout.addStretch(1)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        export_button = QPushButton("Exportar páginas")
        export_button.setObjectName("primaryButton")
        export_button.clicked.connect(self._export_pdf_pages)
        button_row.addWidget(export_button)
        layout.addLayout(button_row)
        return page

    def _build_convert_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Converter e redimensionar imagens",
            "Converta várias imagens de uma só vez. O redimensionamento mantém a proporção e nunca amplia imagens pequenas.",
        )
        self.convert_list = self._new_list(extended=True)
        layout.addWidget(self.convert_list, 1)

        file_row = QHBoxLayout()
        file_row.setContentsMargins(0, 0, 0, 0)
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
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
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
        out_row.setContentsMargins(0, 0, 0, 0)
        out_row.addWidget(self.convert_directory, 1)
        out_row.addWidget(browse_dir)
        out_container = QWidget()
        out_container.setLayout(out_row)
        form.addRow("Pasta de saída", out_container)

        layout.addLayout(form)
        multi_frame_note = QLabel(
            "Para GIF/TIFF/WebP com vários quadros, a conversão usa somente o primeiro quadro."
        )
        multi_frame_note.setObjectName("muted")
        multi_frame_note.setWordWrap(True)
        layout.addWidget(multi_frame_note)
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
        if added:
            self._set_status("{added} imagem(ns) adicionada(s).", added=added)
        else:
            self._set_status("Nenhuma imagem nova adicionada.")

    def _select_convert_directory(self) -> None:
        path = self._choose_directory("Escolher pasta para salvar as imagens")
        if path:
            self.convert_directory.setText(path)

    def _convert_images(self) -> None:
        sources = self._all_paths(self.convert_list)
        directory_text = self.convert_directory.text().strip()
        if not sources:
            QMessageBox.information(self, self._t("Converter imagens"), self._t("Adicione pelo menos uma imagem."))
            return
        if not directory_text or not Path(directory_text).is_dir():
            QMessageBox.information(self, self._t("Pasta de saída"), self._t("Escolha uma pasta de saída existente."))
            return

        image_format = self.convert_format.currentText()
        extension = FORMAT_EXTENSIONS[image_format]
        max_width = self.convert_width.value() or None
        max_height = self.convert_height.value() or None
        quality = self.convert_quality.value()
        file_mode = self._output_file_mode()
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
                            file_mode=file_mode,
                        )
                    )
                except Exception as error:
                    failures.append(f"{source.name}: {self._t(friendly_error_message(error))}")

            summary = self._t("{count} imagem(ns) convertida(s) em {directory}.").format(
                count=len(completed), directory=directory
            )
            if failures:
                summary += self._t(" Falhas: {count}.").format(count=len(failures)) + " " + " | ".join(failures[:3])
            if not completed:
                raise ValueError(summary)
            return summary

        self._run_task("Convertendo imagens…", task, output_location=directory)


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("PDFHub")
    application.setWindowIcon(create_app_icon())
    application.setFont(QFont("Segoe UI", 10))
    window = DocumentToolsWindow()
    window.showMaximized()
    return application.exec()
