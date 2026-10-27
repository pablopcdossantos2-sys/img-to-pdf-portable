from __future__ import annotations
import pytest
from document_tools.profiles import CURRENT_PROFILE_SCHEMA_VERSION, DEFAULT_OUTPUT_SUFFIX, migrate_local_profile, validate_profile_document


def schema_one_profile() -> dict[str, object]:
    return {
        "rotate_enabled": True, "rotate_angle": 90, "rotate_ranges": "",
        "stamp_enabled": False, "stamp_text": "", "page_numbering": False,
        "stamp_ranges": "", "optimize_enabled": True, "optimize_mode": "lossless", "quality": 82,
    }


def test_schema_one_json_profile_migrates_to_current_schema() -> None:
    name, profile = validate_profile_document({"schema_version": 1, "name": "Legacy profile", "profile": schema_one_profile()})
    assert name == "Legacy profile" and CURRENT_PROFILE_SCHEMA_VERSION == 2
    assert profile["output_suffix"] == DEFAULT_OUTPUT_SUFFIX
    assert profile["rotate_angle"] == 90 and profile["quality"] == 82


def test_schema_two_profile_round_trips_and_validates_safe_suffix() -> None:
    current = schema_one_profile()
    current["output_suffix"] = "_ready"
    name, profile = validate_profile_document({"schema_version": 2, "name": "Current profile", "profile": current})
    assert name == "Current profile" and profile["output_suffix"] == "_ready"


@pytest.mark.parametrize("version", [True, 0, 3, "1"])
def test_profile_document_rejects_invalid_or_future_schema_versions(version: object) -> None:
    with pytest.raises(ValueError, match="versão do perfil"):
        validate_profile_document({"schema_version": version, "name": "Bad", "profile": schema_one_profile()})


def test_local_settings_profile_is_migrated_without_paths_or_passwords() -> None:
    old = schema_one_profile()
    upgraded = migrate_local_profile(old)
    assert upgraded["output_suffix"] == "-processado"
    assert "password" not in upgraded and "source_path" not in upgraded
    assert old == schema_one_profile()


@pytest.mark.parametrize("suffix", ["../outside", "/root", r"\folder", "bad:name", "ends."])
def test_profile_rejects_unsafe_output_suffix(suffix: str) -> None:
    current = schema_one_profile()
    current["output_suffix"] = suffix
    with pytest.raises(ValueError, match="sufixo de saída"):
        validate_profile_document({"schema_version": 2, "name": "Bad suffix", "profile": current})


def test_profile_rejects_unknown_fields_in_every_schema() -> None:
    old = schema_one_profile()
    old["password"] = "never-accept"
    with pytest.raises(ValueError, match="campos não reconhecidos"):
        validate_profile_document({"schema_version": 1, "name": "Injected", "profile": old})
