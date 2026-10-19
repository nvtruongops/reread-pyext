"""
Registry manager for translation models loaded from registry.json.
Provides access to model metadata, file roles, and validation hashes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..paths import resource_path


@dataclass(frozen=True)
class ModelFile:
    role: str  # "model", "shortlist", or "vocab"
    url: str
    download_bytes: int
    unpacked_bytes: int
    sha256: str


@dataclass(frozen=True)
class ModelMetadata:
    pair: str  # e.g. "envi", "vien", "zhen", "jaen"
    src_lang: str  # e.g. "en", "vi", "zh", "ja"
    tgt_lang: str  # e.g. "vi", "en"
    architecture: str
    download_bytes: int
    unpacked_bytes: int
    files: List[ModelFile]

    def get_file_by_role(self, role: str) -> Optional[ModelFile]:
        for f in self.files:
            if f.role == role:
                return f
        return None


class ModelRegistry:
    def __init__(self, registry_path: Path | str | None = None) -> None:
        if registry_path is None:
            self.registry_path = resource_path("data", "registry.json")
        else:
            self.registry_path = Path(registry_path)

        self._models: Dict[str, ModelMetadata] = {}
        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"registry.json not found at {self.registry_path}")

        with open(self.registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data.get("models", []):
            pair = entry.get("pair")
            files: List[ModelFile] = []
            for item in entry.get("files", []):
                files.append(
                    ModelFile(
                        role=item.get("role", ""),
                        url=item.get("url", ""),
                        download_bytes=item.get("downloadBytes", 0),
                        unpacked_bytes=item.get("bytes", 0),
                        sha256=item.get("sha256", ""),
                    )
                )

            metadata = ModelMetadata(
                pair=pair,
                src_lang=entry.get("from", ""),
                tgt_lang=entry.get("to", ""),
                architecture=entry.get("architecture", "base-memory"),
                download_bytes=entry.get("downloadBytes", 0),
                unpacked_bytes=entry.get("bytes", 0),
                files=files,
            )
            self._models[pair] = metadata

    def get(self, pair: str) -> Optional[ModelMetadata]:
        return self._models.get(pair)

    def find_pair(self, src: str, tgt: str) -> Optional[ModelMetadata]:
        for m in self._models.values():
            if m.src_lang == src and m.tgt_lang == tgt:
                return m
        return None

    def list_pairs(self) -> List[str]:
        return sorted(list(self._models.keys()))
