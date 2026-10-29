"""User-friendly errors for background document processing."""
from __future__ import annotations

import errno
from pathlib import Path

_THIRD_PARTY_ROOTS = {"PIL", "pypdf", "reportlab", "PySide6", "cryptography"}


def _origin_root(error: BaseException) -> str:
    """Return the package of the innermost Python frame that raised the error."""
    traceback = error.__traceback__
    module = ""
    while traceback is not None:
        module = str(traceback.tb_frame.f_globals.get("__name__", ""))
        traceback = traceback.tb_next
    return module.split(".", 1)[0]


def friendly_error_message(error: Exception) -> str:
    """Return a safe and actionable Portuguese message for expected failures."""
    if isinstance(error, UnicodeError):
        return (
            "O nome do arquivo ou o texto contém caracteres que não podem ser "
            "representados com segurança. Renomeie o arquivo ou ajuste o texto e tente novamente."
        )
    if isinstance(error, PermissionError):
        return "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas."
    if isinstance(error, FileNotFoundError):
        filename = getattr(error, "filename", None)
        name = Path(str(filename)).name if filename else ""
        if name:
            return f"Arquivo não encontrado: {name}. Confira o caminho e tente novamente."
        return "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente."
    if isinstance(error, FileExistsError):
        detail = str(error)
        if detail.startswith("A pasta já contém '"):
            return detail
        return "Um arquivo de destino já existe. Escolha outra pasta ou nome."
    if isinstance(error, (IsADirectoryError, NotADirectoryError)):
        return "O caminho escolhido não serve para esta operação (foi informado um arquivo no lugar de pasta, ou o contrário)."
    if isinstance(error, MemoryError):
        return "Memória insuficiente para concluir a operação. Feche outros programas ou use uma imagem/PDF de menor resolução."
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return "Não há espaço livre suficiente no disco de destino."

    error_type = error.__class__.__name__
    origin = _origin_root(error)
    module_name = error.__class__.__module__
    if error_type in {"UnidentifiedImageError", "DecompressionBombError", "DecompressionBombWarning"}:
        return "A imagem é inválida, muito grande para processar com segurança ou usa um formato não suportado."
    if error_type == "DependencyError":
        return "Falta um componente de criptografia nesta instalação. Reinstale o aplicativo usando o pacote oficial completo."
    if error_type in {"WrongPasswordError", "FileNotDecryptedError"}:
        return "Não foi possível interpretar o PDF. Ele pode estar danificado ou protegido por senha."
    if module_name.startswith("pypdf") or origin == "pypdf":
        return "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar."
    if module_name.startswith("PIL") or origin == "PIL":
        return "A imagem não pôde ser processada. Verifique se o arquivo está íntegro e usa um formato compatível."
    if isinstance(error, InterruptedError):
        return "A operação foi cancelada."
    if isinstance(error, ValueError):
        # App validations originate from document_tools; third-party ValueErrors
        # are implementation details and should not leak codec/parser text.
        if origin == "document_tools":
            return str(error)
        return "Não foi possível validar os dados informados. Confira os arquivos e as opções e tente novamente."
    if error_type == "RuntimeError" and str(error).startswith("Não foi possível concluir"):
        return str(error)
    return "Não foi possível concluir a operação. Os detalhes internos foram ocultados."
