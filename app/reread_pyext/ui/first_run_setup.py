"""One-time model storage setup shown on the app's first launch."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..config.settings import SettingsManager
from ..config.startup import StartupManager
from ..paths import models_dir
from .main_window import AppCheckBox, AppComboBox, _style_combo_popup
from .translations import set_ui_language, translate


class FirstRunSetupDialog(QDialog):
    def __init__(self, settings: SettingsManager, preferred_language: str | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.language = set_ui_language(preferred_language or settings.config.ui_language)
        self.startup = StartupManager()
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        self.title = QLabel("Thiết lập lần đầu")
        self.title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        self.description = QLabel(
            "Ứng dụng chưa tải mô hình nào. Sau khi hoàn tất, bạn có thể tải mô hình ở mục Mô hình. "
            "Thư mục lưu và thay đổi vị trí có trong Cài đặt."
        )
        self.description.setWordWrap(True)
        self.language_combo = AppComboBox()
        self.language_combo.setObjectName("uiLanguage")
        self.language_combo.addItem("Tiếng Việt", "vi")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(0 if self.language == "vi" else 1)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        _style_combo_popup(self.language_combo)
        self.language_label = QLabel("Ngôn ngữ giao diện")
        self.start_on_boot = AppCheckBox("Mở re/read khi đăng nhập Windows (chạy nền)")
        self.start_on_boot.setChecked(settings.config.start_on_boot)
        self.start_on_boot.setVisible(sys.platform == "win32")
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #a03e40;")
        self.error_label.hide()

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self.reject)
        self.continue_button = QPushButton("Hoàn tất thiết lập")
        self.continue_button.setObjectName("primaryButton")
        self.continue_button.setProperty("setupAction", "finish")
        self.continue_button.clicked.connect(self._save_and_accept)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.continue_button)

        layout.addWidget(self.title)
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(self.description)
        layout.addWidget(self.start_on_boot)
        layout.addWidget(self.error_label)
        layout.addLayout(button_row)
        self._retranslate()
        if preferred_language is not None:
            self.language_label.hide()
            self.language_combo.hide()

    def _language_changed(self, _index: int) -> None:
        self.language = set_ui_language(str(self.language_combo.currentData()))
        self._retranslate()

    def _retranslate(self) -> None:
        self.setWindowTitle(translate("Thiết lập re/read", self.language))
        self.title.setText(translate("Thiết lập lần đầu", self.language))
        self.description.setText(
            translate(
                "Ứng dụng chưa tải mô hình nào. Sau khi hoàn tất, bạn có thể tải mô hình ở mục Mô hình. "
                "Thư mục lưu và thay đổi vị trí có trong Cài đặt.",
                self.language,
            )
        )
        self.language_label.setText(translate("Ngôn ngữ giao diện", self.language))
        self.start_on_boot.setText(translate("Mở re/read khi đăng nhập Windows (chạy nền)", self.language))
        self.cancel_button.setText(translate("Hủy", self.language))
        self.continue_button.setText(translate("Hoàn tất thiết lập", self.language))
        self.language_combo.setItemText(0, translate("Tiếng Việt", self.language))
        self.language_combo.setItemText(1, translate("English", self.language))

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _restore_startup_registration(
        self, was_registered: bool, previous_command: str | None
    ) -> None:
        if was_registered:
            self.startup.register(previous_command)
        else:
            self.startup.clear_keys()

    def _save_and_accept(self) -> None:
        wants_startup = self.start_on_boot.isChecked() if sys.platform == "win32" else False
        was_registered, _name, previous_command = self.startup.is_registered()
        registration_changed = False
        if wants_startup and not was_registered:
            startup_ok, startup_message = self.startup.register()
            registration_changed = startup_ok
        elif not wants_startup and was_registered:
            startup_ok, startup_message, _count = self.startup.clear_keys()
            registration_changed = startup_ok
        else:
            startup_ok, startup_message = True, ""
        if not startup_ok:
            self._show_error(translate("Không thể cập nhật khởi động", self.language) + ": " + startup_message)
            return

        try:
            if not self.settings.complete_first_run_setup(
                models_dir(self.settings.config.model_directory),
                str(self.language_combo.currentData()),
                wants_startup,
            ):
                raise OSError(translate("Không thể lưu thiết lập vào thư mục dữ liệu của ứng dụng.", self.language))
        except Exception as exc:
            if registration_changed:
                self._restore_startup_registration(was_registered, previous_command)
            self._show_error(translate("Không thể lưu thiết lập: ", self.language) + str(exc))
            return
        self.accept()
