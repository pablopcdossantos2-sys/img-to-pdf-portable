from __future__ import annotations

from pypdf.errors import PdfReadError, PdfStreamError

from document_tools.errors import friendly_error_message


def test_pdf_parser_errors_use_the_safe_structural_error_message() -> None:
    for error in (PdfReadError("internal parser detail"), PdfStreamError("internal stream detail")):
        message = friendly_error_message(error)
        assert "estrutura não suportada ou está danificado" in message
        assert "internal parser detail" not in message
        assert "internal stream detail" not in message


def test_unexpected_errors_do_not_expose_internal_details() -> None:
    message = friendly_error_message(RuntimeError("secret internal library detail"))
    assert message == "Não foi possível concluir a operação. Os detalhes internos foram ocultados."


def test_split_conflict_message_keeps_file_name() -> None:
    error = FileExistsError(
        "A pasta já contém 'doc-pagina-001.pdf'. Escolha outra pasta ou remova os arquivos conflitantes."
    )
    message = friendly_error_message(error)
    assert "doc-pagina-001.pdf" in message
    assert "Escolha outra pasta" in message


def test_existing_output_error_does_not_include_file_path() -> None:
    message = friendly_error_message(FileExistsError("/private/user/document.pdf"))
    assert message == "Um arquivo de destino já existe. Escolha outra pasta ou nome."
    assert "/private/user" not in message


def test_unicode_error_is_friendly() -> None:
    error = UnicodeEncodeError("utf-8", chr(0xDCFF), 0, 1, "surrogates not allowed")
    message = friendly_error_message(error)
    assert "Renomeie o arquivo" in message
    assert "surrogates not allowed" not in message


def test_memory_and_disk_full_errors_are_actionable() -> None:
    memory = friendly_error_message(MemoryError())
    disk = friendly_error_message(OSError(28, "No space left on device"))
    assert "memória" in memory.lower()
    assert "espaço" in disk.lower()


def test_is_a_directory_error_is_actionable() -> None:
    assert "pasta" in friendly_error_message(IsADirectoryError()).lower()


def test_dependency_error_is_not_described_as_a_damaged_pdf() -> None:
    error = type("DependencyError", (Exception,), {"__module__": "pypdf.errors"})(
        "cryptography is missing"
    )
    message = friendly_error_message(error)
    assert "dependência" in message.lower()
    assert "danificado" not in message.lower()


def test_library_value_error_details_are_not_echoed() -> None:
    error = ValueError("Image size exceeds WebP limit")
    try:
        raise error
    except ValueError as caught:
        message = friendly_error_message(caught)
    assert "Image size exceeds" not in message
    assert "detalhes internos" in message


def test_pillow_origin_oserror_is_described_as_an_image_problem() -> None:
    namespace = {"__name__": "PIL.ImageFile"}
    code = compile(
        "def fail():\n    raise OSError('image file is truncated')\n",
        "/usr/local/lib/python/site-packages/PIL/ImageFile.py",
        "exec",
    )
    exec(code, namespace)
    try:
        namespace["fail"]()
    except OSError as error:
        message = friendly_error_message(error)
    assert "imagem" in message.lower()
    assert "truncated" not in message.lower()


def test_not_a_directory_error_is_actionable() -> None:
    message = friendly_error_message(NotADirectoryError())
    assert "caminho" in message.lower() or "pasta" in message.lower()
