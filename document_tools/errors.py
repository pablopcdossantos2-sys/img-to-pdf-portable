"""User-friendly errors for background document processing."""
from __future__ import annotations


def friendly_error_message(error: Exception) -> str:
    """Return a localized-safe message without exposing arbitrary library details."""
    if isinstance(error, PermissionError):
        return "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas."
    if isinstance(error, FileNotFoundError):
        return "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente."
    if isinstance(error, FileExistsError):
        return "Um arquivo de destino já existe. Escolha outra pasta ou nome."
    error_type = error.__class__.__name__
    module_name = error.__class__.__module__
    if error_type in {"UnidentifiedImageError", "DecompressionBombError"}:
        return "A imagem é inválida, muito grande para processar com segurança ou usa um formato não suportado."
    if error_type in {"WrongPasswordError", "FileNotDecryptedError", "PdfReadError", "PdfStreamError"}:
        return "Não foi possível interpretar o PDF. Ele pode estar danificado ou protegido por senha."
    if module_name.startswith("pypdf"):
        return "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar."
    if module_name.startswith("PIL"):
        return "A imagem não pôde ser processada. Verifique se o arquivo está íntegro e usa um formato compatível."
    if module_name.startswith("PySide6.QtPdf"):
        return "Não foi possível renderizar o PDF. Ele pode usar recursos não suportados ou estar danificado."
    # ValueError is used by pdf_ops for actionable, user-facing validation messages.
    # Other unexpected exceptions are deliberately not echoed to the interface.
    if isinstance(error, ValueError):
        return str(error)
    if error_type == "RuntimeError" and str(error).startswith("Não foi possível concluir"):
        return str(error)
    return "Não foi possível concluir a operação. Os detalhes internos foram ocultados."
