"""Offscreen smoke check for the PySide6 desktop shell and translation overlay."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QStyleOptionButton,
)
from PySide6.QtGui import QColor, QImage, QPalette

from reread_pyext.config.history import HistoryManager
from reread_pyext.config.model_registry import ModelRegistryManager
from reread_pyext.config.settings import SettingsManager
from reread_pyext.kernel import TranslationResult
from reread_pyext.logger import AppLogger
from reread_pyext.ui.main_window import (
    APP_STYLE,
    PAGE_ACTIVITY,
    PAGE_HISTORY,
    PAGE_MODELS,
    PAGE_OVERVIEW,
    PAGE_SETTINGS,
    MainWindow,
    ModelPage,
)
from reread_pyext.ui.tooltip import FloatingTooltip
from reread_pyext.ui.first_run_setup import FirstRunSetupDialog


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLE)
    with tempfile.TemporaryDirectory(prefix="reread-qt-smoke-") as temp_dir:
        data = Path(temp_dir)
        setup_settings = SettingsManager(config_path=data / "first-run-config.json")
        selected_models = data / "selected-models"
        setup_dialog = FirstRunSetupDialog(setup_settings)
        assert [setup_dialog.language_combo.itemData(i) for i in range(setup_dialog.language_combo.count())] == ["vi", "en"]
        setup_dialog.directory_edit.setText(str(selected_models))
        setup_dialog.language_combo.setCurrentIndex(1)

        def complete_first_run_setup() -> None:
            image = setup_dialog.grab().toImage()
            assert image.pixelColor(5, 5).name() == "#f3f6f4"
            button = next(
                button for button in setup_dialog.findChildren(QPushButton)
                if button.property("setupAction") == "finish"
            )
            button.click()

        QTimer.singleShot(0, complete_first_run_setup)
        assert setup_dialog.exec() == QDialog.DialogCode.Accepted
        assert setup_settings.config.setup_complete
        assert setup_settings.config.model_directory == str(selected_models)
        assert setup_settings.config.ui_language == "en"
        assert selected_models.is_dir() and list(selected_models.iterdir()) == []

        settings = SettingsManager(config_path=data / "config.json")
        settings.update(model_directory=str(data / "models"))
        history = HistoryManager(history_file=data / "history.json")
        logger = AppLogger(log_file=data / "app.log")
        models = ModelRegistryManager(models_dir=data / "models")

        window = MainWindow(settings, history, logger, models, tray_available=False)
        window.set_status("Đang hoạt động · dịch ngoại tuyến", ready=True)
        window.show()
        app.processEvents()
        for index in range(window.pages.count()):
            scroll_or_page = window.pages.widget(index)
            page = scroll_or_page.widget() if hasattr(scroll_or_page, "widget") else scroll_or_page
            rendered = QImage(page.size(), QImage.Format.Format_ARGB32)
            rendered.fill(QColor("#1e1e1e"))
            page.render(rendered)
            assert not rendered.isNull()
        assert window.pages.count() == 5
        assert [button.text() for button in window.nav_buttons] == ["Dịch", "Lịch sử", "Mô hình", "Cài đặt", "Nhật ký"]
        tray_menu = QMenu(window)
        tray_menu.addAction("Mở re/read")
        tray_menu.addAction("Tạm dừng")
        tray_menu.addSeparator()
        tray_menu.addAction("Thoát")
        tray_menu.ensurePolished()
        tray_menu.resize(tray_menu.sizeHint())
        tray_menu.show()
        app.processEvents()
        tray_menu_image = tray_menu.grab().toImage()
        assert tray_menu.palette().color(QPalette.ColorRole.Window).name() == "#ffffff"
        assert tray_menu.palette().color(QPalette.ColorRole.WindowText).name() == "#1d2927"
        assert tray_menu_image.pixelColor(tray_menu_image.width() - 12, tray_menu_image.height() // 2).name() == "#ffffff"
        tray_menu.hide()
        assert window.home.target_combo.count() == 1
        assert window.home.target_combo.currentText() == "Chưa có mô hình đã cài"
        assert window.home.target_combo.currentData() is None
        assert window.home.target_combo.isEnabled() is False
        home_labels = [label.text() for label in window.home.findChildren(QLabel)]
        assert "Bắt đầu nhanh" in home_labels
        assert any("Ctrl+C hai lần" in label for label in home_labels)
        assert any("Ctrl+V hai lần" in label for label in home_labels)
        assert window.home.settings_button.text() == "Chọn nơi lưu"
        assert window.home.layout().itemAt(1).widget() is window.home.quick_start_card
        assert [window.settings_page.ui_language.itemData(i) for i in range(window.settings_page.ui_language.count())] == ["vi", "en"]
        assert window.settings_page.uninstall_button.text() == "Gỡ cài đặt"
        uninstall_requests = []
        window.uninstall_requested.connect(lambda: uninstall_requests.append(True))
        with patch("reread_pyext.ui.main_window._confirm_action", return_value=True):
            window.settings_page.uninstall_button.click()
        assert uninstall_requests == [True]
        window.home.install_models_button.click()
        app.processEvents()
        assert window.pages.currentIndex() == PAGE_MODELS
        window.home.settings_button.click()
        app.processEvents()
        assert window.pages.currentIndex() == PAGE_SETTINGS
        assert window.settings_page.model_directory.text() == str(models.models_dir)
        assert window.settings_page.choose_model_directory_button.text() == "Chọn thư mục…"
        window.show_page(PAGE_OVERVIEW)
        assert not hasattr(window.home, "target_summary")
        assert not any(
            label.text() == "Nhập văn bản hoặc bôi đen nội dung trong ứng dụng khác."
            for label in window.home.findChildren(QLabel)
        )
        assert [label.text() for label in window.findChildren(type(window.page_title), "navGroup")] == ["Làm việc", "Tiện ích"]
        for index, button in enumerate(window.nav_buttons):
            button.click()
            assert window.pages.currentIndex() == index
        assert window.pages.widget(PAGE_HISTORY) is window.history_page
        assert window.pages.widget(PAGE_SETTINGS) is window.settings_page
        assert window.pages.widget(PAGE_ACTIVITY) is window.activity_page
        history_content = window.history_page.findChild(QScrollArea).widget()
        settings_content = window.settings_page.findChild(QScrollArea).widget()
        assert history_content.objectName() == "desktopPageContent"
        assert settings_content.objectName() == "desktopPageContent"
        assert history_content.palette().color(QPalette.ColorRole.Window).name() == "#f3f6f4"
        assert settings_content.palette().color(QPalette.ColorRole.Window).name() == "#f3f6f4"
        form_label = next(label for label in window.settings_page.findChildren(QLabel) if label.text() == "Kéo chọn")
        assert form_label.palette().color(QPalette.ColorRole.WindowText).name() == "#1d2927"
        assert not any(
            checkbox.text() == "Tự cuộn"
            for checkbox in window.activity_page.findChildren(QCheckBox)
        )
        assert window.status.minimumWidth() >= 250
        startup_enabled = window.settings_page.startup.is_registered()[0]
        if startup_enabled and window.settings_page.start_on_boot.isChecked():
            expected_startup_status = "Đã đăng ký khởi động cùng Windows."
        elif startup_enabled:
            expected_startup_status = "Lưu thay đổi sẽ gỡ mục tự khởi động của re/read."
        else:
            expected_startup_status = "Ứng dụng không tự chạy khi đăng nhập Windows."
        assert window.settings_page.startup_status.text() == expected_startup_status
        assert window.settings_page.save_button.isEnabled() is False
        for disabled_button in (window.home.translate_button, window.history_page.clear_button, window.settings_page.save_button):
            assert disabled_button.isEnabled() is False
            assert disabled_button.palette().color(QPalette.ColorRole.Button).name() == "#f1f4f2"
            assert disabled_button.palette().color(QPalette.ColorRole.ButtonText).name() == "#96a49f"
        original_auto_drag = window.settings_page.auto_drag.isChecked()
        window.settings_page.auto_drag.setChecked(not original_auto_drag)
        assert window.settings_page.dirty_status.text() == "Có thay đổi chưa lưu"
        assert window.settings_page.save_button.isEnabled() is True
        assert window.settings_page.undo_button.isEnabled() is True
        window.show_page(PAGE_HISTORY)
        window.show_page(PAGE_SETTINGS)
        assert window.settings_page.auto_drag.isChecked() != original_auto_drag
        assert window.settings_page.is_dirty is True
        window.settings_page.undo_button.click()
        assert window.settings_page.auto_drag.isChecked() == original_auto_drag
        assert window.settings_page.save_button.isEnabled() is False

        settings_page = window.settings_page
        custom_model_directory = data / "portable-models"
        with patch(
            "reread_pyext.ui.main_window.QFileDialog.getExistingDirectory",
            return_value=str(custom_model_directory),
        ):
            settings_page._choose_model_directory()
        assert settings_page.model_directory.text() == str(custom_model_directory)
        assert settings_page.is_dirty is True
        assert settings_page.auto_close_enabled.isChecked() is True
        assert settings_page.hold_duration.value() == 2.0
        assert settings_page.hold_duration.lineEdit().text() == "2.00"
        assert settings_page.auto_close_delay.value() == 15
        assert settings_page.auto_close_delay.lineEdit().text() == "15"
        assert settings_page.auto_close_delay.isEnabled() is True
        assert settings_page.hold_duration_unit.text() == "giây"
        assert settings_page.auto_close_delay_unit.text() == "giây"
        assert "toàn bộ lịch sử" in settings_page.save_history.text().casefold()
        assert settings_page.data_path.text().endswith("reread.sqlite3")
        checkbox_option = QStyleOptionButton()
        settings_page.auto_drag.initStyleOption(checkbox_option)
        checkbox_rect = settings_page.auto_drag.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            checkbox_option,
            settings_page.auto_drag,
        )
        checkbox_image = settings_page.auto_drag.grab().toImage()
        white_tick_pixels = sum(
            checkbox_image.pixelColor(x, y).name() == "#ffffff"
            for y in range(checkbox_rect.top(), checkbox_rect.bottom() + 1)
            for x in range(checkbox_rect.left(), checkbox_rect.right() + 1)
        )
        assert white_tick_pixels > 0
        settings_page.auto_close_enabled.setChecked(False)
        assert settings_page.auto_close_delay.isEnabled() is False
        assert settings_page._form_values()["auto_close_seconds"] == 0
        settings_page.auto_close_enabled.setChecked(True)
        assert settings_page._form_values()["auto_close_seconds"] == 15
        window.show_page(PAGE_SETTINGS)
        app.processEvents()
        for spinbox in (settings_page.hold_duration, settings_page.auto_close_delay):
            assert spinbox.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
            assert spinbox.width() <= 110
            assert spinbox.suffix() == ""
            assert spinbox.lineEdit().width() > 1
            editor = spinbox.lineEdit()
            editor_image = editor.grab().toImage()
            assert "background: #ffffff" in editor.styleSheet()
            assert editor.palette().color(QPalette.ColorRole.Text).name() == "#1d2927"
            assert editor_image.pixelColor(8, editor_image.height() // 2).name() == "#ffffff"

        style = window.styleSheet()
        assert "QCheckBox::indicator:checked" in style
        assert "QMenu { color: #1d2927; background-color: #ffffff;" in APP_STYLE
        assert "QMenu::item:selected { color: #1d5a52; background: #dcefe9; }" in APP_STYLE
        assert "QComboBox QAbstractItemView" in style
        dropdown_style = style.split("QComboBox::drop-down {", 1)[1].split("}", 1)[0]
        assert "border: none" in dropdown_style and "background: transparent" in dropdown_style
        combo_view = window.home.target_combo.view()
        assert combo_view.palette().color(QPalette.ColorRole.Base).name() == "#ffffff"
        assert combo_view.palette().color(QPalette.ColorRole.Text).name() == "#1d2927"
        assert combo_view.palette().color(QPalette.ColorRole.Highlight).name() == "#dcefe9"
        assert combo_view.palette().color(QPalette.ColorRole.HighlightedText).name() == "#1d5a52"
        window.home.target_combo.showPopup()
        app.processEvents()
        popup_container = combo_view.parentWidget()
        assert isinstance(popup_container, QFrame)
        assert popup_container.frameShape() == QFrame.Shape.NoFrame
        assert popup_container.palette().color(QPalette.ColorRole.Window).name() == "#ffffff"
        assert combo_view.minimumHeight() >= combo_view.sizeHintForRow(0) * window.home.target_combo.count()
        assert combo_view.height() >= combo_view.sizeHintForRow(0) * window.home.target_combo.count()
        window.home.target_combo.hidePopup()

        installed = SimpleNamespace(
            pair="envi", from_lang="en", to_lang="vi", from_name="English", to_name="Vietnamese",
            from_display_name="Tiếng Anh", to_display_name="Tiếng Việt", is_installed=True,
            installed_size_mb=812.4, download_size_mb=0, architecture="intgemm8", underlying_pair=None,
        )
        available = SimpleNamespace(
            pair="jaen", from_lang="ja", to_lang="en", from_name="Japanese", to_name="English",
            from_display_name="Tiếng Nhật", to_display_name="Tiếng Anh", is_installed=False,
            installed_size_mb=0, download_size_mb=92.1, architecture="intgemm8", underlying_pair=None,
        )
        models_page = ModelPage(SimpleNamespace(get_available_packages=lambda: [available, installed]))
        assert not hasattr(models_page, "model_summary")
        model_card = models_page.list.item(0)
        assert model_card.text().splitlines() == [
            "Tiếng Anh → Tiếng Việt",
            "EN → VI",
            "✓ ĐÃ CÀI  ·  812.4 MB",
        ]
        assert model_card.sizeHint().height() >= 82
        assert models_page.detail_title.text() == "Tiếng Anh → Tiếng Việt"
        assert models_page.detail_text.text().startswith("EN → VI\n")

        zhen = SimpleNamespace(
            pair="zhen", from_lang="zh", to_lang="en", from_name="Chinese (Simplified)", to_name="English",
            from_display_name="Tiếng Trung (Giản thể)", to_display_name="Tiếng Anh", is_installed=True,
            installed_size_mb=812.4, download_size_mb=0, architecture="intgemm8", underlying_pair=None,
        )
        zhvi = SimpleNamespace(
            pair="zhvi", from_lang="zh", to_lang="vi", from_name="Chinese (Simplified)", to_name="Vietnamese",
            from_display_name="Tiếng Trung (Giản thể)", to_display_name="Tiếng Việt", is_installed=True,
            installed_size_mb=812.4, download_size_mb=0, architecture="intgemm8", underlying_pair="zhen",
        )
        companion_page = ModelPage(SimpleNamespace(get_available_packages=lambda: [zhen, zhvi]))
        assert not hasattr(companion_page, "model_summary")
        companion_row = next(
            index for index in range(companion_page.list.count())
            if companion_page.list.item(index).data(Qt.ItemDataRole.UserRole) == "zhvi"
        )
        companion_page.list.setCurrentRow(companion_row)
        app.processEvents()
        assert companion_page.list.currentItem().text().splitlines()[:2] == ["Tiếng Trung (Giản thể) → Tiếng Việt", "ZH → VI"]
        assert "DÙNG CHUNG ZHEN" not in companion_page.list.currentItem().text()
        assert companion_page.delete_button.isHidden()
        assert companion_page.detail_title.text() == "Tiếng Trung (Giản thể) → Tiếng Việt"
        assert companion_page.detail_text.text() == "ZH → VI\nSẵn sàng"

        model_confirmation = []

        def cancel_model_confirmation() -> None:
            for dialog in QApplication.topLevelWidgets():
                if isinstance(dialog, QMessageBox) and dialog.isVisible():
                    buttons = [button.text() for button in dialog.findChildren(QPushButton)]
                    model_confirmation.append(buttons)
                    cancel = next(
                        (button for button in dialog.findChildren(QPushButton) if button.text() == "Hủy"),
                        None,
                    )
                    if cancel:
                        cancel.click()
                    return

        QTimer.singleShot(0, cancel_model_confirmation)
        models_page._delete()
        assert model_confirmation and "Gỡ mô hình" in model_confirmation[0] and "Hủy" in model_confirmation[0]

        class RecordingStartup:
            def __init__(self) -> None:
                self.registered = True
                self.cleared = False

            def is_registered(self):
                return self.registered, "RereadDesktopService", "launcher"

            def register(self):
                self.registered = True
                return True, "registered"

            def clear_keys(self):
                self.cleared = True
                self.registered = False
                return True, "cleared", 1

        settings.update(start_on_boot=True)
        startup = RecordingStartup()
        settings_page.startup = startup
        settings_page.load()
        custom_model_directory = data / "portable-models"
        settings_page.model_directory.setText(str(custom_model_directory))
        settings_page.start_on_boot.setChecked(False)
        assert "gỡ" in settings_page.startup_status.text().casefold()
        settings_page._save()
        assert startup.cleared is True
        assert settings.config.start_on_boot is False
        assert settings.config.model_directory == str(custom_model_directory.resolve())
        assert custom_model_directory.is_dir()
        assert "mở lại ứng dụng" in settings_page.feedback.text().casefold()
        assert "gỡ mục đăng ký" in settings_page.feedback.text().casefold()

        window.show_page(PAGE_OVERVIEW)
        assert window.home.target_combo.currentData() is None
        assert window.home.models_status.text().startswith("Chưa có mô hình")
        assert window.home.install_models_button.isVisible()
        window.home.install_models_button.click()
        assert window.pages.currentIndex() == 2
        assert window.home.translate_button.isEnabled() is False
        assert window.home.copy_button.isEnabled() is False
        window.home.input.setPlainText("Hello")
        window.home.set_kernel_status("Đang hoạt động", ready=True)
        assert window.home.translate_button.isEnabled() is True
        translated = []
        window.manual_translation_requested.connect(translated.append)
        window.home.translate_button.click()
        assert translated == ["Hello"]
        window.home.show_result("Xin chào")
        assert window.home.copy_button.isEnabled() is True
        window.home.copy_button.click()
        assert app.clipboard().text() == "Xin chào"
        window.home.clear_button.click()
        assert window.home.input.toPlainText() == ""
        assert window.home.output.toPlainText() == ""

        installed_models = [
            SimpleNamespace(pair="envi", to_lang="vi"),
            SimpleNamespace(pair="vien", to_lang="en"),
            SimpleNamespace(pair="zhen", to_lang="en"),
        ]
        installed_directions = [
            SimpleNamespace(pair="envi", from_lang="en", to_lang="vi", is_installed=True, underlying_pair=None),
            SimpleNamespace(pair="zhvi", from_lang="zh", to_lang="vi", is_installed=True, underlying_pair="zhen"),
            SimpleNamespace(pair="vien", from_lang="vi", to_lang="en", is_installed=True, underlying_pair=None),
            SimpleNamespace(pair="zhen", from_lang="zh", to_lang="en", is_installed=True, underlying_pair=None),
        ]
        window.home.model_registry = SimpleNamespace(
            get_installed_models=lambda: installed_models,
            get_available_packages=lambda: installed_directions,
        )
        settings.update(target_lang="zh")
        window.show_page(PAGE_OVERVIEW)
        assert [window.home.target_combo.itemData(i) for i in range(window.home.target_combo.count())] == ["vi", "en"]
        assert [window.home.target_combo.itemText(i) for i in range(window.home.target_combo.count())] == [
            "Tiếng Việt (VI)", "Tiếng Anh (EN)"
        ]
        assert window.home.target_combo.itemData(0, Qt.ItemDataRole.ToolTipRole) is None
        assert not hasattr(window.home, "target_summary")
        assert window.home.models_status.isHidden()
        assert window.home.target_combo.currentData() == "vi"
        assert settings.config.target_lang == "vi"
        window.home.target_combo.setCurrentIndex(window.home.target_combo.findData("en"))
        app.processEvents()
        assert settings.config.target_lang == "en"
        window.home.target_combo.setCurrentIndex(window.home.target_combo.findData("vi"))
        app.processEvents()
        window.show_page(PAGE_HISTORY)
        app.processEvents()
        assert window.pages.currentIndex() == PAGE_HISTORY

        history.add_item("Hello", "Xin chào", "en", "vi")
        window.history_page.refresh()
        confirmation = []

        def cancel_history_confirmation() -> None:
            for dialog in QApplication.topLevelWidgets():
                if isinstance(dialog, QMessageBox) and dialog.isVisible():
                    confirmation.append({
                        "buttons": [button.text() for button in dialog.findChildren(QPushButton)],
                        "background": dialog.palette().color(QPalette.ColorRole.Window).name(),
                        "text": dialog.palette().color(QPalette.ColorRole.WindowText).name(),
                        "style": dialog.styleSheet(),
                        "title": dialog.windowTitle(),
                    })
                    cancel = next(
                        (button for button in dialog.findChildren(QPushButton) if button.text() == "Hủy"),
                        None,
                    )
                    if cancel:
                        cancel.click()
                    return

        QTimer.singleShot(0, cancel_history_confirmation)
        window.history_page._clear()
        assert confirmation and "Xóa lịch sử" in confirmation[0]["buttons"] and "Hủy" in confirmation[0]["buttons"]
        assert confirmation[0]["title"] == "re/read Desktop"
        assert confirmation[0]["background"] == "#ffffff"
        assert confirmation[0]["text"] == "#1d2927"
        assert "QMessageBox QLabel" in confirmation[0]["style"]
        assert len(history.get_items()) == 1

        activity_confirmation = []

        def cancel_activity_confirmation() -> None:
            for dialog in QApplication.topLevelWidgets():
                if isinstance(dialog, QMessageBox) and dialog.isVisible():
                    activity_confirmation.extend(button.text() for button in dialog.findChildren(QPushButton))
                    cancel = next(
                        (button for button in dialog.findChildren(QPushButton) if button.text() == "Hủy"),
                        None,
                    )
                    if cancel:
                        cancel.click()
                    return

        QTimer.singleShot(0, cancel_activity_confirmation)
        window.activity_page._clear()
        assert "Xóa nhật ký" in activity_confirmation and "Hủy" in activity_confirmation

        shown = []
        tooltip = FloatingTooltip(on_shown=shown.append)
        result = TranslationResult(
            source_text="Hello desktop",
            translated_text="Xin chào máy tính",
            src_lang="en",
            tgt_lang="vi",
            pipeline=["envi"],
            duration_ms=43.0,
        )
        tooltip.show_result(result, 30, 30)
        app.processEvents()
        assert tooltip.is_visible
        assert tooltip.translation.text() == result.translated_text
        assert shown == [result]
        tooltip.hide()
        window.close()
        english_settings = SettingsManager(config_path=data / "english-config.json")
        english_settings.update(ui_language="en", model_directory=str(data / "english-models"))
        english_window = MainWindow(
            english_settings,
            HistoryManager(history_file=data / "english-history.json"),
            AppLogger(log_file=data / "english-app.log"),
            ModelRegistryManager(models_dir=data / "english-models"),
            tray_available=False,
        )
        assert [button.text() for button in english_window.nav_buttons] == [
            "Translate", "History", "Models", "Settings", "Log"
        ]
        assert english_window.page_title.text() == "Translate"
        assert english_window.home.install_models_button.text() == "Get models"
        assert english_window.settings_page.ui_language.currentData() == "en"
        assert english_window.settings_page.uninstall_button.text() == "Uninstall"
        assert english_window.models_page.findChildren(QLabel)[0].text() == "Language models"
        english_window.show()
        app.processEvents()
        for index in range(english_window.pages.count()):
            scroll_or_page = english_window.pages.widget(index)
            page = scroll_or_page.widget() if hasattr(scroll_or_page, "widget") else scroll_or_page
            rendered = QImage(page.size(), QImage.Format.Format_ARGB32)
            rendered.fill(QColor("#1e1e1e"))
            page.render(rendered)
            assert not rendered.isNull()
        english_window.settings_page.ui_language.setCurrentIndex(0)
        english_window.settings_page._save()
        assert english_settings.config.ui_language == "vi"
        assert english_window.settings_page.feedback.text() == "Khởi động lại ứng dụng để áp dụng ngôn ngữ mới."
        english_tooltip = FloatingTooltip()
        english_tooltip.show_result(result, 30, 30)
        english_tooltip.copy_button.click()
        assert english_tooltip.copy_button.text() == "Copied"
        english_tooltip.hide()
        english_window.close()
        app.processEvents()

    print("Qt desktop and overlay smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
