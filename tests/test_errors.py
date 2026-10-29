from __future__ import annotations

import errno
import types

from PIL import Image
from pypdf.errors import DependencyError, PdfReadError, PdfStreamError

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



def test_truncated_image_message_is_actionable(tmp_path) -> None:
    source = tmp_path / "good.png"
    Image.effect_noise((100, 100), 70).save(source)
    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(source.read_bytes()[:100])
    try:
        with Image.open(truncated) as image:
            image.load()
    except Exception as error:
        assert "A imagem não pôde ser processada" in friendly_error_message(error)
    else:
        raise AssertionError("A imagem truncada deveria falhar")


def test_memory_error_message() -> None:
    assert "Memória insuficiente" in friendly_error_message(MemoryError())


def test_disk_full_message() -> None:
    assert "Não há espaço livre suficiente" in friendly_error_message(OSError(errno.ENOSPC, "full"))


def test_is_a_directory_message() -> None:
    assert "caminho escolhido não serve" in friendly_error_message(IsADirectoryError(21, "directory"))


def test_library_value_errors_are_not_echoed_but_app_validation_is() -> None:
    fake_pil = types.ModuleType("PIL.fake_encoder")
    exec("def reject():\n    raise ValueError('encoding error 5: internal detail')", fake_pil.__dict__)
    try:
        fake_pil.reject()
    except ValueError as error:
        assert "encoding error 5" not in friendly_error_message(error)

    app_module = types.ModuleType("document_tools.pdf_ops")
    exec("def validate():\n    raise ValueError('A resolução precisa ficar entre 72 e 600 DPI.')", app_module.__dict__)
    try:
        app_module.validate()
    except ValueError as error:
        assert friendly_error_message(error) == "A resolução precisa ficar entre 72 e 600 DPI."


def test_dependency_error_points_to_installation() -> None:
    message = friendly_error_message(DependencyError("cryptography>=3 is required for AES"))
    assert "componente de criptografia" in message
    assert "Reinstale" in message
