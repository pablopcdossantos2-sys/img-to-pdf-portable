"""Versioned, validated profiles for PDF Hub's reusable workflows."""
from __future__ import annotations

CURRENT_PROFILE_SCHEMA_VERSION = 2
DEFAULT_OUTPUT_SUFFIX = "-processado"
PROFILE_FIELDS_V1 = frozenset({
    "rotate_enabled", "rotate_angle", "rotate_ranges",
    "stamp_enabled", "stamp_text", "page_numbering", "stamp_ranges",
    "optimize_enabled", "optimize_mode", "quality",
})
PROFILE_FIELDS_V2 = PROFILE_FIELDS_V1 | {"output_suffix"}


def _validate_suffix(value: object) -> str:
    if (
        not isinstance(value, str) or len(value) > 40 or value != value.strip()
        or any(ord(char) < 32 for char in value)
        or any(char in value for char in '<>:"/\\|?*')
        or value.endswith((".", " "))
    ):
        raise ValueError("O sufixo de saída contém caracteres inválidos ou é longo demais.")
    return value


def _validate_page_range_syntax(specification: str) -> None:
    """Validate page-range syntax without expanding ranges or assuming a PDF length."""
    if not specification.strip():
        return
    intervals: list[tuple[int, int | None, str]] = []
    for raw_segment in specification.split(","):
        segment = raw_segment.strip()
        if not segment:
            raise ValueError("Há um item vazio na lista de páginas.")
        pieces = [part.strip() for part in segment.split("-")]
        if len(pieces) == 1 and pieces[0].isdecimal():
            start = end = int(pieces[0])
        elif (
            len(pieces) == 2
            and pieces[0].isdecimal()
            and (pieces[1].isdecimal() or pieces[1] == "")
        ):
            start = int(pieces[0])
            end = int(pieces[1]) if pieces[1] else None
        else:
            raise ValueError(f"Intervalo de páginas inválido: '{segment}'.")
        if start < 1 or (end is not None and (end < start or end < 1)):
            raise ValueError(f"Intervalo de páginas inválido: '{segment}'.")
        for previous_start, previous_end, _previous_segment in intervals:
            overlap_start = max(start, previous_start)
            current_end = end if end is not None else float("inf")
            prior_end = previous_end if previous_end is not None else float("inf")
            if overlap_start <= min(current_end, prior_end):
                raise ValueError(f"A página {overlap_start} foi informada mais de uma vez.")
        intervals.append((start, end, segment))


def validate_profile_options(profile: object, schema_version: int) -> dict[str, object]:
    """Validate one schema and return current-schema values, migrating schema 1."""
    expected = PROFILE_FIELDS_V1 if schema_version == 1 else PROFILE_FIELDS_V2
    if not isinstance(profile, dict) or set(profile) != expected:
        raise ValueError("O perfil contém opções ausentes ou campos não reconhecidos.")
    for key in ("rotate_enabled", "stamp_enabled", "page_numbering", "optimize_enabled"):
        if not isinstance(profile[key], bool):
            raise ValueError("O perfil contém opções com tipos inválidos.")
    angle = profile["rotate_angle"]
    if not isinstance(angle, int) or isinstance(angle, bool) or angle not in (90, 180, 270):
        raise ValueError("O ângulo de rotação do perfil é inválido.")
    for key, max_length in (("rotate_ranges", 200), ("stamp_text", 500), ("stamp_ranges", 200)):
        value = profile[key]
        if not isinstance(value, str) or len(value) > max_length:
            raise ValueError("O perfil contém texto inválido ou longo demais.")
    if not isinstance(profile["optimize_mode"], str) or profile["optimize_mode"] not in ("lossless", "balanced"):
        raise ValueError("O modo de otimização do perfil é inválido.")
    quality = profile["quality"]
    if not isinstance(quality, int) or isinstance(quality, bool) or not 50 <= quality <= 95:
        raise ValueError("A qualidade do perfil deve ficar entre 50 e 95.")
    _validate_page_range_syntax(profile["rotate_ranges"])
    _validate_page_range_syntax(profile["stamp_ranges"])
    stamp_text = profile["stamp_text"]
    if stamp_text:
        try:
            stamp_text.encode("cp1252")
        except UnicodeEncodeError as error:
            raise ValueError(
                "A marca d'água contém caracteres não suportados pela fonte padrão. Use caracteres latinos e símbolos compatíveis."
            ) from error
    normalized = {key: profile[key] for key in PROFILE_FIELDS_V1}
    normalized["output_suffix"] = DEFAULT_OUTPUT_SUFFIX if schema_version == 1 else _validate_suffix(profile["output_suffix"])
    return normalized


def validate_profile_document(document: object) -> tuple[str, dict[str, object]]:
    """Validate a JSON profile and upgrade supported older schema versions."""
    if not isinstance(document, dict):
        raise ValueError("O arquivo de perfil não contém um objeto JSON.")
    if set(document) != {"schema_version", "name", "profile"}:
        raise ValueError("O arquivo contém campos extras ou não reconhecidos.")
    version = document.get("schema_version")
    if type(version) is not int or version not in (1, CURRENT_PROFILE_SCHEMA_VERSION):
        raise ValueError("A versão do perfil não é compatível.")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        raise ValueError("O nome do perfil é inválido.")
    return name.strip(), validate_profile_options(document.get("profile"), version)


def migrate_local_profile(profile: object) -> dict[str, object]:
    """Migrate a locally stored profile based on its exact recognized field set."""
    if not isinstance(profile, dict):
        raise ValueError("O perfil contém opções ausentes ou campos não reconhecidos.")
    if set(profile) == PROFILE_FIELDS_V1:
        return validate_profile_options(profile, 1)
    if set(profile) == PROFILE_FIELDS_V2:
        return validate_profile_options(profile, CURRENT_PROFILE_SCHEMA_VERSION)
    raise ValueError("O perfil contém opções ausentes ou campos não reconhecidos.")
