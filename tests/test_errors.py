from __future__ import annotations

from pypdf.errors import PdfReadError, PdfStreamError

from document_tools.errors import friendly_error_message


def test_pdf_read_errors_are_not_swallowed_by_generic_pypdf_branch() -> None:
    for error in (PdfReadError("internal parser detail"), PdfStreamError("internal stream detail")):
        message = friendly_error_message(error)
        assert "danificado ou protegido por senha" in message
        assert "internal parser detail" not in message
        assert "internal stream detail" not in message


def test_unexpected_errors_do_not_expose_internal_details() -> None:
    message = friendly_error_message(RuntimeError("secret internal library detail"))
    assert message == "Não foi possível concluir a operação. Os detalhes internos foram ocultados."


def test_existing_output_error_does_not_include_file_path() -> None:
    message = friendly_error_message(FileExistsError("/private/user/document.pdf"))
    assert message == "Um arquivo de destino já existe. Escolha outra pasta ou nome."
    assert "/private/user" not in message
