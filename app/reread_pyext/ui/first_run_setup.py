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


class FirstRunSetupDialog(QDialog):
    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.settings = settings
        self.setWindowTitle("Thiết lập re/read")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel("Chọn nơi lưu mô hình")
        title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        description = QLabel(
            "Chọn thư mục để lưu các mô hình dịch. Ứng dụng chưa tải mô hình nào; "
            "bạn có thể tải từng mô hình sau trong mục Mô hình."
        )
        description.setWordWrap(True)
        self.directory_edit = QLineEdit(str(models_dir(settings.config.model_directory)))
        self.directory_edit.setAccessibleName("Thư mục lưu mô hình")
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #a03e40;")
        self.error_label.hide()

        directory_row = QHBoxLayout()
        directory_row.addWidget(self.directory_edit, 1)
        browse_button = QPushButton("Duyệt…")
        browse_button.clicked.connect(self._browse)
        directory_row.addWidget(browse_button)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.reject)
        continue_button = QPushButton("Hoàn tất thiết lập")
        continue_button.setObjectName("primaryButton")
        continue_button.clicked.connect(self._save_and_accept)
        button_row.addWidget(cancel_button)
        button_row.addWidget(continue_button)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(directory_row)
        layout.addWidget(self.error_label)
        layout.addLayout(button_row)

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục lưu mô hình",
            self.directory_edit.text(),
        )
        if directory:
            self.directory_edit.setText(directory)

    def _save_and_accept(self) -> None:
        try:
            if not self.settings.complete_first_run_setup(self.directory_edit.text()):
                raise OSError("Không thể lưu thiết lập vào thư mục dữ liệu của ứng dụng.")
        except Exception as exc:
            self.error_label.setText(f"Không thể thiết lập thư mục này: {exc}")
            self.error_label.show()
            return
        self.accept()
