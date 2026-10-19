"""
Local model store manager.
Discovers and manages unpacked model, shortlist, and vocabulary files.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..paths import migrate_legacy_data, models_dir as default_models_dir
from .registry import ModelMetadata, ModelRegistry


@dataclass
class LoadedModelFiles:
    pair: str
    model_path: Path
    shortlist_path: Path
    vocab_paths: List[Path]


class ModelStore:
    def __init__(self, models_dir: Path | str | None = None, registry: ModelRegistry | None = None) -> None:
        if models_dir is None:
            migrate_legacy_data()
        self.models_dir = Path(models_dir) if models_dir else default_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry or ModelRegistry()

    def list_installed_pairs(self) -> List[str]:
        installed = []
        for pair_dir in self.models_dir.iterdir():
            if pair_dir.is_dir():
                pair = pair_dir.name
                meta = self.registry.get(pair)
                if meta:
                    installed.append(pair)
        return sorted(installed)

    def get_model_files(self, pair: str) -> Optional[LoadedModelFiles]:
        """
        Locates the unpacked model, shortlist, and vocab files.
        Automatically ungzips if only .gz is present.
        """
        pair_dir = self.models_dir / pair
        if not pair_dir.is_dir():
            return None

        meta = self.registry.get(pair)
        if not meta:
            return None

        model_path: Optional[Path] = None
        shortlist_path: Optional[Path] = None
        vocab_paths: List[Path] = []

        for f in meta.files:
            file_name = f.url.split("/")[-1]
            unpacked_name = file_name[:-3] if file_name.endswith(".gz") else file_name
            unpacked_path = pair_dir / unpacked_name
            gz_path = pair_dir / file_name

            if not unpacked_path.exists() and gz_path.exists():
                # Auto decompress
                with gzip.open(gz_path, "rb") as gz_in, open(unpacked_path, "wb") as out_f:
                    out_f.write(gz_in.read())

            if not unpacked_path.exists():
                return None

            if f.role == "model":
                model_path = unpacked_path
            elif f.role == "shortlist":
                shortlist_path = unpacked_path
            elif f.role == "vocab":
                vocab_paths.append(unpacked_path)

        if model_path and shortlist_path and vocab_paths:
            return LoadedModelFiles(
                pair=pair,
                model_path=model_path,
                shortlist_path=shortlist_path,
                vocab_paths=vocab_paths,
            )

        return None
