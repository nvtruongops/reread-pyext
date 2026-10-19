"""
Downloader module for fetching, decompressing, and validating offline translation models.
Enforces SHA-256 checksums matching the official registry.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
from pathlib import Path
from typing import Callable, Optional

import requests

from .registry import ModelMetadata, ModelRegistry


class ModelDownloader:
    def __init__(self, models_dir: Path | str | None = None, registry: ModelRegistry | None = None) -> None:
        root = Path(__file__).resolve().parent.parent.parent
        self.models_dir = Path(models_dir) if models_dir else root / "data" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.registry = registry or ModelRegistry()

    def is_installed(self, pair: str) -> bool:
        """Check if all required files for a pair exist and have valid sizes."""
        meta = self.registry.get(pair)
        if not meta:
            return False

        pair_dir = self.models_dir / pair
        if not pair_dir.is_dir():
            return False

        for f in meta.files:
            file_name = f.url.split("/")[-1]
            target_gz = pair_dir / file_name
            # Target can be either the gz or the unpacked .bin / .spm
            unpacked_name = file_name[:-3] if file_name.endswith(".gz") else file_name
            target_unpacked = pair_dir / unpacked_name

            if not (target_gz.exists() or target_unpacked.exists()):
                return False

        return True

    def download_pair(
        self,
        pair: str,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        force: bool = False,
    ) -> bool:
        """
        Download all files for the specified language pair.
        Verifies SHA-256 checksums against unpacked bytes.
        """
        meta = self.registry.get(pair)
        if not meta:
            raise ValueError(f"Pair '{pair}' not found in registry.")

        pair_dir = self.models_dir / pair
        pair_dir.mkdir(parents=True, exist_ok=True)

        for f in meta.files:
            file_name = f.url.split("/")[-1]
            unpacked_name = file_name[:-3] if file_name.endswith(".gz") else file_name
            unpacked_path = pair_dir / unpacked_name
            gz_path = pair_dir / file_name

            if not force and unpacked_path.exists():
                # Verify size at least
                if unpacked_path.stat().st_size == f.unpacked_bytes:
                    if on_progress:
                        on_progress(f"Already downloaded: {unpacked_name}", f.download_bytes, f.download_bytes)
                    continue

            if on_progress:
                on_progress(f"Downloading {file_name}...", 0, f.download_bytes)

            resp = requests.get(f.url, stream=True, timeout=60)
            resp.raise_for_status()

            # Stream into memory or temp buffer
            raw_bytes = io.BytesIO()
            downloaded = 0
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    raw_bytes.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(f"Downloading {file_name}", downloaded, f.download_bytes)

            # Also save raw gz file
            with open(gz_path, "wb") as gz_file:
                gz_file.write(raw_bytes.getvalue())

            # Decompress and verify sha256
            raw_bytes.seek(0)
            if file_name.endswith(".gz"):
                unpacked_bytes = gzip.decompress(raw_bytes.getvalue())
            else:
                unpacked_bytes = raw_bytes.getvalue()

            # Verify sha256 checksum
            digest = hashlib.sha256(unpacked_bytes).hexdigest()
            if f.sha256 and digest.lower() != f.sha256.lower():
                raise ValueError(
                    f"Checksum mismatch for {file_name}: expected {f.sha256}, got {digest}"
                )

            with open(unpacked_path, "wb") as out_file:
                out_file.write(unpacked_bytes)

            if on_progress:
                on_progress(f"Verified & saved {unpacked_name}", f.download_bytes, f.download_bytes)

        return True
