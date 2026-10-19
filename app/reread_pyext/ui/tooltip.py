"""Interactive, screen-aware translation overlay implemented with Qt Widgets."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..kernel.kernel import TranslationResult
from .translations import localize_widgets, translate


class FloatingTooltip(QWidget):
    def __init__(self, on_shown: Optional[Callable[[TranslationResult], None]] = None) -> None:
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.on_shown = on_shown
        self._current_result: Optional[TranslationResult] = None
        self._drag_offset: Optional[QPoint] = None
        self._is_hold = False
        self.auto_close_seconds = 15
        self.is_visible = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("""
          QWidget#translationCard { background: #142033; color: #f7f9fc; border: 1px solid #40516a; border-radius: 13px; }
          QLabel#route { color: #a9c6ff; font-size: 9pt; font-weight: 700; }
          QLabel#duration { color: #a4b1c4; font-size: 9pt; }
          QLabel#translation { color: #f7f9fc; font-size: 12pt; }
          QLabel#source { color: #b3bfd0; font-size: 9pt; }
          QPushButton { color: #e8eef8; background: #26364e; border: 1px solid #42546d; border-radius: 7px; padding: 5px 9px; }
          QPushButton:hover { background: #344965; }
        """)
        card = QFrame(self)
        card.setObjectName("translationCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(9)
        header = QHBoxLayout()
        self.route = QLabel("")
        self.route.setObjectName("route")
        self.duration = QLabel("")
        self.duration.setObjectName("duration")
        self.copy_button = QPushButton("Sao chép")
        self.copy_button.clicked.connect(self._copy)
        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.hide)
        header.addWidget(self.route)
        header.addWidget(self.duration)
        header.addStretch(1)
        header.addWidget(self.copy_button)
        header.addWidget(close_button)
        self.translation = QLabel("")
        self.translation.setObjectName("translation")
        self.translation.setWordWrap(True)
        self.translation.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.source = QLabel("")
        self.source.setObjectName("source")
        self.source.setWordWrap(True)
        layout.addLayout(header)
        layout.addWidget(self.translation)
        layout.addWidget(self.source)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.setMinimumWidth(300)
        self.setMaximumWidth(440)
        self._drag_widget = card
        card.mousePressEvent = self._drag_start
        card.mouseMoveEvent = self._drag_move
        card.mouseReleaseEvent = self._drag_end
        localize_widgets(self)

    def set_auto_close_seconds(self, seconds: int) -> None:
        self.auto_close_seconds = max(0, seconds)

    @property
    def is_hold(self) -> bool:
        return self._is_hold

    def show_result(self, result: TranslationResult, mouse_x: int, mouse_y: int, is_hold: bool = False) -> None:
        self._current_result = result
        self._is_hold = is_hold
        self.route.setText(f"{result.src_lang.upper()}  →  {result.tgt_lang.upper()}")
        self.duration.setText(f"{result.duration_ms:.0f} ms")
        self.translation.setText(result.translated_text or translate(result.error) or translate("Không có bản dịch."))
        text = result.source_text
        snippet = text if len(text) <= 140 else text[:137] + "…"
        self.source.setText(snippet)
        self.source.setVisible(bool(snippet))
        self.adjustSize()
        self.setMinimumWidth(300)
        self.resize(max(300, self.width()), self.height())

        point = QPoint(mouse_x, mouse_y)
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry() if screen else self.geometry()
        x = mouse_x + 16
        y = mouse_y + 18
        if x + self.width() > bounds.right() - 8:
            x = mouse_x - self.width() - 16
        if y + self.height() > bounds.bottom() - 8:
            y = mouse_y - self.height() - 16
        x = max(bounds.left() + 8, min(x, bounds.right() - self.width() - 8))
        y = max(bounds.top() + 8, min(y, bounds.bottom() - self.height() - 8))
        self.move(x, y)
        self.show()
        self.raise_()
        self.is_visible = True
        if self.on_shown:
            self.on_shown(result)
        self._timer.stop()
        if not is_hold and self.auto_close_seconds:
            self._timer.start(self.auto_close_seconds * 1000)

    def is_click_inside(self, x: int, y: int) -> bool:
        return self.is_visible and self.geometry().contains(QPoint(x, y))

    def hide(self) -> None:  # type: ignore[override]
        self.is_visible = False
        self._timer.stop()
        super().hide()

    def _copy(self) -> None:
        if self._current_result and self._current_result.translated_text:
            QApplication.clipboard().setText(self._current_result.translated_text)
            self.copy_button.setText(translate("Đã sao chép"))
            QTimer.singleShot(1300, lambda: self.copy_button.setText(translate("Sao chép")))

    def _drag_start(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _drag_move(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def _drag_end(self, event) -> None:
        self._drag_offset = None
        event.accept()
