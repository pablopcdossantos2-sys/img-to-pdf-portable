from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_requirements_match_pyproject_runtime_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = set(project["project"]["dependencies"])
    requirements = {
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert declared == requirements


def test_batch_files_use_windows_crlf() -> None:
    for filename in ("instalar-e-iniciar.bat", "executar-aplicativo.bat"):
        content = (ROOT / filename).read_bytes()
        assert content.count(b"\n") == content.count(b"\r\n"), filename


def test_readmes_share_structure_and_document_distribution_requirements() -> None:
    structures = []
    for filename in ("README.md", "README.en.md", "README.es.md"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        structures.append((content.count("\n## "), content.count("\n### ")))
        assert "libxcb-cursor0" in content
        assert "[create-release]" in content
        assert "Start-Process -Wait -PassThru" in content
        assert "THIRD-PARTY-NOTICES.txt" in content
    assert len(set(structures)) == 1


def test_workflow_actions_are_pinned_to_full_commit_sha() -> None:
    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    uses = re.findall(r"^[ \t]*(?:-[ \t]*)?uses:[ \t]+([^ \t]+)", workflow, flags=re.MULTILINE)
    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", item) for item in uses)


def test_workflow_has_bounded_jobs_and_protects_releases() -> None:
    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    assert workflow.count("timeout-minutes:") >= 5
    assert "Tag $GITHUB_REF_NAME does not match application version $expected." in workflow
    assert "already exists" in workflow
    assert "cancel-in-progress: " + "${{ github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/main' && !contains(github.event.head_commit.message, '[create-release]')) }}" in workflow
    assert "&& 'release' || 'routine'" in workflow


def test_third_party_notice_generator_lists_runtime_dependencies() -> None:
    source = (ROOT / "scripts/generate_third_party_notices.py").read_text(encoding="utf-8")
    for package in ("PySide6", "shiboken6", "pypdf", "cryptography", "Pillow", "reportlab"):
        assert package in source
