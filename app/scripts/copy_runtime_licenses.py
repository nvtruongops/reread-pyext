"""Collect license and notice files for the runtime dependency bundle."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import re
import shutil
import sys
from pathlib import Path, PurePosixPath


ROOT_DISTRIBUTIONS = ("PySide6", "requests", "fastapi", "uvicorn", "pydantic", "Nuitka")
LICENSE_PREFIXES = ("license", "licence", "copying", "notice", "copyright")


def _distribution_names() -> list[metadata.Distribution]:
    selected: dict[str, metadata.Distribution] = {}
    pending = list(ROOT_DISTRIBUTIONS)
    while pending:
        requested = pending.pop()
        try:
            distribution = metadata.distribution(requested)
        except metadata.PackageNotFoundError:
            continue
        key = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).casefold()
        if key in selected:
            continue
        selected[key] = distribution
        for requirement in distribution.requires or []:
            base_requirement, _, marker = requirement.partition(";")
            if "extra" in marker:
                continue
            match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", base_requirement)
            if match:
                pending.append(match.group(1))
    return sorted(selected.values(), key=lambda item: item.metadata["Name"].casefold())


def _copy_license_files(distribution: metadata.Distribution, output: Path) -> list[str]:
    name = distribution.metadata["Name"]
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{name}-{distribution.version}")
    destination = output / safe_name
    copied: list[str] = []
    for entry in distribution.files or ():
        relative = PurePosixPath(str(entry))
        if ".." in relative.parts:
            continue
        filename = relative.name.casefold()
        if not filename.startswith(LICENSE_PREFIXES):
            continue
        source = Path(distribution.locate_file(entry))
        if not source.is_file():
            continue
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(output)))
    if not copied:
        license_id = distribution.metadata.get("License-Expression") or distribution.metadata.get("License")
        if license_id:
            destination.mkdir(parents=True, exist_ok=True)
            marker = destination / "LICENSE-ID.txt"
            marker.write_text(f"{name} {distribution.version}\nLicense metadata: {license_id}\n", encoding="utf-8")
            copied.append(str(marker.relative_to(output)))
    return copied


def copy_runtime_licenses(output_directory: Path) -> int:
    output_directory.mkdir(parents=True, exist_ok=True)
    distributions = _distribution_names()
    copied_files: list[str] = []
    manifest_lines = ["License files collected from the build environment.", ""]
    for distribution in distributions:
        files = _copy_license_files(distribution, output_directory)
        manifest_lines.append(
            f"{distribution.metadata['Name']} {distribution.version}: "
            f"{distribution.metadata.get('License-Expression') or distribution.metadata.get('License') or 'license files included'}"
        )
        copied_files.extend(files)

    python_root = Path(sys.base_prefix)
    for candidate in (python_root / "LICENSE.txt", python_root / "LICENSE"):
        if candidate.is_file():
            python_dir = output_directory / "Python"
            python_dir.mkdir(parents=True, exist_ok=True)
            target = python_dir / candidate.name
            shutil.copy2(candidate, target)
            copied_files.append(str(target.relative_to(output_directory)))
            break

    if not copied_files:
        print("No dependency license files were found.", file=sys.stderr)
        return 1
    manifest_lines.extend(("", "Copied files:", *[f"- {name}" for name in sorted(copied_files)]))
    (output_directory / "MANIFEST.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"Copied {len(copied_files)} runtime license and notice files to {output_directory}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    return copy_runtime_licenses(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
