"""User-friendly errors for background document processing."""
from __future__ import annotations

import errno
import traceback


def _origin_root(error: Exception) -> str | None:
    """Find the innermost third-party package represented in the traceback."""
    root = None
    node = error.__traceback__
    while node is not None:
        module = str(node.tb_frame.f_globals.get("__name__", ""))
        for package in ("PIL", "pypdf", "reportlab", "PySide6", "cryptography"):
            if module == package or module.startswith(package + "."):
                root = package
        node = node.tb_next
    return root


def friendly_error_message(error: Exception) -> str:
    """Return a localized-safe message without exposing arbitrary library details."""
    if isinstance(error, UnicodeError):
        return "O nome do arquivo contém caracteres que não podem ser representados com segurança. Renomeie o arquivo e tente novamente."
    if isinstance(error, PermissionError):
        return "Não foi possível acessar ou salvar o arquivo. Confira as permissões e feche o documento em outros programas."
    if isinstance(error, FileNotFoundError):
        return "O arquivo ou a pasta não foi encontrado. Confira o caminho e tente novamente."
    if isinstance(error, FileExistsError):
        detail = str(error)
        if detail.startswith("A pasta já contém '"):
            return detail
        return "Um arquivo de destino já existe. Escolha outra pasta ou nome."
    error_type = error.__class__.__name__
    module_name = error.__class__.__module__
    origin = _origin_root(error)
    if isinstance(error, MemoryError):
        return "Não há memória suficiente para concluir a operação. Feche outros aplicativos ou tente uma imagem menor."
    if isinstance(error, (IsADirectoryError, NotADirectoryError)):
        return "O caminho selecionado não corresponde a um arquivo ou pasta válido."
    if isinstance(error, OSError) and error.errno in {errno.ENOSPC, getattr(errno, "EDQUOT", -1)}:
        return "Não há espaço disponível no disco para salvar o resultado. Libere espaço e tente novamente."
    if error_type == "DependencyError" and (module_name.startswith("pypdf") or origin == "pypdf"):
        return "Falta uma dependência necessária para abrir este PDF criptografado. Reinstale o PDF Hub usando o pacote oficial."
    if origin == "PIL" or error_type in {"UnidentifiedImageError", "DecompressionBombError"}:
        return "A imagem não pôde ser processada. Verifique se o arquivo está íntegro, não excede os limites de segurança e usa um formato compatível."
    if error_type in {"WrongPasswordError", "FileNotDecryptedError"} or origin == "pypdf":
        return "O PDF contém uma estrutura não suportada ou está danificado. Tente salvar uma nova cópia do PDF antes de processar."
    if origin == "reportlab":
        return "Não foi possível gerar o PDF com o conteúdo informado. Verifique os textos, fontes e caracteres usados."
    if origin in {"PySide6", "cryptography"}:
        return "Não foi possível processar o documento com os componentes instalados. Reinstale o PDF Hub usando o pacote oficial."
    if isinstance(error, OSError):
        return "Não foi possível ler ou gravar o arquivo. Verifique se ele está íntegro, se o destino é válido e se há espaço em disco."
    # Only echo validation messages raised from the app; arbitrary library details
    # are mapped by the package that raised them.
    if isinstance(error, ValueError):
        frames = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
        last_filename = frames[-1].filename.replace("\\", "/") if frames else ""
        detail = str(error).casefold()
        library_detail = any(
            phrase in detail
            for phrase in (
                "image size exceeds", "maximum supported image dimension",
                "cannot write mode", "broken data stream", "cannot identify image file",
                "cannot determine image file", "not enough image data",
                "unknown filter", "bad transparency mask",
            )
        )
        if origin is None and not library_detail and (
            "/document_tools/" in last_filename or "/tests/" in last_filename
        ):
            return str(error)
    if error_type == "RuntimeError" and str(error) == "A exportação de páginas foi cancelada.":
        return str(error)
    if error_type == "RuntimeError" and str(error).startswith("Não foi possível concluir"):
        return str(error)
    return "Não foi possível concluir a operação. Os detalhes internos foram ocultados."
