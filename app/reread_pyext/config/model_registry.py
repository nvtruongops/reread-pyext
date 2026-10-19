"""
Model Registry Manager for re/read Python Desktop.
Parses data/models/registry.json, tracks installed translation engines,
and handles background downloading and uncompressing of offline language packages.
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from ..paths import models_dir as default_models_dir, package_root, resource_path

LANG_NAMES: Dict[str, str] = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "gl": "Galician",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "hu": "Hungarian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "nb": "Norwegian Bokmål",
    "nl": "Dutch",
    "nn": "Norwegian Nynorsk",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian",
    "sv": "Swedish",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh": "Chinese (Simplified)",
    "zh_hant": "Chinese (Traditional)",
}

LANG_NAMES_VI: Dict[str, str] = {
    "ar": "Tiếng Ả Rập",
    "bg": "Tiếng Bulgaria",
    "bn": "Tiếng Bengal",
    "ca": "Tiếng Catalan",
    "cs": "Tiếng Séc",
    "da": "Tiếng Đan Mạch",
    "de": "Tiếng Đức",
    "el": "Tiếng Hy Lạp",
    "en": "Tiếng Anh",
    "es": "Tiếng Tây Ban Nha",
    "et": "Tiếng Estonia",
    "eu": "Tiếng Basque",
    "fa": "Tiếng Ba Tư",
    "fi": "Tiếng Phần Lan",
    "fr": "Tiếng Pháp",
    "gl": "Tiếng Galicia",
    "he": "Tiếng Do Thái",
    "hi": "Tiếng Hindi",
    "hr": "Tiếng Croatia",
    "hu": "Tiếng Hungary",
    "id": "Tiếng Indonesia",
    "is": "Tiếng Iceland",
    "it": "Tiếng Ý",
    "ja": "Tiếng Nhật",
    "ko": "Tiếng Hàn",
    "lt": "Tiếng Litva",
    "lv": "Tiếng Latvia",
    "nb": "Tiếng Na Uy (Bokmål)",
    "nl": "Tiếng Hà Lan",
    "nn": "Tiếng Na Uy (Nynorsk)",
    "pl": "Tiếng Ba Lan",
    "pt": "Tiếng Bồ Đào Nha",
    "ro": "Tiếng Romania",
    "ru": "Tiếng Nga",
    "sk": "Tiếng Slovak",
    "sl": "Tiếng Slovenia",
    "sq": "Tiếng Albania",
    "sr": "Tiếng Serbia",
    "sv": "Tiếng Thụy Điển",
    "th": "Tiếng Thái",
    "tr": "Tiếng Thổ Nhĩ Kỳ",
    "uk": "Tiếng Ukraina",
    "ur": "Tiếng Urdu",
    "vi": "Tiếng Việt",
    "zh": "Tiếng Trung (Giản thể)",
    "zh_hant": "Tiếng Trung (Phồn thể)",
}


def _language_name_vi(code: str, fallback: str) -> str:
    normalized = code.strip().casefold()
    return LANG_NAMES_VI.get(normalized) or fallback.strip() or normalized.upper() or "Ngôn ngữ không xác định"


@dataclass
class ModelPackageInfo:
    pair: str
    from_lang: str
    to_lang: str
    from_name: str
    to_name: str
    download_bytes: int
    unpacked_bytes: int
    download_size_mb: float
    unpacked_size_mb: float
    architecture: str
    is_installed: bool
    installed_size_mb: float = 0.0
    files: Optional[List[Dict]] = None
    underlying_pair: Optional[str] = None

    @property
    def formatted_pair(self) -> str:
        return f"{self.from_lang.upper()} - {self.to_lang.upper()}"

    @property
    def effective_to_name(self) -> str:
        return self.to_name

    @property
    def from_display_name(self) -> str:
        return _language_name_vi(self.from_lang, self.from_name)

    @property
    def to_display_name(self) -> str:
        return _language_name_vi(self.to_lang, self.to_name)

    @property
    def display_name(self) -> str:
        return f"[{self.formatted_pair}] {self.from_name} -> {self.effective_to_name} ({self.download_size_mb:.1f} MB)"



class ModelRegistryManager:
    def __init__(
        self,
        root_dir: Optional[Path | str] = None,
        *,
        models_dir: Optional[Path | str] = None,
        registry_file: Optional[Path | str] = None,
    ) -> None:
        self.root_dir = Path(root_dir) if root_dir is not None else package_root()
        if root_dir is not None:
            self.models_dir = self.root_dir / "data" / "models"
            default_registry = self.models_dir / "registry.json"
        else:
            self.models_dir = Path(models_dir) if models_dir is not None else default_models_dir()
            default_registry = resource_path("data", "models", "registry.json")
        self.registry_file = Path(registry_file) if registry_file is not None else default_registry
        self._raw_models: List[Dict] = []
        self._load_registry()

    def _load_registry(self) -> None:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._raw_models = data.get("models", [])
            except Exception as e:
                print(f"[ModelRegistryManager] Error reading registry.json: {e}", flush=True)

    def get_installed_models(self) -> List[ModelPackageInfo]:
        """Scans data/models/ directory and returns list of installed translation engines."""
        installed: List[ModelPackageInfo] = []
        if not self.models_dir.exists():
            return installed

        for item in self.models_dir.iterdir():
            if item.is_dir():
                pair = item.name.lower()
                package = next((model for model in self._raw_models if model.get("pair") == pair), None)
                if package:
                    required_files = []
                    for file_info in package.get("files", []):
                        filename = str(file_info.get("url", "")).rsplit("/", 1)[-1]
                        if filename.endswith(".gz"):
                            filename = filename[:-3]
                        if filename:
                            required_files.append(item / filename)
                    is_complete = bool(required_files) and all(path.is_file() for path in required_files)
                else:
                    bin_files = list(item.glob("*.bin"))
                    vocab_files = list(item.glob("*.spm"))
                    is_complete = bool(bin_files and vocab_files)

                if is_complete:
                    # Calculate disk size
                    total_bytes = sum(f.stat().st_size for f in item.glob("*") if f.is_file())
                    total_mb = total_bytes / (1024 * 1024)

                    from_code = pair[:2]
                    to_code = pair[2:]
                    if len(pair) > 4:
                        if "zh_hant" in pair:
                            from_code = "zh_hant" if pair.startswith("zh_hant") else "en"
                            to_code = "en" if pair.startswith("zh_hant") else "zh_hant"

                    from_name = LANG_NAMES.get(from_code, from_code.upper())
                    to_name = LANG_NAMES.get(to_code, to_code.upper())

                    installed.append(
                        ModelPackageInfo(
                            pair=pair,
                            from_lang=from_code,
                            to_lang=to_code,
                            from_name=from_name,
                            to_name=to_name,
                            download_bytes=0,
                            unpacked_bytes=total_bytes,
                            download_size_mb=0.0,
                            unpacked_size_mb=total_mb,
                            architecture="intgemm8",
                            is_installed=True,
                            installed_size_mb=total_mb,
                        )
                    )

        # Ensure envi and vien are prioritized at the top
        installed.sort(key=lambda m: (0 if m.pair == "envi" else (1 if m.pair == "vien" else 2), m.pair))
        return installed

    def get_available_packages(self) -> List[ModelPackageInfo]:
        """Returns catalog of models available for download from registry."""
        installed_list = self.get_installed_models()
        installed_pairs = {m.pair for m in installed_list}
        installed_size_map = {m.pair: m.installed_size_mb for m in installed_list}
        packages: List[ModelPackageInfo] = []

        for m in self._raw_models:
            pair = m.get("pair", "")
            from_c = m.get("from", "")
            to_c = m.get("to", "")
            dl_b = int(m.get("downloadBytes", 0))
            un_b = int(m.get("bytes", 0))
            arch = m.get("architecture", "base-memory")
            files = m.get("files", [])

            from_n = LANG_NAMES.get(from_c, from_c.upper())
            to_n = LANG_NAMES.get(to_c, to_c.upper())

            is_inst = pair in installed_pairs

            # 1. Genuine model package (e.g. [RU - EN] Russian -> English)
            packages.append(
                ModelPackageInfo(
                    pair=pair,
                    from_lang=from_c,
                    to_lang=to_c,
                    from_name=from_n,
                    to_name=to_n,
                    download_bytes=dl_b,
                    unpacked_bytes=un_b,
                    download_size_mb=dl_b / (1024 * 1024),
                    unpacked_size_mb=un_b / (1024 * 1024),
                    architecture=arch,
                    is_installed=is_inst,
                    installed_size_mb=installed_size_map.get(pair, 0.0),
                    files=files,
                )
            )

            # 2. Companion Vietnamese target package for third languages translating through English
            # e.g. for "ruen", offer "ruvi": [RU - VI] Russian -> Vietnamese
            if to_c == "en" and from_c != "vi":
                vi_pair = f"{from_c}vi"
                packages.append(
                    ModelPackageInfo(
                        pair=vi_pair,
                        from_lang=from_c,
                        to_lang="vi",
                        from_name=from_n,
                        to_name="Vietnamese",
                        download_bytes=dl_b,
                        unpacked_bytes=un_b,
                        download_size_mb=dl_b / (1024 * 1024),
                        unpacked_size_mb=un_b / (1024 * 1024),
                        architecture=arch,
                        is_installed=is_inst,
                        installed_size_mb=installed_size_map.get(pair, 0.0),
                        files=files,
                        underlying_pair=pair,
                    )
                )

            # 3. Companion Vietnamese source package for translating from Vietnamese to third languages
            # e.g. for "enru", offer "viru": [VI - RU] Vietnamese -> Russian (vi -> en -> ru)
            if from_c == "en" and to_c != "vi":
                vi_pair = f"vi{to_c}"
                packages.append(
                    ModelPackageInfo(
                        pair=vi_pair,
                        from_lang="vi",
                        to_lang=to_c,
                        from_name="Vietnamese",
                        to_name=to_n,
                        download_bytes=dl_b,
                        unpacked_bytes=un_b,
                        download_size_mb=dl_b / (1024 * 1024),
                        unpacked_size_mb=un_b / (1024 * 1024),
                        architecture=arch,
                        is_installed=is_inst,
                        installed_size_mb=installed_size_map.get(pair, 0.0),
                        files=files,
                        underlying_pair=pair,
                    )
                )

        # Sort: uninstalled first, then popular pairs
        popular = [
            "zhen", "zhvi", "enzh", "vizh",
            "jaen", "javi", "enja", "vija",
            "ruen", "ruvi", "enru", "viru",
            "koen", "kovi", "enko", "viko",
            "deen", "devi", "ende", "vide",
            "fren", "frvi", "enfr", "vifr",
            "esen", "esvi", "enes", "vies",
            "iten", "itvi", "enit", "viit",
            "envi", "vien"
        ]
        def sort_key(p: ModelPackageInfo):
            is_pop = 0 if p.pair in popular else 1
            pop_idx = popular.index(p.pair) if p.pair in popular else 99
            return (0 if not p.is_installed else 1, is_pop, pop_idx, p.display_name)

        packages.sort(key=sort_key)
        return packages

    def _resolve_real_pair(self, pair: str) -> str:
        """Resolves virtual companion pair (e.g. viru -> enru, ruvi -> ruen) to physical directory pair."""
        p = pair.lower().strip()
        if p.startswith("vi") and len(p) == 4 and p != "vien":
            return f"en{p[2:]}"
        if p.endswith("vi") and len(p) == 4 and p != "envi":
            return f"{p[:2]}en"
        return p

    def download_model(
        self,
        pair: str,
        on_progress: Optional[Callable[[str, float], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str, str], None]] = None,
    ) -> threading.Thread:
        """Downloads and unpacks model package in a daemon background thread."""
        real_pair = self._resolve_real_pair(pair)

        def _worker():
            package = next((m for m in self._raw_models if m.get("pair") == real_pair), None)
            if not package:
                if on_error:
                    on_error(pair, f"Package '{pair}' (engine: '{real_pair}') not found in registry.")
                return

            target_dir = self.models_dir / real_pair
            target_dir.mkdir(parents=True, exist_ok=True)

            files = package.get("files", [])
            total_files = len(files)
            if total_files == 0:
                if on_error:
                    on_error(pair, f"No files defined for package '{pair}'.")
                return

            try:
                for idx, f_info in enumerate(files, start=1):
                    url = f_info.get("url")
                    role = f_info.get("role", "file")
                    if not url:
                        continue

                    url_filename = url.split("/")[-1]
                    dest_gz = target_dir / url_filename

                    if on_progress:
                        on_progress(f"Downloading {role} ({idx}/{total_files})...", (idx - 1) / total_files)

                    # Download with urllib
                    req = urllib.request.Request(url, headers={"User-Agent": "reread-desktop/1.0"})
                    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_gz, "wb") as out_f:
                        shutil.copyfileobj(resp, out_f)

                    # Decompress .gz if it is gzipped
                    if url_filename.endswith(".gz"):
                        unpacked_name = url_filename[:-3]
                        dest_unpacked = target_dir / unpacked_name
                        if on_progress:
                            on_progress(f"Unpacking {unpacked_name}...", (idx - 0.2) / total_files)
                        with gzip.open(dest_gz, "rb") as gz_in, open(dest_unpacked, "wb") as un_out:
                            shutil.copyfileobj(gz_in, un_out)

                if on_progress:
                    on_progress(f"Installed {pair.upper()} successfully!", 1.0)
                if on_complete:
                    on_complete(pair)
            except Exception as e:
                print(f"[ModelRegistryManager] Download error for {pair} ({real_pair}): {e}", flush=True)
                if on_error:
                    on_error(pair, str(e))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t

    def delete_model(self, pair: str) -> tuple[bool, str]:
        """Deletes an installed model directory from data/models/<pair>."""
        pair = pair.lower().strip()
        real_pair = self._resolve_real_pair(pair)

        target_dir = self.models_dir / real_pair
        if not target_dir.exists():
            return False, f"Model directory for '{real_pair.upper()}' does not exist."

        try:
            shutil.rmtree(target_dir)
            return True, f"Model '{pair.upper()}' (engine: '{real_pair.upper()}') deleted successfully."
        except Exception as e:
            return False, f"Failed to delete model '{pair.upper()}': {e}"



