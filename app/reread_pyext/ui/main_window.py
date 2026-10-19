"""PySide6 desktop shell and its primary pages."""

from __future__ import annotations

import re
import threading
import unicodedata
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QTextCursor
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyleOptionButton,
    QStyleOptionComboBox,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config.history import HistoryManager
from ..config.model_registry import ModelPackageInfo, ModelRegistryManager
from ..config.database import database_path
from ..config.settings import AppConfig, SettingsManager
from ..config.startup import StartupManager
from ..logger import AppLogger
from ..paths import app_data_dir, models_dir, resource_path
from .. import __version__
from ..update_checker import UpdateCheckResult, check_for_update, download_installer
from .translations import localize_widgets, set_ui_language, translate, ui_language


PAGE_OVERVIEW, PAGE_HISTORY, PAGE_MODELS, PAGE_SETTINGS, PAGE_ACTIVITY = range(5)
APP_NAME = "re/read Desktop"
TARGETS = [
    ("Tiếng Việt (VI)", "vi"),
    ("Tiếng Anh (EN)", "en"),
    ("Tiếng Nga", "ru"),
    ("Tiếng Trung", "zh"),
    ("Tiếng Nhật", "ja"),
]

APP_STYLE = """
QMainWindow, QWidget#appRoot { background: #f3f6f4; color: #1d2927; }
QDialog { background: #f3f6f4; color: #1d2927; }
QDialog QLabel { color: #1d2927; background: transparent; }
QStackedWidget, QScrollArea, QWidget#desktopPageContent, QWidget#settingsPage { background: #f3f6f4; }
QWidget { font-family: "Segoe UI"; font-size: 10pt; color: #1d2927; }
QFrame#sidebar { background: #17312e; border: none; }
QLabel#brand { color: #f8fbf9; font-size: 19pt; font-weight: 700; }
QLabel#brandSub { color: #a9c0bb; font-size: 9pt; }
QLabel#navGroup { color: #91aaa4; font-size: 8pt; font-weight: 700; padding: 8px 10px 2px; }
QPushButton#navButton { color: #d0dfdb; background: transparent; border: none; border-radius: 8px; text-align: left; padding: 10px 12px; font-weight: 600; }
QPushButton#navButton:hover { color: white; background: #23413d; }
QPushButton#navButton:checked { color: white; background: #2d625b; }
QPushButton#navButton:focus { border: 2px solid #9dd4c7; }
QFrame#topbar { background: #ffffff; border-bottom: 1px solid #dce5e1; }
QFrame#settingsFooter { background: #ffffff; border-top: 1px solid #dce5e1; }
QLabel#pageTitle { color: #1b2927; font-size: 14pt; font-weight: 650; }
QLabel#statusText { color: #315b54; background: #e9f3ef; border-radius: 10px; padding: 6px 10px; }
QLabel#dirtyStatus { color: #315b54; background: #e9f3ef; border-radius: 8px; padding: 6px 10px; }
QLabel#dirtyStatus[dirty="true"] { color: #805a1d; background: #fbf1dc; }
QLabel#muted { color: #657571; }
QLabel#heroTitle { color: #1c2c29; font-size: 21pt; font-weight: 700; }
QLabel#sectionTitle { color: #243632; font-size: 11pt; font-weight: 650; }
QLabel#eyebrow { color: #687974; font-size: 9pt; font-weight: 600; }
QLabel#emptyState { color: #657571; background: #ffffff; border-radius: 10px; padding: 24px; }
QFrame[card="true"] { background: #ffffff; border: 1px solid #e0e7e3; border-radius: 11px; }
QFrame#workPane { background: #ffffff; border: 1px solid #dce5e1; border-radius: 11px; }
QFrame#sideStatus { background: #203c38; border: 1px solid #36534e; border-radius: 9px; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {
  color: #1d2927; background: #ffffff; border: 1px solid #cbd8d3; border-radius: 7px; padding: 8px 10px; selection-background-color: #28766c;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid #28766c; padding: 7px 9px; }
QComboBox { padding-right: 32px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: right center; width: 27px; border: none; background: transparent; }
QComboBox::down-arrow { image: none; width: 14px; height: 14px; }
QComboBox QAbstractItemView { color: #1d2927; background: #ffffff; border: 1px solid #cbd8d3; outline: 0; padding: 4px; selection-background-color: #dcefe9; selection-color: #1d5a52; }
QComboBox QAbstractItemView::item { min-height: 26px; padding: 6px 10px; color: #1d2927; border-radius: 5px; }
QComboBox QAbstractItemView::item:hover:!selected { color: #1d2927; background: #f1f6f3; }
QComboBox QAbstractItemView::item:selected { color: #1d5a52; background: #dcefe9; }
QMenu { color: #1d2927; background-color: #ffffff; border: 1px solid #cbd8d3; padding: 4px; }
QMenu::item { color: #1d2927; background: transparent; padding: 7px 26px; }
QMenu::item:selected { color: #1d5a52; background: #dcefe9; }
QMenu::item:disabled { color: #96a49f; }
QMenu::separator { height: 1px; background: #dce5e1; margin: 4px 8px; }
QPushButton { color: #2b3c38; background: #ffffff; border: 1px solid #cbd8d3; border-radius: 7px; padding: 8px 13px; font-weight: 600; }
QPushButton:hover { background: #f5f8f6; border-color: #9fb5ae; }
QPushButton:pressed { background: #eaf1ee; }
QPushButton:disabled { color: #96a49f; background: #f1f4f2; border-color: #e1e8e4; }
QPushButton#primaryButton { color: #ffffff; background: #28766c; border: 1px solid #28766c; }
QPushButton#primaryButton:hover { background: #205f57; }
QPushButton#dangerButton { color: #a03e40; background: #fffafa; border-color: #e7c6c4; }
QPushButton#primaryButton:disabled, QPushButton#dangerButton:disabled { color: #96a49f; background: #f1f4f2; border-color: #e1e8e4; }
QPushButton#quietButton { border: none; background: transparent; }
QListWidget { color: #2b3c38; background: #ffffff; border: 1px solid #dce5e1; border-radius: 8px; padding: 4px; }
QListWidget::item { padding: 10px; border-radius: 6px; }
QListWidget::item:selected { color: #1f5d55; background: #e7f1ed; }
QProgressBar { color: #2b3c38; background: #e5ece8; border: none; border-radius: 6px; height: 12px; text-align: center; }
QProgressBar::chunk { background: #28766c; border-radius: 6px; }
QCheckBox { color: #263632; spacing: 9px; padding: 2px 0; }
QCheckBox:disabled { color: #87958f; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #9aaea6; border-radius: 5px; background: #ffffff; }
QCheckBox::indicator:hover { border-color: #28766c; background: #f4f8f6; }
QCheckBox::indicator:focus { border: 2px solid #28766c; }
QCheckBox::indicator:checked { background: #28766c; border: 1px solid #28766c; }
QCheckBox::indicator:checked:hover { background: #205f57; border-color: #205f57; }
QCheckBox::indicator:disabled { background: #edf1ef; border-color: #cbd5d0; }
QMessageBox { color: #1d2927; background: #ffffff; }
QMessageBox QLabel { color: #1d2927; background: transparent; }
QMessageBox QPushButton { min-width: 82px; }
QMessageBox QPushButton#dangerButton { color: #a03e40; background: #fffafa; border-color: #e7c6c4; }
QScrollArea { border: none; }
QScrollBar:vertical { width: 9px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #b8c9c2; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

NUMERIC_INPUT_STYLE = """
QLineEdit { color: #1d2927; background: #ffffff; border: 1px solid #cbd8d3; border-radius: 7px; padding: 7px 10px; }
QLineEdit:focus { border: 2px solid #28766c; padding: 6px 9px; }
QLineEdit:disabled { color: #96a49f; background: #f1f4f2; border-color: #e1e8e4; }
"""


def _apply_app_style(widget: QWidget) -> None:
    widget.setStyleSheet(APP_STYLE)


def _style_message_box(dialog: QMessageBox) -> None:
    _apply_app_style(dialog)
    palette = dialog.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1d2927"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1d2927"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#2b3c38"))
    dialog.setPalette(palette)
    dialog.setMinimumWidth(420)


def _confirm_action(
    parent: QWidget,
    message: str,
    confirm_label: str,
    details: str = "",
) -> bool:
    dialog = QMessageBox(parent)
    dialog.setIcon(QMessageBox.Icon.Question)
    dialog.setWindowTitle(APP_NAME)
    dialog.setText(translate(message))
    if details:
        dialog.setInformativeText(translate(details))
    confirm_button = dialog.addButton(translate(confirm_label), QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = dialog.addButton(translate("Hủy"), QMessageBox.ButtonRole.RejectRole)
    dialog.setDefaultButton(cancel_button)
    dialog.setEscapeButton(cancel_button)
    _style_message_box(dialog)
    dialog.exec()
    return dialog.clickedButton() == confirm_button


def _style_combo_popup(combo: QComboBox) -> None:
    view = QListView(combo)
    view.setFrameShape(QFrame.Shape.NoFrame)
    view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    view.setUniformItemSizes(True)
    palette = view.palette()
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1d2927"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1d2927"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#dcefe9"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1d5a52"))
    view.setPalette(palette)
    view.setStyleSheet(
        "QListView { color:#1d2927; background:#ffffff; border:1px solid #cbd8d3; "
        "outline:0; padding:4px; } "
        "QListView::item { color:#1d2927; min-height:26px; padding:6px 10px; border-radius:5px; } "
        "QListView::item:hover:!selected { color:#1d2927; background:#f1f6f3; } "
        "QListView::item:selected { color:#1d5a52; background:#dcefe9; }"
    )
    combo.setView(view)
    combo.setMaxVisibleItems(5)


class AppCheckBox(QCheckBox):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.isChecked():
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)
        if rect.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffffff" if self.isEnabled() else "#e6f0ed"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath(QPointF(rect.left() + 4.1, rect.top() + 9.3))
        path.lineTo(QPointF(rect.left() + 7.2, rect.top() + 12.4))
        path.lineTo(QPointF(rect.left() + 14.0, rect.top() + 5.6))
        painter.drawPath(path)


class AppComboBox(QComboBox):
    def showPopup(self) -> None:
        view = self.view()
        view.setMinimumHeight(0)
        visible_rows = min(self.count(), self.maxVisibleItems())
        if visible_rows:
            row_height = max(view.sizeHintForRow(0), self.fontMetrics().height())
            # QComboBox sizes the popup before the stylesheet's item padding is included.
            view.setMinimumHeight(row_height * visible_rows + 10)
        super().showPopup()
        container = view.parentWidget()
        if not isinstance(container, QFrame):
            return
        container.setObjectName("languagePopupContainer")
        container.setFrameShape(QFrame.Shape.NoFrame)
        container.setLineWidth(0)
        container.setAutoFillBackground(True)
        palette = container.palette()
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
            palette.setColor(role, QColor("#ffffff"))
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
            palette.setColor(role, QColor("#1d2927"))
        container.setPalette(palette)
        container.setStyleSheet(
            "QFrame#languagePopupContainer { color:#1d2927; background:#ffffff; border:none; }"
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxArrow,
            self,
        )
        if rect.isEmpty():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#28766c" if self.hasFocus() else "#52645e")
        painter.setPen(QPen(color, 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        center = rect.center()
        path = QPainterPath(QPointF(center.x() - 3.3, center.y() - 1.2))
        path.lineTo(QPointF(center.x(), center.y() + 2.1))
        path.lineTo(QPointF(center.x() + 3.3, center.y() - 1.2))
        painter.drawPath(path)


def _card(title: str = "", description: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("card", True)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    if title:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
    if description:
        label = QLabel(description)
        label.setObjectName("muted")
        label.setWordWrap(True)
        layout.addWidget(label)
    return frame, layout


def _page_scroll(page: QWidget) -> QWidget:
    if page.property("selfScrolling") or page.property("stickyFooter"):
        return page
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    page.setObjectName("desktopPageContent")
    page.setMinimumWidth(0)
    page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    scroll.setWidget(page)
    return scroll


class HomePage(QWidget):
    translate_requested = Signal(str)
    models_requested = Signal()
    settings_requested = Signal()

    def __init__(self, settings: SettingsManager, model_registry: ModelRegistryManager) -> None:
        super().__init__()
        self.settings = settings
        self.model_registry = model_registry
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 24, 26, 20)
        outer.setSpacing(16)

        heading = QHBoxLayout()
        heading.setSpacing(18)
        title = QLabel("Dịch văn bản")
        title.setObjectName("heroTitle")
        heading.addWidget(title, 1)

        target_box = QVBoxLayout()
        target_box.setSpacing(5)
        target_label = QLabel("DỊCH SANG")
        target_label.setObjectName("eyebrow")
        self.target_combo = AppComboBox()
        _style_combo_popup(self.target_combo)
        self.target_combo.setMinimumWidth(174)
        self.target_combo.setAccessibleName("Ngôn ngữ đích")
        target_box.addWidget(target_label)
        target_box.addWidget(self.target_combo)
        heading.addLayout(target_box)
        outer.addLayout(heading)

        workspace = QHBoxLayout()
        workspace.setSpacing(14)

        source_frame = QFrame()
        source_frame.setObjectName("workPane")
        source_layout = QVBoxLayout(source_frame)
        source_layout.setContentsMargins(17, 15, 17, 15)
        source_layout.setSpacing(12)
        source_heading = QHBoxLayout()
        source_title = QLabel("Văn bản nguồn")
        source_title.setObjectName("sectionTitle")
        source_hint = QLabel("Tự nhận diện")
        source_hint.setObjectName("muted")
        source_heading.addWidget(source_title)
        source_heading.addStretch(1)
        source_heading.addWidget(source_hint)

        self.input = QPlainTextEdit()
        self.input.setObjectName("sourceInput")
        self.input.setPlaceholderText("Nhập hoặc dán văn bản cần dịch…")
        self.input.setMinimumHeight(230)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.input.setAccessibleName("Văn bản cần dịch")

        source_actions = QHBoxLayout()
        self.input_status = QLabel("Văn bản chỉ được xử lý trên máy.")
        self.input_status.setObjectName("muted")
        self.clear_button = QPushButton("Xóa")
        self.clear_button.setObjectName("quietButton")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_workspace)
        self.translate_button = QPushButton("Dịch văn bản")
        self.translate_button.setObjectName("primaryButton")
        self.translate_button.setEnabled(False)
        self.translate_button.clicked.connect(self._translate)
        source_actions.addWidget(self.input_status, 1)
        source_actions.addWidget(self.clear_button)
        source_actions.addWidget(self.translate_button)
        self.input.textChanged.connect(self._input_changed)
        source_layout.addLayout(source_heading)
        source_layout.addWidget(self.input, 1)
        source_layout.addLayout(source_actions)

        result_frame = QFrame()
        result_frame.setObjectName("workPane")
        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(17, 15, 17, 15)
        result_layout.setSpacing(12)
        result_heading = QHBoxLayout()
        result_title = QLabel("Bản dịch")
        result_title.setObjectName("sectionTitle")
        self.copy_button = QPushButton("Sao chép")
        self.copy_button.setObjectName("quietButton")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_result)
        result_heading.addWidget(result_title)
        result_heading.addStretch(1)
        result_heading.addWidget(self.copy_button)

        self.output = QTextEdit()
        self.output.setObjectName("translationOutput")
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Bản dịch sẽ xuất hiện ở đây.")
        self.output.setMinimumHeight(230)
        self.output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.output.setAccessibleName("Kết quả dịch")
        self.output_status = QLabel("" )
        self.output_status.setObjectName("muted")
        result_layout.addLayout(result_heading)
        result_layout.addWidget(self.output, 1)
        result_layout.addWidget(self.output_status)
        workspace.addWidget(source_frame, 1)
        workspace.addWidget(result_frame, 1)
        outer.addLayout(workspace, 1)

        self.quick_start_card, quick_start_layout = _card("Bắt đầu nhanh")
        self.quick_start_instructions = QLabel(
            "1. Tải mô hình cần dùng ở trang Mô hình. Mô hình được lưu trên máy; sau đó bạn có thể dịch ngoại tuyến.\n"
            "2. Bôi đen văn bản ở ứng dụng khác rồi giữ chuột 2 giây, hoặc nhấn Ctrl+C hai lần.\n"
            "3. Bạn cũng có thể dán văn bản vào ô bên trái. Nhấn Ctrl+V hai lần để mở lịch sử."
        )
        self.quick_start_instructions.setObjectName("muted")
        self.quick_start_instructions.setWordWrap(True)
        quick_start_layout.addWidget(self.quick_start_instructions)

        footer = QHBoxLayout()
        self.models_status = QLabel("")
        self.models_status.setObjectName("muted")
        self.install_models_button = QPushButton("Cài mô hình")
        self.install_models_button.setObjectName("primaryButton")
        self.install_models_button.clicked.connect(self.models_requested.emit)
        self.settings_button = QPushButton("Chọn nơi lưu")
        self.settings_button.setObjectName("quietButton")
        self.settings_button.clicked.connect(self.settings_requested.emit)
        footer.addWidget(self.models_status, 1)
        footer.addWidget(self.settings_button)
        footer.addWidget(self.install_models_button)
        quick_start_layout.addLayout(footer)
        outer.insertWidget(1, self.quick_start_card)

        self._ready = False
        self.target_combo.currentIndexChanged.connect(self._target_changed)
        self.refresh_details()

    def refresh_details(self) -> None:
        installed = self.model_registry.get_installed_models()
        installed_directions = [
            package for package in self.model_registry.get_available_packages() if package.is_installed
        ]
        installed_targets = {model.to_lang for model in installed_directions}
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for label, code in TARGETS:
            if code in installed_targets:
                self.target_combo.addItem(translate(label), code)
        if self.target_combo.count():
            index = self.target_combo.findData(self.settings.config.target_lang)
            if index < 0:
                index = 0
                self.settings.update(target_lang=self.target_combo.itemData(index))
            self.target_combo.setCurrentIndex(index)
            self.target_combo.setEnabled(True)
        else:
            self.target_combo.addItem(translate("Chưa có mô hình đã cài"), None)
            self.target_combo.setEnabled(False)
        self.target_combo.blockSignals(False)
        if installed:
            self.quick_start_card.hide()
            self.models_status.hide()
            self.install_models_button.hide()
        else:
            self.models_status.setText(translate("Chưa có mô hình. Cài một lần để bắt đầu dịch ngoại tuyến."))
            self.quick_start_card.show()
            self.models_status.show()
            self.install_models_button.show()
        localize_widgets(self)

    def _target_changed(self) -> None:
        target_lang = self.target_combo.currentData()
        if target_lang and target_lang != self.settings.config.target_lang:
            self.settings.update(target_lang=target_lang)

    def _input_changed(self) -> None:
        has_text = bool(self.input.toPlainText().strip())
        self.translate_button.setEnabled(self._ready and has_text)
        self.clear_button.setEnabled(has_text or bool(self.output.toPlainText()))
        if self.output.toPlainText():
            self.output.clear()
            self.output_status.clear()
            self.copy_button.setEnabled(False)

    def _copy_result(self) -> None:
        text = self.output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.output_status.setText(translate("Đã sao chép bản dịch."))

    def clear_workspace(self) -> None:
        self.input.clear()
        self.output.clear()
        self.output_status.clear()
        self.copy_button.setEnabled(False)
        self.clear_button.setEnabled(False)

    def _translate(self) -> None:
        text = self.input.toPlainText().strip()
        if text:
            self.output.clear()
            self.copy_button.setEnabled(False)
            self.output_status.setText(translate("Đang dịch…"))
            self.translate_button.setEnabled(False)
            self.translate_requested.emit(text)

    def set_kernel_status(self, message: str, ready: bool) -> None:
        self._ready = ready
        self.input_status.setText(translate("Lõi sẵn sàng · văn bản được xử lý trên máy") if ready else translate(message))
        self.translate_button.setEnabled(ready and bool(self.input.toPlainText().strip()))

    def show_result(self, translated_text: str, error: str = "") -> None:
        self.output.setPlainText(translate(error) if error else translated_text or translate("Không có bản dịch."))
        self.output_status.setText(translate(error) if error else (translate("Dịch xong.") if translated_text else ""))
        self.copy_button.setEnabled(bool(translated_text and not error))
        self.clear_button.setEnabled(bool(self.input.toPlainText().strip() or translated_text or error))
        self.translate_button.setEnabled(self._ready and bool(self.input.toPlainText().strip()))


class HistoryPage(QWidget):
    def __init__(self, history: HistoryManager) -> None:
        super().__init__()
        self.setObjectName("desktopPageContent")
        self.setProperty("selfScrolling", True)
        self.history = history
        self.list_layout: Optional[QVBoxLayout] = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 28)
        outer.setSpacing(16)
        header = QHBoxLayout()
        title = QLabel("Lịch sử dịch")
        title.setObjectName("heroTitle")
        self.count = QLabel("")
        self.count.setObjectName("muted")
        self.clear_button = QPushButton("Xóa lịch sử")
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.clicked.connect(self._clear)
        header.addWidget(title)
        header.addWidget(self.count)
        header.addStretch(1)
        header.addWidget(self.clear_button)
        outer.addLayout(header)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("desktopPageContent")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.scroll_content)
        outer.addWidget(scroll, 1)
        self.refresh()

    def refresh(self) -> None:
        assert self.list_layout is not None
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        entries = self.history.get_items()
        count_unit = "mục" if ui_language() == "vi" else ("item" if len(entries) == 1 else "items")
        self.count.setText(f"{len(entries)} {count_unit}")
        self.clear_button.setEnabled(bool(entries))
        if not entries:
            empty = QLabel(
                f"{translate('Chưa có bản dịch nào')}\n"
                f"{translate('Bản dịch mới sẽ xuất hiện tại đây khi bật lưu lịch sử.')}"
            )
            empty.setObjectName("emptyState")
            empty.setWordWrap(True)
            self.list_layout.addWidget(empty)
        for entry in entries:
            frame, layout = _card()
            heading = QHBoxLayout()
            route = QLabel(f"{entry.src_lang.upper()}  →  {entry.tgt_lang.upper()}")
            route.setObjectName("sectionTitle")
            timestamp = QLabel(entry.timestamp)
            timestamp.setObjectName("muted")
            heading.addWidget(route)
            heading.addStretch(1)
            heading.addWidget(timestamp)
            source_label = QLabel("Văn bản gốc")
            source_label.setObjectName("eyebrow")
            source = QLabel(entry.source_text)
            source.setObjectName("historyContentText")
            source.setObjectName("muted")
            source.setWordWrap(True)
            target_label = QLabel("Bản dịch")
            target_label.setObjectName("eyebrow")
            target = QLabel(entry.translated_text)
            target.setObjectName("historyContentText")
            target.setWordWrap(True)
            target.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            copy_button = QPushButton("Sao chép bản dịch")
            copy_button.clicked.connect(lambda _checked=False, text=entry.translated_text: QApplication.clipboard().setText(text))
            layout.addLayout(heading)
            layout.addWidget(source_label)
            layout.addWidget(source)
            layout.addWidget(target_label)
            layout.addWidget(target)
            layout.addWidget(copy_button, 0, Qt.AlignmentFlag.AlignRight)
            self.list_layout.addWidget(frame)
        self.list_layout.addStretch(1)
        localize_widgets(self)

    def _clear(self) -> None:
        confirmed = _confirm_action(
            self,
            "Xóa các bản dịch đã lưu trên máy?",
            "Xóa lịch sử",
            "Bạn có thể hoàn tác ngay sau khi xóa.",
        )
        if not confirmed:
            return

        items = self.history.get_items()
        self.history.clear()
        self.refresh()
        if not items:
            return

        notice = QMessageBox(self)
        notice.setIcon(QMessageBox.Icon.Information)
        notice.setWindowTitle(translate("Lịch sử đã được xóa"))
        notice.setText(f"{translate('Đã xóa ')}{len(items)}{translate(' bản dịch.')}")
        undo_button = notice.addButton(translate("Hoàn tác"), QMessageBox.ButtonRole.ActionRole)
        notice.addButton(translate("Đóng"), QMessageBox.ButtonRole.AcceptRole)
        _style_message_box(notice)
        notice.exec()
        if notice.clickedButton() == undo_button:
            self.history.restore_items([*self.history.get_items(), *items])
            self.refresh()


def _normalize_model_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold().replace("đ", "d")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(re.sub(r"[\W_]+", " ", normalized).split())


class ModelPage(QWidget):
    def __init__(self, manager: ModelRegistryManager) -> None:
        super().__init__()
        self.manager = manager
        self.packages: list[ModelPackageInfo] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 28)
        outer.setSpacing(15)
        title = QLabel("Mô hình ngôn ngữ")
        title.setObjectName("heroTitle")
        outer.addWidget(title)

        card, layout = _card()
        columns = QHBoxLayout()
        columns.setSpacing(18)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm hướng dịch")
        self.search.setAccessibleName("Tìm mô hình")
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        self.list.setMinimumHeight(300)
        self.list.currentRowChanged.connect(self._selection_changed)
        self.search.textChanged.connect(self.refresh)
        details = QVBoxLayout()
        self.detail_title = QLabel("Chọn một mô hình")
        self.detail_title.setObjectName("sectionTitle")
        self.detail_text = QLabel("")
        self.detail_text.setWordWrap(True)
        self.detail_text.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        self.download_button = QPushButton("Tải mô hình")
        self.download_button.setObjectName("primaryButton")
        self.download_button.clicked.connect(self._download)
        self.delete_button = QPushButton("Gỡ mô hình")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self._delete)
        self.folder_button = QPushButton("Mở thư mục dữ liệu")
        self.folder_button.clicked.connect(self._open_folder)
        self.operation_status = QLabel("")
        self.operation_status.setWordWrap(True)
        self.operation_status.setObjectName("muted")
        details.addWidget(self.detail_title)
        details.addWidget(self.detail_text)
        details.addWidget(self.progress)
        details.addWidget(self.operation_status)
        details.addWidget(self.download_button, 0, Qt.AlignmentFlag.AlignLeft)
        details.addWidget(self.delete_button, 0, Qt.AlignmentFlag.AlignLeft)
        details.addStretch(1)
        details.addWidget(self.folder_button, 0, Qt.AlignmentFlag.AlignLeft)
        columns.addWidget(self.list, 1)
        columns.addLayout(details, 1)
        layout.addWidget(self.search)
        layout.addLayout(columns)
        outer.addWidget(card, 1)
        self.refresh()

    def refresh(self, *_args) -> None:
        current_pair = self._selected_pair()
        self.packages = self.manager.get_available_packages()
        query = _normalize_model_search_text(self.search.text())
        query_terms = query.split()
        visible = [
            package for package in self.packages
            if not query_terms or all(
                term in _normalize_model_search_text(" ".join((
                    package.pair,
                    package.from_name,
                    package.to_name,
                    package.from_display_name,
                    package.to_display_name,
                    package.display_name,
                    f"{package.from_display_name} → {package.to_display_name}",
                    f"{package.from_lang} → {package.to_lang}",
                )))
                for term in query_terms
            )
        ]
        visible.sort(key=lambda package: not package.is_installed)
        self.list.blockSignals(True)
        self.list.clear()
        selected_row = -1
        for package in visible:
            size = package.installed_size_mb if package.is_installed else package.download_size_mb
            if package.underlying_pair:
                status = translate("✓ SẴN SÀNG") if package.is_installed else f"{translate('Có thể tải')}  ·  {size:.1f} MB"
            else:
                status = f"{translate('✓ ĐÃ CÀI')}  ·  {size:.1f} MB" if package.is_installed else f"{translate('Có thể tải')}  ·  {size:.1f} MB"
            route = translate(f"{package.from_display_name} → {package.to_display_name}")
            route_codes = f"{package.from_lang.upper()} → {package.to_lang.upper()}"
            item = QListWidgetItem(f"{route}\n{route_codes}\n{status}")
            item.setSizeHint(QSize(300, 82))
            if package.is_installed:
                font = item.font()
                font.setWeight(QFont.Weight.DemiBold)
                item.setFont(font)
                item.setForeground(QColor("#1f5d55"))
            item.setData(Qt.ItemDataRole.UserRole, package.pair)
            self.list.addItem(item)
            if package.pair == current_pair:
                selected_row = self.list.count() - 1
        if self.list.count():
            self.list.setCurrentRow(max(0, selected_row))
        self.list.blockSignals(False)
        self._selection_changed(self.list.currentRow())

    def _selected_pair(self) -> str:
        item = self.list.currentItem() if hasattr(self, "list") else None
        return str(item.data(Qt.ItemDataRole.UserRole)) if item else ""

    def _selected_package(self) -> Optional[ModelPackageInfo]:
        pair = self._selected_pair()
        return next((package for package in self.packages if package.pair == pair), None)

    def _selection_changed(self, _row: int) -> None:
        package = self._selected_package()
        self.download_button.setVisible(bool(package and not package.is_installed))
        self.delete_button.setVisible(bool(package and package.is_installed and not package.underlying_pair))
        if package is None:
            self.detail_title.setText(translate("Chưa có mô hình phù hợp"))
            self.detail_text.clear()
            return
        self.detail_title.setText(translate(f"{package.from_display_name} → {package.to_display_name}"))
        route_codes = f"{package.from_lang.upper()} → {package.to_lang.upper()}"
        if package.underlying_pair:
            status = translate("Sẵn sàng" if package.is_installed else "Chưa cài")
            self.detail_text.setText(f"{route_codes}\n{status}")
            return
        size = package.installed_size_mb if package.is_installed else package.download_size_mb
        size_label = f"{size:.1f} {translate('MB trên đĩa')}" if package.is_installed else f"{translate('Tải xuống khoảng ')}{size:.1f} MB"
        status = translate("Đã cài" if package.is_installed else "Chưa cài")
        self.detail_text.setText(f"{route_codes}\n{status}  ·  {size_label}")

    def _download(self) -> None:
        package = self._selected_package()
        if not package:
            return
        self.download_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.operation_status.setText(translate("Đang tải mô hình…"))

        from PySide6.QtCore import QObject

        class DownloadEvents(QObject):
            progress = Signal(str, float)
            complete = Signal(str)
            error = Signal(str, str)

        events = DownloadEvents(self)
        events.progress.connect(self._download_progress)
        events.complete.connect(self._download_complete)
        events.error.connect(self._download_error)
        self._download_events = events
        self.manager.download_model(
            package.pair,
            on_progress=events.progress.emit,
            on_complete=events.complete.emit,
            on_error=events.error.emit,
        )

    def _download_progress(self, message: str, progress: float) -> None:
        self.progress.setValue(max(0, min(100, round(progress * 100))))
        self.operation_status.setText(message)

    def _download_complete(self, pair: str) -> None:
        self.download_button.setEnabled(True)
        self.progress.hide()
        self.operation_status.setText(f"{translate('Đã cài ')}{translate('mô hình')} {pair.upper()}.")
        self.refresh()

    def _download_error(self, pair: str, error: str) -> None:
        self.download_button.setEnabled(True)
        self.progress.hide()
        self.operation_status.setText(f"{translate('Không thể tải ')}{pair.upper()}: {error}")

    def _delete(self) -> None:
        package = self._selected_package()
        if not package or package.underlying_pair:
            return
        confirmed = _confirm_action(
            self,
            f"{translate('Gỡ mô hình ')}{package.pair.upper()}{translate(' khỏi máy?')}",
            translate("Gỡ mô hình"),
            translate("Bạn có thể tải lại sau."),
        )
        if not confirmed:
            return
        ok, message = self.manager.delete_model(package.pair)
        self.operation_status.setText(message)
        self.refresh()

    def _open_folder(self) -> None:
        self.manager.models_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.models_dir)))


class SettingsPage(QWidget):
    saved = Signal(object)
    uninstall_requested = Signal()
    restart_requested = Signal()
    update_check_complete = Signal(object)
    update_check_failed = Signal()
    update_download_complete = Signal(str)
    update_download_failed = Signal(str)
    update_download_progress = Signal(int, int)
    update_install_requested = Signal(str)

    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.setObjectName("desktopPageContent")
        self.setProperty("stickyFooter", True)
        self.settings = settings
        self.startup = StartupManager()
        self._loading = False
        self._saved_values: dict[str, object] = {}
        self._startup_registered = False
        self._latest_update: UpdateCheckResult | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QWidget()
        body.setObjectName("desktopPageContent")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(26, 24, 26, 20)
        body_layout.setSpacing(14)
        title = QLabel("Cài đặt")
        title.setObjectName("heroTitle")
        body_layout.addWidget(title)

        language_card, language_layout = _card("Ngôn ngữ giao diện")
        self.ui_language = AppComboBox()
        self.ui_language.addItem("Tiếng Việt", "vi")
        self.ui_language.addItem("English", "en")
        _style_combo_popup(self.ui_language)
        self._form_row(language_layout, "Ngôn ngữ giao diện", self.ui_language)
        body_layout.addWidget(language_card)

        behavior, behavior_layout = _card("Cách dịch", "Chọn hành vi khi thao tác trên ứng dụng khác.")
        self.auto_drag = AppCheckBox("Giữ chuột để dịch")
        self.hold_duration = QDoubleSpinBox()
        self.hold_duration.setRange(0.1, 10)
        self.hold_duration.setSingleStep(0.1)
        self.hold_duration.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.hold_duration.setFrame(False)
        self.hold_duration.setFixedSize(96, 38)
        self.hold_duration.lineEdit().setStyleSheet(NUMERIC_INPUT_STYLE)
        self.hold_duration_unit = QLabel("giây")
        self.hold_duration_unit.setObjectName("muted")
        self.double_ctrl_c = AppCheckBox("Nhấn Ctrl + C hai lần để dịch")
        self.double_ctrl_v = AppCheckBox("Nhấn Ctrl + V hai lần để mở lịch sử")
        self.auto_close_enabled = AppCheckBox("Tự đóng thẻ dịch")
        self.auto_close_delay = QSpinBox()
        self.auto_close_delay.setRange(1, 120)
        self.auto_close_delay.setValue(15)
        self.auto_close_delay.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.auto_close_delay.setFrame(False)
        self.auto_close_delay.setFixedSize(96, 38)
        self.auto_close_delay.lineEdit().setStyleSheet(NUMERIC_INPUT_STYLE)
        self.auto_close_delay_unit = QLabel("giây")
        self.auto_close_delay_unit.setObjectName("muted")
        self._form_row(behavior_layout, "Kéo chọn", self.auto_drag)
        self._form_row(
            behavior_layout,
            "Thời gian giữ",
            self._with_unit(self.hold_duration, self.hold_duration_unit),
        )
        self._form_row(behavior_layout, "Phím tắt", self.double_ctrl_c)
        self._form_row(behavior_layout, "Lịch sử nhanh", self.double_ctrl_v)
        self._form_row(behavior_layout, "Thẻ dịch", self.auto_close_enabled)
        self._form_row(
            behavior_layout,
            "Đóng sau",
            self._with_unit(self.auto_close_delay, self.auto_close_delay_unit),
        )
        body_layout.addWidget(behavior)

        privacy, privacy_layout = _card(
            "Quyền riêng tư",
            "Văn bản, lịch sử và nhật ký được lưu cục bộ. Lịch sử không tự xóa và có thể tắt bất cứ lúc nào.",
        )
        self.save_history = AppCheckBox("Lưu toàn bộ lịch sử bản dịch trên máy")
        privacy_layout.addWidget(self.save_history)
        body_layout.addWidget(privacy)

        startup_card, startup_layout = _card("Khởi động cùng Windows")
        self.start_on_boot = AppCheckBox("Mở re/read khi đăng nhập Windows (chạy nền)")
        self.startup_status = QLabel("")
        self.startup_status.setObjectName("muted")
        startup_layout.addWidget(self.start_on_boot)
        startup_layout.addWidget(self.startup_status)
        body_layout.addWidget(startup_card)

        storage, storage_layout = _card("Dữ liệu ứng dụng")
        self.data_path = QLabel(str(database_path()))
        self.data_path.setObjectName("dataPath")
        self.data_path.setWordWrap(True)
        self.data_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        open_data = QPushButton("Mở thư mục dữ liệu")
        open_data.clicked.connect(self._open_data_dir)
        storage_layout.addWidget(self.data_path)
        storage_layout.addWidget(open_data, 0, Qt.AlignmentFlag.AlignLeft)

        self.model_directory = QLineEdit()
        self.model_directory.setReadOnly(True)
        self.model_directory.setAccessibleName("Thư mục lưu mô hình")
        self.choose_model_directory_button = QPushButton("Chọn thư mục…")
        self.choose_model_directory_button.clicked.connect(self._choose_model_directory)
        model_directory_row = QWidget()
        model_directory_layout = QHBoxLayout(model_directory_row)
        model_directory_layout.setContentsMargins(0, 0, 0, 0)
        model_directory_layout.addWidget(self.model_directory, 1)
        model_directory_layout.addWidget(self.choose_model_directory_button)
        self._form_row(storage_layout, "Thư mục mô hình", model_directory_row)
        self.model_directory_hint = QLabel(
            "Model tải về được lưu trong thư mục này. Đổi vị trí có hiệu lực sau khi mở lại app; chọn thư mục cũ để dùng lại model đã tải."
        )
        self.model_directory_hint.setObjectName("muted")
        self.model_directory_hint.setWordWrap(True)
        storage_layout.addWidget(self.model_directory_hint)
        body_layout.addWidget(storage)

        updates, updates_layout = _card(
            "Cập nhật ứng dụng",
            "Kiểm tra bản phát hành ổn định trên GitHub. Khi có bản mới, chọn Cập nhật ngay để tải và cài đặt.",
        )
        self.version_label = QLabel(f"{translate('Phiên bản')}: v{__version__}")
        self.update_status = QLabel("Chưa kiểm tra cập nhật.")
        self.update_status.setObjectName("muted")
        self.update_status.setWordWrap(True)
        update_actions = QHBoxLayout()
        self.check_update_button = QPushButton("Kiểm tra cập nhật")
        self.check_update_button.setObjectName("primaryButton")
        self.check_update_button.clicked.connect(self._on_update_action)
        self.open_release_button = QPushButton("Xem bản phát hành trên GitHub")
        self.open_release_button.hide()
        self.open_release_button.clicked.connect(self._open_latest_release)
        update_actions.addWidget(self.check_update_button)
        update_actions.addWidget(self.open_release_button)
        update_actions.addStretch(1)
        updates_layout.addWidget(self.version_label)
        updates_layout.addWidget(self.update_status)
        updates_layout.addLayout(update_actions)
        body_layout.addWidget(updates)

        uninstall, uninstall_layout = _card(
            "Gỡ cài đặt re/read",
            "Gỡ ứng dụng cùng lịch sử, cài đặt và toàn bộ mô hình đã tải.",
        )
        self.uninstall_button = QPushButton("Gỡ cài đặt")
        self.uninstall_button.setObjectName("dangerButton")
        self.uninstall_button.clicked.connect(self._request_uninstall)
        uninstall_layout.addWidget(self.uninstall_button, 0, Qt.AlignmentFlag.AlignLeft)
        body_layout.addWidget(uninstall)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("settingsFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 11, 24, 11)
        self.dirty_status = QLabel("Mọi thay đổi đã được lưu")
        self.dirty_status.setObjectName("dirtyStatus")
        self.feedback = QLabel("")
        self.feedback.setObjectName("muted")
        self.restart_button = QPushButton("Khởi động lại")
        self.restart_button.setObjectName("quietButton")
        self.restart_button.setToolTip(translate("Lưu thay đổi rồi khởi động lại ứng dụng và dịch vụ."))
        self.restart_button.clicked.connect(self._request_restart)
        self.undo_button = QPushButton("Hoàn tác")
        self.undo_button.setObjectName("quietButton")
        self.undo_button.clicked.connect(self._undo)
        self.save_button = QPushButton("Lưu thay đổi")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save)
        footer_layout.addWidget(self.dirty_status, 1)
        footer_layout.addWidget(self.feedback)
        footer_layout.addWidget(self.restart_button)
        footer_layout.addWidget(self.undo_button)
        footer_layout.addWidget(self.save_button)
        outer.addWidget(footer)

        for signal in (
            self.auto_drag.toggled,
            self.hold_duration.valueChanged,
            self.double_ctrl_c.toggled,
            self.double_ctrl_v.toggled,
            self.auto_close_enabled.toggled,
            self.auto_close_delay.valueChanged,
            self.save_history.toggled,
            self.start_on_boot.toggled,
            self.ui_language.currentIndexChanged,
        ):
            signal.connect(self._update_dirty_state)
        self.auto_close_enabled.toggled.connect(self.auto_close_delay.setEnabled)
        self.start_on_boot.toggled.connect(self._refresh_startup_status)
        self.update_check_complete.connect(self._show_update_result)
        self.update_check_failed.connect(self._show_update_error)
        self.update_download_complete.connect(self._on_update_downloaded)
        self.update_download_failed.connect(self._show_download_error)
        self.update_download_progress.connect(self._show_download_progress)
        self.load()

    def _on_update_action(self) -> None:
        if self._latest_update is not None:
            self._download_update(self._latest_update)
        else:
            self._check_for_updates()

    def _check_for_updates(self) -> None:
        self.check_update_button.setEnabled(False)
        self.update_status.setText(translate("Đang kiểm tra cập nhật…"))

        def check() -> None:
            try:
                self.update_check_complete.emit(check_for_update(__version__))
            except Exception:
                self.update_check_failed.emit()

        threading.Thread(target=check, name="reread-update-check", daemon=True).start()

    def _show_update_result(self, result: UpdateCheckResult) -> None:
        self.check_update_button.setEnabled(True)
        self._latest_update = result if result.update_available else None
        self.check_update_button.setText(
            translate("Cập nhật ngay") if result.update_available else translate("Kiểm tra cập nhật")
        )
        self._latest_release_url = result.release_url if result.update_available else ""
        self.open_release_button.setVisible(result.update_available)
        if result.update_available:
            self.update_status.setText(f"{translate('Có phiên bản mới: ')}v{result.latest_version}")
        else:
            self.update_status.setText(f"{translate('Bạn đang dùng phiên bản mới nhất.')} (v{__version__})")

    def _download_update(self, result: UpdateCheckResult) -> None:
        self.check_update_button.setEnabled(False)
        self.update_status.setText(translate("Đang tải và xác minh bản cập nhật…"))

        def download() -> None:
            try:
                installer = download_installer(
                    result,
                    progress=lambda received, total: self.update_download_progress.emit(received, total),
                )
                self.update_download_complete.emit(str(installer))
            except Exception as exc:
                self.update_download_failed.emit(str(exc))

        threading.Thread(target=download, name="reread-update-download", daemon=True).start()

    def _show_download_progress(self, received: int, total: int) -> None:
        percentage = min(100, received * 100 // max(1, total))
        self.update_status.setText(
            f"{translate('Đang tải và xác minh bản cập nhật…')} {percentage}%"
        )

    def _on_update_downloaded(self, installer_path: str) -> None:
        self.update_status.setText(translate("Đang cài đặt cập nhật và khởi động lại ứng dụng…"))
        self.update_install_requested.emit(installer_path)

    def _show_download_error(self, message: str) -> None:
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText(translate("Cập nhật ngay"))
        self.update_status.setText(
            f"{translate('Không thể tải hoặc xác minh bản cập nhật: ')}{message}"
        )

    def show_update_install_error(self, message: str) -> None:
        self.check_update_button.setEnabled(True)
        self.update_status.setText(f"{translate('Không thể chạy bộ cài cập nhật: ')}{message}")

    def _show_update_error(self) -> None:
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText(translate("Kiểm tra cập nhật"))
        self._latest_update = None
        self.open_release_button.hide()
        self.update_status.setText(translate("Không thể kiểm tra cập nhật. Hãy kiểm tra kết nối mạng rồi thử lại."))

    def _open_latest_release(self) -> None:
        if getattr(self, "_latest_release_url", ""):
            QDesktopServices.openUrl(QUrl(self._latest_release_url))

    @staticmethod
    def _form_row(layout: QVBoxLayout, label_text: str, control: QWidget) -> None:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setMinimumWidth(180)
        label.setWordWrap(True)
        row.addWidget(label)
        row.addWidget(control, 1)
        layout.addLayout(row)

    @staticmethod
    def _with_unit(control: QWidget, unit: QLabel) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(control)
        row.addWidget(unit)
        row.addStretch(1)
        return wrapper

    def load(self) -> None:
        self._loading = True
        cfg = self.settings.config
        self.auto_drag.setChecked(cfg.auto_drag)
        self.hold_duration.setValue(cfg.hold_duration_seconds)
        self.double_ctrl_c.setChecked(cfg.double_ctrl_c)
        self.double_ctrl_v.setChecked(cfg.double_ctrl_v_history)
        self.auto_close_enabled.setChecked(cfg.auto_close_seconds > 0)
        self.auto_close_delay.setValue(cfg.auto_close_seconds or 15)
        self.auto_close_delay.setEnabled(self.auto_close_enabled.isChecked())
        self.save_history.setChecked(cfg.enable_history)
        self.start_on_boot.setChecked(cfg.start_on_boot)
        language_index = self.ui_language.findData(cfg.ui_language)
        self.ui_language.setCurrentIndex(max(0, language_index))
        self.model_directory.setText(str(models_dir(cfg.model_directory)))
        self._startup_registered, _name, _command = self.startup.is_registered()
        self._refresh_startup_status()
        self._saved_values = self._form_values()
        self._loading = False
        self.feedback.clear()
        self._update_dirty_state()
        localize_widgets(self)

    @property
    def is_dirty(self) -> bool:
        return bool(self._saved_values) and self._form_values() != self._saved_values

    def _form_values(self) -> dict[str, object]:
        return {
            "auto_drag": self.auto_drag.isChecked(),
            "hold_duration_seconds": self.hold_duration.value(),
            "double_ctrl_c": self.double_ctrl_c.isChecked(),
            "double_ctrl_v_history": self.double_ctrl_v.isChecked(),
            "auto_close_seconds": self.auto_close_delay.value() if self.auto_close_enabled.isChecked() else 0,
            "enable_history": self.save_history.isChecked(),
            "start_on_boot": self.start_on_boot.isChecked(),
            "ui_language": str(self.ui_language.currentData()),
            "model_directory": self.model_directory.text().strip(),
        }

    def _update_dirty_state(self, *_args) -> None:
        if self._loading:
            return
        dirty = self.is_dirty
        self.dirty_status.setText(translate("Có thay đổi chưa lưu" if dirty else "Mọi thay đổi đã được lưu"))
        self.dirty_status.setProperty("dirty", dirty)
        self.dirty_status.style().unpolish(self.dirty_status)
        self.dirty_status.style().polish(self.dirty_status)
        self.save_button.setEnabled(dirty)
        self.undo_button.setEnabled(dirty)
        self.restart_button.setEnabled(True)
        if dirty:
            self.feedback.clear()

    def _refresh_startup_status(self, *_args) -> None:
        wants_startup = self.start_on_boot.isChecked()
        if wants_startup and not self._startup_registered:
            text = translate("Lưu thay đổi sẽ đăng ký chạy nền khi đăng nhập Windows.")
        elif not wants_startup and self._startup_registered:
            text = translate("Lưu thay đổi sẽ gỡ mục tự khởi động của re/read.")
        elif self._startup_registered:
            text = translate("Đã đăng ký khởi động cùng Windows.")
        else:
            text = translate("Ứng dụng không tự chạy khi đăng nhập Windows.")
        self.startup_status.setText(text)

    def _undo(self) -> None:
        self.load()
        self.feedback.setText(translate("Đã hoàn tác thay đổi."))

    def _request_restart(self) -> None:
        if self.is_dirty and not self._save():
            return
        self.restart_requested.emit()

    def _save(self) -> bool:
        model_directory = models_dir(self.model_directory.text().strip()).resolve()
        current_model_directory = models_dir(self.settings.config.model_directory).resolve()
        model_directory_changed = model_directory != current_model_directory
        language_changed = str(self.ui_language.currentData()) != self.settings.config.ui_language
        try:
            if model_directory.exists() and not model_directory.is_dir():
                raise NotADirectoryError(str(model_directory))
            model_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            warning = QMessageBox(self)
            warning.setIcon(QMessageBox.Icon.Warning)
            warning.setWindowTitle(translate("Không thể dùng thư mục mô hình"))
            warning.setText(f"{translate('Không thể tạo hoặc mở thư mục đã chọn: ')}{exc}")
            warning.addButton(translate("Đóng"), QMessageBox.ButtonRole.AcceptRole)
            _style_message_box(warning)
            warning.exec()
            return False

        wants_startup = self.start_on_boot.isChecked()
        registered, _name, _command = self.startup.is_registered()
        startup_ok = True
        startup_message = ""
        if wants_startup and not registered:
            startup_ok, startup_message = self.startup.register()
        elif not wants_startup and registered:
            startup_ok, startup_message, _count = self.startup.clear_keys()
        if not startup_ok:
            warning = QMessageBox(self)
            warning.setIcon(QMessageBox.Icon.Warning)
            warning.setWindowTitle(translate("Không thể cập nhật khởi động"))
            warning.setText(startup_message)
            warning.addButton(translate("Đóng"), QMessageBox.ButtonRole.AcceptRole)
            _style_message_box(warning)
            warning.exec()
            self.start_on_boot.setChecked(self.settings.config.start_on_boot)
            return False

        values = self._form_values()
        values["model_directory"] = str(model_directory)
        if not self.settings.update(**values):
            self.feedback.setText(translate("Không thể lưu cài đặt. Kiểm tra quyền ghi vào thư mục dữ liệu."))
            return False
        self.saved.emit(self.settings.config)
        self.load()
        if language_changed:
            message = translate("Khởi động lại ứng dụng để áp dụng ngôn ngữ mới.", str(values["ui_language"]))
        elif not wants_startup and registered:
            message = translate("Đã tắt khởi động và gỡ mục đăng ký của re/read.")
        elif wants_startup and not registered:
            message = translate("Đã bật khởi động cùng Windows.")
        else:
            message = translate("Đã lưu cài đặt.")
        if model_directory_changed:
            message += translate(" Mở lại ứng dụng để dùng thư mục mô hình mới.")
        self.feedback.setText(message)
        return True

    def _choose_model_directory(self) -> None:
        current = Path(self.model_directory.text()).expanduser()
        start_directory = current if current.is_dir() else current.parent
        selected = QFileDialog.getExistingDirectory(
            self,
            translate("Chọn thư mục lưu mô hình"),
            str(start_directory),
        )
        if selected:
            self.model_directory.setText(selected)
            self._update_dirty_state()

    def _open_data_dir(self) -> None:
        app_data_dir().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_data_dir())))

    def _request_uninstall(self) -> None:
        if self.is_dirty:
            self.feedback.setText(translate("Lưu cài đặt trước khi gỡ ứng dụng."))
            return
        if _confirm_action(
            self,
            "Gỡ cài đặt re/read khỏi máy tính?",
            "Gỡ cài đặt",
            "Toàn bộ ứng dụng, lịch sử, cài đặt và mô hình đã tải sẽ bị xóa.",
        ):
            self.uninstall_requested.emit()


class ActivityPage(QWidget):
    def __init__(self, logger: AppLogger) -> None:
        super().__init__()
        self.setObjectName("desktopPageContent")
        self.setProperty("selfScrolling", True)
        self.logger = logger
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 28)
        outer.setSpacing(14)
        header = QHBoxLayout()
        title = QLabel("Nhật ký hoạt động")
        title.setObjectName("heroTitle")
        header.addWidget(title)
        header.addStretch(1)
        copy_button = QPushButton("Sao chép")
        clear_button = QPushButton("Xóa nhật ký")
        header.addWidget(copy_button)
        header.addWidget(clear_button)
        outer.addLayout(header)
        log_hint = QLabel("Lưu đầy đủ trong SQLite; màn hình hiển thị 2.000 dòng mới nhất.")
        log_hint.setObjectName("muted")
        log_hint.setWordWrap(True)
        outer.addWidget(log_hint)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setAccessibleName("Nhật ký ứng dụng")
        outer.addWidget(self.log_view, 1)
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.log_view.toPlainText()))
        clear_button.clicked.connect(self._clear)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def set_active(self, active: bool) -> None:
        if active:
            self.refresh()
            self.timer.start(1200)
        else:
            self.timer.stop()

    def refresh(self) -> None:
        text = self.logger.get_all_logs()
        if self.log_view.toPlainText() != text:
            self.log_view.setPlainText(text)
            self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _clear(self) -> None:
        confirmed = _confirm_action(
            self,
            "Xóa nhật ký cục bộ của ứng dụng?",
            "Xóa nhật ký",
        )
        if not confirmed:
            return
        self.logger.clear()
        self.refresh()


class MainWindow(QMainWindow):
    pause_requested = Signal()
    quit_requested = Signal()
    restart_requested = Signal()
    uninstall_requested = Signal()
    update_install_requested = Signal(str)

    def __init__(
        self,
        settings: SettingsManager,
        history: HistoryManager,
        logger: AppLogger,
        model_registry: ModelRegistryManager,
        tray_available: bool,
    ) -> None:
        super().__init__()
        self.settings = settings
        set_ui_language(settings.config.ui_language)
        self.tray_available = tray_available
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 620)
        self.resize(1120, 760)
        icon_path = resource_path("assets", "icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        _apply_app_style(self)

        root = QWidget()
        root.setObjectName("appRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(10)
        brand = QLabel("re/read")
        brand.setObjectName("brand")
        brand_sub = QLabel("DESKTOP TRANSLATOR")
        brand_sub.setObjectName("brandSub")
        side.addWidget(brand)
        side.addWidget(brand_sub)
        side.addSpacing(25)

        self.pages = QStackedWidget()
        self.home = HomePage(settings, model_registry)
        self.history_page = HistoryPage(history)
        self.models_page = ModelPage(model_registry)
        self.settings_page = SettingsPage(settings)
        self.activity_page = ActivityPage(logger)
        self.page_widgets = [
            ("Dịch", self.home),
            ("Lịch sử", self.history_page),
            ("Mô hình", self.models_page),
            ("Cài đặt", self.settings_page),
            ("Nhật ký", self.activity_page),
        ]
        self.nav_buttons: list[QPushButton] = []
        for group_name, indices in (("Làm việc", range(PAGE_OVERVIEW, PAGE_MODELS + 1)), ("Tiện ích", range(PAGE_SETTINGS, PAGE_ACTIVITY + 1))):
            group_label = QLabel(group_name)
            group_label.setObjectName("navGroup")
            side.addWidget(group_label)
            for index in indices:
                label, page = self.page_widgets[index]
                button = QPushButton(label)
                button.setObjectName("navButton")
                button.setCheckable(True)
                button.setAccessibleName(f"Mở trang {label}")
                button.clicked.connect(lambda _checked=False, idx=index: self.show_page(idx))
                side.addWidget(button)
                self.nav_buttons.append(button)
                self.pages.addWidget(_page_scroll(page))
        side.addStretch(1)
        footer = QLabel("Bản dịch được xử lý cục bộ")
        footer.setObjectName("brandSub")
        footer.setWordWrap(True)
        side.addWidget(footer)
        shell.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(26, 15, 26, 15)
        self.page_title = QLabel("Dịch")
        self.page_title.setObjectName("pageTitle")
        self.status = QLabel("Đang khởi động…")
        self.status.setObjectName("statusText")
        self.status.setMinimumWidth(260)
        self.status.setMaximumWidth(360)
        self.status.setWordWrap(True)
        self.pause_button = QPushButton("Tạm dừng")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_requested.emit)
        top_layout.addWidget(self.page_title)
        top_layout.addStretch(1)
        top_layout.addWidget(self.status)
        top_layout.addSpacing(14)
        top_layout.addWidget(self.pause_button)
        content_layout.addWidget(topbar)
        content_layout.addWidget(self.pages, 1)
        shell.addWidget(content, 1)
        self.setCentralWidget(root)
        self.show_page(PAGE_OVERVIEW)
        self.home.translate_requested.connect(self.manual_translation_requested.emit)
        self.home.models_requested.connect(lambda: self.show_page(PAGE_MODELS))
        self.home.settings_requested.connect(lambda: self.show_page(PAGE_SETTINGS))
        self.settings_page.restart_requested.connect(self.restart_requested.emit)
        self.settings_page.uninstall_requested.connect(self.uninstall_requested.emit)
        self.settings_page.update_install_requested.connect(self.update_install_requested.emit)
        localize_widgets(self)

    def show_page(self, index: int) -> None:
        if hasattr(self, "activity_page"):
            self.activity_page.set_active(index == PAGE_ACTIVITY)
        self.pages.setCurrentIndex(index)
        self.page_title.setText(translate(self.page_widgets[index][0]))
        if index == PAGE_OVERVIEW:
            self.home.refresh_details()
        for row, button in enumerate(self.nav_buttons):
            button.setChecked(row == index)
        if index == PAGE_HISTORY:
            self.history_page.refresh()
        elif index == PAGE_MODELS:
            self.models_page.refresh()
        elif index == PAGE_SETTINGS and not self.settings_page.is_dirty:
            self.settings_page.load()
        elif index == PAGE_ACTIVITY:
            self.activity_page.refresh()

    manual_translation_requested = Signal(str)

    def set_status(self, message: str, ready: bool = False) -> None:
        self.status.setText(translate(message))
        self.home.set_kernel_status(translate(message), ready)
        self.pause_button.setEnabled(ready)

    def set_paused(self, paused: bool) -> None:
        self.pause_button.setText(translate("Tiếp tục" if paused else "Tạm dừng"))
        self.status.setText(translate("Đang tạm dừng" if paused else "Đang hoạt động"))

    def show_result(self, translated_text: str, error: str = "") -> None:
        self.home.show_result(translated_text, error)
        if error:
            self.status.setText(translate("Không dịch được văn bản"))

    def refresh_history(self) -> None:
        self.history_page.refresh()

    def closeEvent(self, event) -> None:
        if self.tray_available:
            self.hide()
            event.ignore()
        else:
            self.quit_requested.emit()
            event.accept()

