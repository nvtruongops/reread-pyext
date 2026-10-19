"""Runtime paths for packaged assets and per-user application data."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from shutil import which


APP_NAME = "re-read"


def package_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if "__compiled__" in globals():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    return package_root().joinpath(*parts)


def app_data_dir() -> Path:
    override = os.environ.get("REREAD_DATA_DIR")
    if override:
        return Path(override).expanduser()

    return canonical_app_data_dir()


def canonical_app_data_dir() -> Path:
    """Return the installed user's app data directory, ignoring development overrides."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_NAME


def models_dir(directory: Path | str | None = None) -> Path:
    if directory and str(directory).strip():
        return Path(directory).expanduser()
    return app_data_dir() / "models" / "reread_pyext"


def node_executable() -> str:
    override = os.environ.get("REREAD_NODE_EXECUTABLE")
    if override:
        return override
    packaged = resource_path("runtime", "node.exe" if sys.platform == "win32" else "node")
    if packaged.is_file():
        return str(packaged)
    return which("node") or "node"


def migrate_legacy_data() -> list[str]:
    """Copy legacy user data into the app data directory without removing its source."""
    if os.environ.get("REREAD_DATA_DIR"):
        return []

    legacy = package_root() / "data"
    destination = app_data_dir()
    copied: list[str] = []

    for name in ("config.json", "history.json"):
        source = legacy / name
        target = destination / name
        if source.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(name)

    source_models = legacy / "models"
    migration_marker = destination / ".legacy-models-migrated"
    if source_models.is_dir() and not migration_marker.exists():
        for source in source_models.iterdir():
            if not source.is_dir():
                continue
            target = models_dir() / source.name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, target)
                copied.append(f"models/reread_pyext/{source.name}")
        migration_marker.parent.mkdir(parents=True, exist_ok=True)
        migration_marker.touch()

    return copied
