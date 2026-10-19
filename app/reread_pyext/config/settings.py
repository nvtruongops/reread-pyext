"""
Configuration and settings manager.
Persists desktop translation preferences into data/config.json.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, List, Optional

from ..paths import app_data_dir


@dataclass
class AppConfig:
    auto_drag: bool = True  # Enable hold-to-translate when dragging mouse
    hold_duration_seconds: float = 2.0  # Hold mouse button for X seconds to show translation, release to hide
    double_ctrl_c: bool = True  # Double Ctrl+C shortcut to translate
    enable_history: bool = True  # Save translation history locally
    double_ctrl_v_history: bool = True  # Double Ctrl+V shortcut to view recent translation history
    auto_close_seconds: int = 15  # Auto-close popup timer in seconds (0 = keep open until clicked outside)
    reverse_vi_to_en: bool = True  # Auto-detect Vietnamese and reverse translate to English
    pivot_cjk: bool = True  # Translate Chinese/Japanese to Vietnamese via English pivot
    start_on_boot: bool = False  # Start re/read background service automatically when Windows boots
    target_lang: str = "vi"  # Primary translation target language (e.g. "vi", "en", "ru", "zh", "ja")
    ui_language: str = "vi"  # Interface language; independent of the translation target
    model_directory: str = ""  # Empty means the default per-user models folder
    setup_complete: bool = False  # First-run model folder setup has been completed



class SettingsManager:
    def __init__(self, config_path: Optional[Path | str] = None) -> None:
        if config_path is None:
            self.config_path = app_data_dir() / "config.json"
        else:
            self.config_path = Path(config_path)

        self._config = AppConfig()
        self._listeners: List[Callable[[AppConfig], None]] = []
        self.load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    model_directory = str(data.get("model_directory") or "").strip()
                    self._config = AppConfig(
                        auto_drag=data.get("auto_drag", True),
                        hold_duration_seconds=float(data.get("hold_duration_seconds", 2.0)),
                        double_ctrl_c=data.get("double_ctrl_c", True),
                        enable_history=data.get("enable_history", True),
                        double_ctrl_v_history=data.get("double_ctrl_v_history", True),
                        auto_close_seconds=int(data.get("auto_close_seconds", 15)),
                        reverse_vi_to_en=data.get("reverse_vi_to_en", True),
                        pivot_cjk=data.get("pivot_cjk", True),
                        start_on_boot=data.get("start_on_boot", False),
                        target_lang=data.get("target_lang", "vi"),
                        ui_language=data.get("ui_language") if data.get("ui_language") in ("vi", "en") else "vi",
                        model_directory=model_directory,
                        setup_complete=bool(data.get("setup_complete", bool(model_directory))),
                    )

            except Exception as e:
                print(f"[SettingsManager] Error loading config: {e}. Using defaults.", flush=True)
                self._config = AppConfig()
        else:
            self.save()
        return self._config

    def save(self) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            self._notify_listeners()
            return True
        except Exception as e:
            print(f"[SettingsManager] Error saving config: {e}", flush=True)
            return False

    def update(self, **kwargs) -> bool:
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        return self.save()

    def complete_first_run_setup(
        self,
        model_directory: Path | str,
        ui_language: str = "vi",
        start_on_boot: bool | None = None,
    ) -> bool:
        selected = str(model_directory).strip()
        if not selected:
            raise ValueError("A model directory must be selected.")
        if ui_language not in ("vi", "en"):
            raise ValueError("The interface language must be 'vi' or 'en'.")

        directory = Path(selected).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        previous_directory = self._config.model_directory
        previous_setup_complete = self._config.setup_complete
        previous_ui_language = self._config.ui_language
        previous_start_on_boot = self._config.start_on_boot
        self._config.model_directory = str(directory.resolve())
        self._config.setup_complete = True
        self._config.ui_language = ui_language
        if start_on_boot is not None:
            self._config.start_on_boot = start_on_boot
        if not self.save():
            self._config.model_directory = previous_directory
            self._config.setup_complete = previous_setup_complete
            self._config.ui_language = previous_ui_language
            self._config.start_on_boot = previous_start_on_boot
            return False
        return True

    def add_listener(self, callback: Callable[[AppConfig], None]) -> None:
        self._listeners.append(callback)

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            try:
                cb(self._config)
            except Exception:
                pass
