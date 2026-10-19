"""Remove re/read-owned data during uninstall."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .paths import canonical_app_data_dir, resource_path


_PAIR_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _is_reparse_point(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & reparse_flag)


def _normalized_path(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _is_within(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((_normalized_path(path), _normalized_path(parent))) == _normalized_path(parent)
    except ValueError:
        return False


def _first_reparse_ancestor(path: Path) -> Path | None:
    current = path
    while True:
        if _is_reparse_point(current):
            return current
        if current.parent == current:
            return None
        current = current.parent


def _registry_files(registry_path: Path) -> dict[str, set[str]]:
    with registry_path.open("r", encoding="utf-8") as registry_file:
        registry = json.load(registry_file)

    result: dict[str, set[str]] = {}
    for model in registry.get("models", []):
        pair = str(model.get("pair", ""))
        if not _PAIR_RE.fullmatch(pair):
            continue
        names = result.setdefault(pair, set())
        for item in model.get("files", []):
            name = unquote(Path(urlsplit(str(item.get("url", ""))).path).name)
            if not name or name in {".", ".."} or Path(name).name != name:
                continue
            names.add(name)
            if name.endswith(".gz"):
                names.add(name[:-3])
    return result


def _remove_external_models(model_directory: Path, registry_path: Path) -> list[str]:
    errors: list[str] = []
    if not model_directory.is_absolute():
        return [f"Custom model directory is not absolute; left unchanged: {model_directory}"]

    try:
        model_files = _registry_files(registry_path)
    except Exception as exc:
        return [f"Could not read model registry {registry_path}: {exc}"]

    if not model_directory.exists():
        return errors
    reparse_ancestor = _first_reparse_ancestor(model_directory)
    if reparse_ancestor is not None:
        return [f"Custom model path crosses a reparse point; left unchanged: {reparse_ancestor}"]

    for pair, filenames in model_files.items():
        pair_directory = model_directory / pair
        if not pair_directory.exists():
            continue
        if _is_reparse_point(pair_directory):
            errors.append(f"Model folder is a reparse point; left unchanged: {pair_directory}")
            continue
        if not pair_directory.is_dir():
            continue

        for filename in filenames:
            candidate = pair_directory / filename
            if _is_reparse_point(candidate):
                errors.append(f"Model file is a reparse point; left unchanged: {candidate}")
                continue
            try:
                if candidate.is_file():
                    candidate.unlink()
            except OSError as exc:
                errors.append(f"Could not remove {candidate}: {exc}")

        try:
            pair_directory.rmdir()
        except OSError:
            pass
    return errors


def cleanup_user_data(
    app_data_root: Path | str,
    model_directory: Path | str | None,
    registry_path: Path | str,
) -> list[str]:
    """Delete app-owned data and model files, returning paths that need attention."""
    app_root = Path(app_data_root).expanduser().absolute()
    registry = Path(registry_path)
    errors: list[str] = []

    if app_root.exists():
        if _is_reparse_point(app_root):
            errors.append(f"App data root is a reparse point; left unchanged: {app_root}")
        else:
            try:
                shutil.rmtree(app_root)
            except OSError as exc:
                errors.append(f"Could not remove app data {app_root}: {exc}")

    if model_directory:
        selected_root = Path(model_directory).expanduser()
        if not selected_root.is_absolute():
            errors.append(f"Custom model directory is not absolute; left unchanged: {selected_root}")
            return errors
        model_root = selected_root.absolute()
        if _is_within(model_root, app_root) or _is_within(app_root, model_root):
            return errors
        errors.extend(_remove_external_models(model_root, registry))
    return errors


def cleanup_installed_data() -> list[str]:
    """Resolve installed paths without honoring developer-only environment overrides."""
    app_root = canonical_app_data_dir()
    registry_path = resource_path("data", "registry.json")
    model_directory: str | None = None
    config_path = app_root / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        model_directory = str(config.get("model_directory") or "").strip() or None
    except FileNotFoundError:
        pass
    except Exception as exc:
        errors = cleanup_user_data(app_root, None, registry_path)
        errors.insert(0, f"Could not read app settings {config_path}; an external model folder may remain: {exc}")
        return errors

    return cleanup_user_data(app_root, model_directory, registry_path)


def main() -> int:
    errors = cleanup_installed_data()
    for error in errors:
        print(error, flush=True)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
