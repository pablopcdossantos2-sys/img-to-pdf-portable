#!/usr/bin/env python3
"""Collect third-party license texts from the installed runtime distributions."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path, PurePosixPath

PACKAGES = ("PySide6", "shiboken6", "pypdf", "cryptography", "Pillow", "reportlab")
TEXT_SUFFIXES = {"", ".txt", ".md", ".rst", ".html", ".license", ".notice"}
NOTICE_NAMES = {
    "license", "license.txt", "licence", "licence.txt", "copying", "copying.txt",
    "notice", "notice.txt", "third-party-notices.txt", "third_party_notices.txt",
}


def _is_license_file(relative: str) -> bool:
    normalized = relative.replace("\\", "/")
    path = PurePosixPath(normalized)
    parts = tuple(part.casefold() for part in path.parts)
    basename = path.name.casefold()
    under_license_folder = any(part in {"licenses", "licences"} for part in parts[:-1])
    looks_like_notice = basename in NOTICE_NAMES or (
        any(word in basename for word in ("license", "licence", "copying", "notice"))
        and path.suffix.casefold() in TEXT_SUFFIXES
    )
    return path.suffix.casefold() in TEXT_SUFFIXES and (under_license_folder or looks_like_notice)


def generate(output: Path) -> None:
    sections = [
        "PDF Hub — third-party license texts",
        "Generated from the installed runtime distributions used for this build.",
        "This file supplements LICENSES-THIRD-PARTY.md; retain it when redistributing the package.",
        "See the project license index for upstream licensing links, including Qt for Python.",
        "",
    ]
    missing = []
    for package in PACKAGES:
        try:
            dist = distribution(package)
        except PackageNotFoundError:
            missing.append(package)
            continue

        name = dist.metadata.get("Name", package)
        license_expression = (
            dist.metadata.get("License-Expression")
            or dist.metadata.get("License")
            or "No SPDX/license expression was supplied in package metadata."
        )
        sections.extend([
            "=" * 78,
            f"{name} {dist.version}",
            f"License metadata: {license_expression}",
            "=" * 78,
            "",
        ])
        count = 0
        for entry in sorted(dist.files or [], key=lambda item: str(item).casefold()):
            relative = str(entry)
            if not _is_license_file(relative):
                continue
            try:
                text = dist.locate_file(entry).read_text(encoding="utf-8")
            except (OSError, UnicodeError, AttributeError):
                continue
            if not text.strip():
                continue
            sections.extend([f"--- {name}: {relative} ---", text.rstrip(), ""])
            count += 1
        if count == 0:
            sections.extend([
                "No separate license file was present in the installed file list.",
                "Review the license metadata and upstream project before redistributing this dependency.",
                "",
            ])

    if missing:
        raise RuntimeError("Missing runtime distributions required for notices: " + ", ".join(missing))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    if output.stat().st_size < 500:
        raise RuntimeError("The third-party license notice file is empty or incomplete.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("THIRD-PARTY-NOTICES.txt"))
    args = parser.parse_args()
    generate(args.output)
    print(f"Generated {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
