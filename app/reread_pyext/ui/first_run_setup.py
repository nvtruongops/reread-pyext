"""One-time model storage setup shown on the app's first launch."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..config.settings import SettingsManager
from ..paths import models_dir
from .main_window import AppComboBox, _style_combo_popup
from .translations import localize_widgets, set_ui_language, translate


class FirstRunSetupDialog(QDialog):
    def __init__(self, settings: SettingsManager, preferred_language: str | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.language = set_ui_language(preferred_language or settings.config.ui_language)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        self.title = QLabel("Chọn nơi lưu mô hình")
        self.title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        self.description = QLabel(
            "Chọn thư mục để lưu các mô hình dịch. Ứng dụng chưa tải mô hình nào; "
            "bạn có thể tải từng mô hình sau trong mục Mô hình."
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
        self.directory_edit = QLineEdit(str(models_dir(settings.config.model_directory)))
        self.directory_edit.setAccessibleName("Thư mục lưu mô hình")
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #a03e40;")
        self.error_label.hide()

        directory_row = QHBoxLayout()
        directory_row.addWidget(self.directory_edit, 1)
        self.browse_button = QPushButton("Duyệt…")
        self.browse_button.clicked.connect(self._browse)
        directory_row.addWidget(self.browse_button)
        self.folder_label = QLabel("Thư mục lưu mô hình")

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
        layout.addWidget(self.folder_label)
        layout.addLayout(directory_row)
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
        for widget in (self, *self.findChildren(QLabel), *self.findChildren(QPushButton)):
            if widget is self:
                continue
            if isinstance(widget, QLabel):
                widget.setText(translate(widget.text(), self.language))
            elif isinstance(widget, QPushButton):
                widget.setText(translate(widget.text(), self.language))
        localize_widgets(self, self.language)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            translate("Chọn thư mục lưu mô hình", self.language),
            self.directory_edit.text(),
        )
        if directory:
            self.directory_edit.setText(directory)

    def _save_and_accept(self) -> None:
        try:
            if not self.settings.complete_first_run_setup(
                self.directory_edit.text(), str(self.language_combo.currentData())
            ):
                raise OSError(translate("Không thể lưu thiết lập vào thư mục dữ liệu của ứng dụng.", self.language))
        except Exception as exc:
            self.error_label.setText(translate("Không thể thiết lập thư mục này: ", self.language) + str(exc))
            self.error_label.show()
            return
        self.accept()
