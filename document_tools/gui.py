"""PySide6 desktop interface for the local PDF and image toolkit."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QThread, Signal, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QPixmap
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
    optimize_pdf,
    pdf_page_count,
    reorder_pdf_pages,
    stamp_pdf,
    rotate_pdf,
    split_pdf,
    pdf_requires_user_password,
)


APP_NAME = "PDF Hub"
IMAGE_FILTER = "Imagens (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.gif)"
PDF_FILTER = "Documentos PDF (*.pdf)"
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
        "Unir PDFs": "Unir PDFs",
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
        "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente.": "No se encontró el archivo o la carpeta. Comprueba la ruta.",
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
    }
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
        self.settings = QSettings("PDFHub", "PDF Hub")
        self._language = "pt"
        self._original_ui_texts: dict[QWidget, str] = {}
        self._original_tooltips: dict[QWidget, str] = {}
        self._original_placeholders: dict[QLineEdit, str] = {}
        self._original_combo_items: dict[QComboBox, list[str]] = {}
        self._original_tab_titles: list[str] = []
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

        brand_mark = QLabel("H")
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

        local_badge = QLabel("●  PDF HUB • PROCESSAMENTO LOCAL")
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

        permission_row = QHBoxLayout()
        language_label = QLabel("Idioma / Language")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Português (Brasil)", "pt")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Español", "es")
        permission_label = QLabel("Permissões de saída (Linux/macOS)")
        permission_label.setObjectName("muted")
        permission_label.setToolTip("No Windows, o sistema de permissões é gerenciado pelo próprio sistema operacional.")
        self.output_permissions = QComboBox()
        self.output_permissions.addItem("Somente usuário (0600)", 0o600)
        self.output_permissions.addItem("Compartilhado (0644)", 0o644)
        try:
            saved_mode = int(self.settings.value("output_file_mode", 0o600))
        except (TypeError, ValueError):
            saved_mode = 0o600
        saved_index = self.output_permissions.findData(saved_mode)
        self.output_permissions.setCurrentIndex(saved_index if saved_index >= 0 else 0)
        self.output_permissions.setToolTip("0600: somente o usuário atual. 0644: outros usuários do sistema podem ler os arquivos.")
        self.output_permissions.currentIndexChanged.connect(self._save_output_permissions)
        permission_row.addWidget(permission_label)
        permission_row.addWidget(self.output_permissions)
        permission_row.addSpacing(16)
        permission_row.addWidget(language_label)
        permission_row.addWidget(self.language_combo)
        permission_row.addStretch(1)
        central_layout.addLayout(permission_row)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_image_pdf_tab(), "  Imagens para PDF  ")
        self.tabs.addTab(self._build_merge_tab(), "  Unir PDFs  ")
        self.tabs.addTab(self._build_extract_tab(), "  Extrair páginas  ")
        self.tabs.addTab(self._build_rotate_tab(), "  Girar páginas  ")
        self.tabs.addTab(self._build_split_tab(), "  Dividir PDF  ")
        self.tabs.addTab(self._build_reorder_tab(), "  Reordenar páginas  ")
        self.tabs.addTab(self._build_stamp_tab(), "  Marca d'água e numeração  ")
        self.tabs.addTab(self._build_optimize_tab(), "  Otimizar PDF  ")
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
        self._capture_ui_texts()
        saved_language = str(self.settings.value("language", "pt"))
        language_index = self.language_combo.findData(saved_language)
        self.language_combo.setCurrentIndex(language_index if language_index >= 0 else 0)
        self.language_combo.currentIndexChanged.connect(self._change_language)
        self._apply_language(str(self.language_combo.currentData()))

    def _t(self, text: str) -> str:
        """Translate a Brazilian Portuguese UI string to the active interface language."""
        if self._language == "pt":
            return text
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
        # Allow switching between non-Portuguese languages when a status is already translated.
        for language in ("en", "es"):
            reverse = {translated: source for source, translated in TRANSLATIONS[language].items()}
            if core in reverse:
                source = reverse[core]
                return leading + mapping.get(source, source) + trailing
        # Translate dynamic operation summaries without altering file paths or sizes.
        dynamic_prefixes = {
            "en": [
                ("PDF criado: ", "PDF created: "),
                ("PDFs unidos: ", "PDFs merged: "),
                ("Páginas extraídas: ", "Pages extracted: "),
                ("PDF rotacionado: ", "PDF rotated: "),
            ],
            "es": [
                ("PDF criado: ", "PDF creado: "),
                ("PDFs unidos: ", "PDFs unidos: "),
                ("Páginas extraídas: ", "Páginas extraídas: "),
                ("PDF rotacionado: ", "PDF rotado: "),
            ],
        }
        for source_prefix, translated_prefix in dynamic_prefixes.get(self._language, []):
            if core.startswith(source_prefix):
                return leading + translated_prefix + core[len(source_prefix):] + trailing
        for source, translated in mapping.items():
            if "{message}" in source and core.startswith(source.split("{message}")[0]):
                prefix = source.split("{message}")[0]
                return leading + translated.split("{message}")[0] + core[len(prefix):] + trailing
        return text

    def _capture_ui_texts(self) -> None:
        for widget in self.findChildren(QWidget):
            if widget is self.language_combo:
                continue
            if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
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
                if isinstance(widget, (QLabel, QPushButton, QCheckBox)):
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
        # Refresh the current status text too, so switching language does not leave stale Portuguese text.
        if self.status_label.text():
            self.status_label.setText(self._t(self.status_label.text()))

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
        paths, _ = QFileDialog.getOpenFileNames(self, self._t(title), "", file_filter)
        return paths

    def _choose_pdf(self, title: str = "Escolher PDF") -> str | None:
        path, _ = QFileDialog.getOpenFileName(self, self._t(title), "", PDF_FILTER)
        return path or None

    def _choose_output_pdf(
        self,
        suggested_name: str,
        *,
        source_paths: tuple[str, ...] | list[str] = (),
    ) -> str | None:
        dialog = QFileDialog(self, self._t("Salvar PDF resultante"), suggested_name, PDF_FILTER)
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
                self.status_label.setText(self._t("Operação cancelada. O arquivo existente foi preservado."))
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
        self.status_label.setText(self._t(description))
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
        self.status_label.setText(self._t(message))
        self.open_directory_button.setVisible(
            self._pending_output_directory is not None
            and self._pending_output_directory.is_dir()
        )

    def _operation_failed(self, message: str) -> None:
        self.open_directory_button.hide()
        self.status_label.setText(self._t(f"Não foi possível concluir a operação: {message}"))
        QMessageBox.warning(self, self._t("Operação não concluída"), self._t(message))

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
            self.status_label.setText(self._t("A pasta de saída não está disponível."))
            self.open_directory_button.hide()
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            QMessageBox.information(self, APP_NAME, self._t("Abra esta pasta manualmente:\n{path}").format(path=directory))

    def closeEvent(self, event: QCloseEvent) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
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

        self.image_all_frames = QCheckBox("Incluir todas as páginas/quadros de imagens multipágina ou animadas")
        self.image_all_frames.setChecked(True)
        self.image_all_frames.setToolTip("Quando desmarcado, usa somente a primeira página ou o primeiro quadro de cada arquivo.")
        layout.addWidget(self.image_all_frames)

        bottom = QHBoxLayout()
        hint = QLabel("Formatos: JPG, PNG, BMP, WEBP, TIFF e GIF.")
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
        status = self._t("{added} imagem(ns) adicionada(s).").format(added=added) if added else self._t("Nenhuma imagem nova adicionada.")
        self.status_label.setText(status)

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
        status = self._t("{added} PDF(s) adicionado(s).").format(added=added) if added else self._t("Nenhum PDF novo adicionado.")
        self.status_label.setText(status)

    def _merge_pdfs(self) -> None:
        sources = self._all_paths(self.pdf_list)
        if len(sources) < 2:
            QMessageBox.information(self, self._t("Unir PDFs"), self._t("Adicione pelo menos dois PDFs."))
            return
        output = self._require_output_pdf("documentos-unidos.pdf", source_paths=sources)
        if not output:
            return
        passwords: list[str | None] = [None] * len(sources)
        try:
            for index, source in enumerate(sources):
                if pdf_requires_user_password(source):
                    password, accepted = QInputDialog.getText(
                        self,
                        "Senha do PDF",
                        f"O arquivo '{Path(source).name}' está protegido. Digite a senha:",
                        QLineEdit.EchoMode.Password,
                    )
                    if not accepted:
                        return
                    if not password:
                        QMessageBox.information(self, self._t("Senha necessária"), self._t("Informe uma senha não vazia para continuar."))
                        return
                    passwords[index] = password
        except Exception as error:
            QMessageBox.warning(self, self._t("Não foi possível verificar o PDF"), self._t(str(error)))
            return
        file_mode = self._output_file_mode()
        self._run_task(
            "Unindo os PDFs…",
            lambda: f"PDFs unidos: {merge_pdfs(sources, output, passwords=passwords, file_mode=file_mode)}",
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
        self.split_password = QLineEdit()
        self.split_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.split_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.split_password)
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
            QMessageBox.information(self, self._t("Dividir PDF"), self._t("Escolha o PDF e uma pasta de saída."))
            return
        password = self.split_password.text() or None
        self.split_password.clear()
        file_mode = self._output_file_mode()
        self._run_task(
            "Dividindo PDF em arquivos de página única…",
            lambda: f"{len(split_pdf(source, directory, password=password, file_mode=file_mode))} páginas salvas em: {directory}",
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
            count = pdf_page_count(path, password=password or None)
        except Exception as error:
            QMessageBox.warning(self, self._t("Não foi possível abrir o PDF"), self._t(str(error)))
            return
        self.reorder_path.setText(path)
        self.reorder_password = password or None
        if self.reorder_document is not None:
            self.reorder_document.close()
        self.reorder_document = QPdfDocument(self)
        if password:
            self.reorder_document.setPassword(password)
        self.reorder_document.load(path)
        if self.reorder_document.pageCount() != count:
            self.reorder_document.close()
            self.reorder_document = None
        self.reorder_list.clear()
        for page_number in range(1, count + 1):
            item = QListWidgetItem(self._t("Página {number}").format(number=page_number))
            item.setData(Qt.ItemDataRole.UserRole, page_number)
            self.reorder_list.addItem(item)
        if count:
            self.reorder_list.setCurrentRow(0)
        self.status_label.setText(self._t("{count} páginas carregadas. Arraste para reorganizar.").format(count=count))

    def _preview_reorder_page(self, row: int) -> None:
        document = self.reorder_document
        if document is None or row < 0 or row >= document.pageCount():
            self.reorder_preview.setPixmap(QPixmap())
            self.reorder_preview.setText(self._t("Selecione uma página para visualizar."))
            return
        try:
            point_size = document.pagePointSize(row)
            if point_size.width() <= 0 or point_size.height() <= 0:
                raise ValueError("Page dimensions are not available")
            scale = min(320 / point_size.width(), 440 / point_size.height())
            render_size = QSize(
                max(1, round(point_size.width() * scale)),
                max(1, round(point_size.height() * scale)),
            )
            page_image = document.render(row, render_size)
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
                self._t("Página {number}").format(number=row + 1)
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
            "Visualize e arraste as páginas para definir a ordem final. Todas as páginas devem permanecer na lista.",
            "Escolha um PDF para reorganizar suas páginas.",
        )
        path_row = QHBoxLayout()
        self.reorder_path = QLineEdit()
        self.reorder_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_reorder_pdf)
        path_row.addWidget(self.reorder_path, 1)
        path_row.addWidget(browse)
        path_container = QWidget()
        path_container.setLayout(path_row)
        layout.addWidget(path_container)
        self.reorder_list = self._new_list()
        self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.reorder_list.currentRowChanged.connect(self._preview_reorder_page)
        preview_row = QHBoxLayout()
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
        self.reorder_password = None
        note = QLabel("Arraste uma página para cima ou para baixo. A numeração indica a página original.")
        note.setObjectName("muted")
        actions.addWidget(note, 1)
        save = QPushButton("Salvar PDF reordenado")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._reorder_pdf)
        actions.addWidget(save)
        layout.addLayout(actions)
        return page

    def _build_stamp_tab(self) -> QWidget:
        page, layout = self._new_page(
            "Adicionar uma marca d'água de texto, numeração, ou ambos. O conteúdo original não é rasterizado.",
            "Escolha o documento e defina o texto, a posição e a opacidade da marca d'água.",
        )
        form = QFormLayout()
        self.stamp_path = QLineEdit()
        self.stamp_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_stamp_pdf)
        file_row = QHBoxLayout()
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
            "Escolha entre preservar toda a qualidade (sem perdas) ou reduzir mais o tamanho recomprimindo imagens.",
            "A otimização sem perdas comprime streams e remove objetos redundantes; a equilibrada também recomprime imagens opacas.",
        )
        form = QFormLayout()
        self.optimize_path = QLineEdit()
        self.optimize_path.setReadOnly(True)
        browse = QPushButton("Escolher PDF")
        browse.clicked.connect(self._select_optimize_pdf)
        file_row = QHBoxLayout()
        file_row.addWidget(self.optimize_path, 1)
        file_row.addWidget(browse)
        file_container = QWidget()
        file_container.setLayout(file_row)
        form.addRow("PDF de origem para otimizar", file_container)
        self.optimize_mode = QComboBox()
        self.optimize_mode.addItem("Sem perdas (mais conservador)", "lossless")
        self.optimize_mode.addItem("Equilibrada (recomprimir imagens)", "balanced")
        form.addRow("Modo de otimização", self.optimize_mode)
        self.optimize_quality = QSpinBox()
        self.optimize_quality.setRange(50, 95)
        self.optimize_quality.setValue(82)
        self.optimize_quality.setSuffix(" / 100")
        form.addRow("Qualidade das imagens", self.optimize_quality)
        self.optimize_password = QLineEdit()
        self.optimize_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.optimize_password.setPlaceholderText("Opcional; não é armazenada")
        form.addRow("Senha do PDF (opcional)", self.optimize_password)
        warning = QLabel("Esta opção recomprime imagens sem transparência; a qualidade visual pode diminuir.")
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
            reduction = max(0, round((old_size - new_size) / old_size * 100)) if old_size else 0
            template = "Otimização equilibrada" if mode == "balanced" else "Otimização sem perdas"
            return self._t("PDF otimizado: {old} → {new} ({percent}% de redução)").format(
                old=self._format_size(old_size),
                new=self._format_size(new_size),
                percent=reduction,
            ) + " — " + self._t(template)

        self._run_task(self._t("Reduzir tamanho do PDF"), task, output_location=output)

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
        status = self._t("{added} imagem(ns) adicionada(s).").format(added=added) if added else self._t("Nenhuma imagem nova adicionada.")
        self.status_label.setText(status)

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
    application.setOrganizationName("PDFHub")
    application.setFont(QFont("Segoe UI", 10))
    window = DocumentToolsWindow()
    window.show()
    return application.exec()
