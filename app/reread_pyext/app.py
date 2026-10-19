"""PySide6 desktop application lifecycle and Python service integration."""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from pathlib import Path
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox, QStyle, QSystemTrayIcon

from .config.history import HistoryManager
from .config.model_registry import ModelRegistryManager
from .config.settings import AppConfig, SettingsManager
from .hook import SelectionHook
from .kernel import TranslationKernel, TranslationResult
from .logger import AppLogger, setup_global_logging
from .paths import app_data_dir, migrate_legacy_data, models_dir, node_executable, resource_path
from .ui.main_window import APP_STYLE, PAGE_HISTORY, PAGE_SETTINGS, MainWindow
from .ui.first_run_setup import FirstRunSetupDialog
from .ui.translations import set_ui_language, translate
from .ui.tooltip import FloatingTooltip
from .uninstall_cleanup import cleanup_installed_data


class AppSignals(QObject):
    selection = Signal(str, int, int, str)
    mouse_release = Signal()
    click_outside = Signal(int, int)
    open_settings = Signal()
    open_history = Signal()
    dismiss_overlay = Signal()
    toggle_pause = Signal()
    quit = Signal()
    kernel_status = Signal(str, bool)
    translated = Signal(object, int, int, bool, bool)


class RereadDesktopApp(QObject):
    def __init__(self, background: bool = False, initial_language: str | None = None) -> None:
        self._background = background
        self._qt_args = tuple(sys.argv[1:])
        self.application = QApplication.instance() or QApplication(sys.argv[:1])
        self.application.setApplicationName("re/read Desktop")
        self.application.setOrganizationName("re/read")
        self.application.setQuitOnLastWindowClosed(False)
        self.application.setStyle("Fusion")
        self.application.setStyleSheet(APP_STYLE)
        super().__init__()

        try:
            copied = migrate_legacy_data()
        except Exception as exc:
            copied = []
            print(f"Data migration failed: {exc}", flush=True)

        self.settings_mgr = SettingsManager()
        self._setup_cancelled = False
        if not self.settings_mgr.config.setup_complete:
            setup_dialog = FirstRunSetupDialog(self.settings_mgr, preferred_language=initial_language)
            if setup_dialog.exec() != QDialog.DialogCode.Accepted:
                self._setup_cancelled = True
                return
        elif initial_language in ("vi", "en"):
            self.settings_mgr.update(ui_language=initial_language)
        set_ui_language(self.settings_mgr.config.ui_language)

        self.logger: AppLogger = setup_global_logging()
        for path in copied:
            self.logger.info(f"Copied legacy data to {app_data_dir()}: {path}")
        self.model_directory = models_dir(self.settings_mgr.config.model_directory)
        self.history_mgr = HistoryManager()
        self.model_registry = ModelRegistryManager(models_dir=self.model_directory)
        self.kernel = TranslationKernel(node_executable=node_executable(), models_dir=self.model_directory)
        self.kernel_ready = False
        self._is_running = True
        self._paused = False
        self._shutdown_started = False
        self._restart_requested = False
        self.signals = AppSignals(self)

        icon_path = resource_path("assets", "icon.ico")
        icon = QIcon(str(icon_path)) if icon_path.exists() else self.application.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        self.main_window = MainWindow(
            settings=self.settings_mgr,
            history=self.history_mgr,
            logger=self.logger,
            model_registry=self.model_registry,
            tray_available=self.tray_available,
        )
        self.main_window.setWindowIcon(icon)
        self.tooltip = FloatingTooltip(on_shown=self._on_tooltip_shown)
        self.tooltip.set_auto_close_seconds(self.settings_mgr.config.auto_close_seconds)

        self.tray = QSystemTrayIcon(icon, self.application)
        self.tray.setToolTip(f"re/read Desktop · {translate('Đang khởi động…')}")
        tray_menu = QMenu()
        open_action = QAction(translate("Mở re/read"), self.tray)
        open_action.triggered.connect(self.show_main_window)
        self.pause_action = QAction(translate("Tạm dừng"), self.tray)
        self.pause_action.triggered.connect(self.toggle_pause)
        quit_action = QAction(translate("Thoát"), self.tray)
        quit_action.triggered.connect(self.shutdown)
        tray_menu.addAction(open_action)
        tray_menu.addAction(self.pause_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        if self.tray_available:
            self.tray.show()

        self.signals.selection.connect(self._handle_selection, Qt.ConnectionType.QueuedConnection)
        self.signals.mouse_release.connect(self._handle_mouse_release, Qt.ConnectionType.QueuedConnection)
        self.signals.click_outside.connect(self._handle_click_outside, Qt.ConnectionType.QueuedConnection)
        self.signals.open_settings.connect(self.open_settings, Qt.ConnectionType.QueuedConnection)
        self.signals.open_history.connect(self.open_history, Qt.ConnectionType.QueuedConnection)
        self.signals.dismiss_overlay.connect(self._dismiss_overlay, Qt.ConnectionType.QueuedConnection)
        self.signals.toggle_pause.connect(self.toggle_pause, Qt.ConnectionType.QueuedConnection)
        self.signals.quit.connect(self.shutdown, Qt.ConnectionType.QueuedConnection)
        self.signals.kernel_status.connect(self._set_kernel_status, Qt.ConnectionType.QueuedConnection)
        self.signals.translated.connect(self._show_translation, Qt.ConnectionType.QueuedConnection)
        self.main_window.pause_requested.connect(self.toggle_pause)
        self.main_window.quit_requested.connect(self.shutdown)
        self.main_window.restart_requested.connect(self.restart)
        self.main_window.uninstall_requested.connect(self.start_uninstaller)
        self.main_window.update_install_requested.connect(self.install_update)
        self.main_window.manual_translation_requested.connect(self._handle_manual_translation)
        self.settings_mgr.add_listener(self._on_settings_updated)

        self.hook = SelectionHook(
            on_selection=lambda text, x, y, source="mouse": self.signals.selection.emit(text, x, y, source),
            on_click_outside=lambda x, y: self.signals.click_outside.emit(x, y),
            on_mouse_release=self.signals.mouse_release.emit,
            on_hotkey_settings=self.signals.open_settings.emit,
            on_hotkey_pause=self.signals.toggle_pause.emit,
            on_hotkey_quit=self.signals.quit.emit,
            on_hotkey_history=self.signals.open_history.emit,
            on_hotkey_dismiss=self.signals.dismiss_overlay.emit,
            settings_mgr=self.settings_mgr,
        )

        self._start_kernel()
        if not background:
            self.show_main_window()

    def _start_kernel(self) -> None:
        self.hook.start()

        def start_services() -> None:
            try:
                self.kernel.start()
                self.signals.kernel_status.emit("Đang hoạt động · dịch ngoại tuyến", True)
                self.logger.info("Translation kernel is ready.")
            except Exception as exc:
                self.signals.kernel_status.emit(f"Không thể khởi động lõi dịch: {exc}", False)
                self.logger.error(f"Translation kernel startup failed: {exc}")

        threading.Thread(target=start_services, name="reread-startup", daemon=True).start()

    @Slot(str, bool)
    def _set_kernel_status(self, message: str, ready: bool) -> None:
        self.kernel_ready = ready
        self.main_window.set_status(message, ready)
        self.tray.setToolTip(f"re/read Desktop · {translate(message)}")

    @Slot(str, int, int, str)
    def _handle_selection(self, text: str, mouse_x: int, mouse_y: int, source: str) -> None:
        if not self._is_running or self._paused:
            return
        self.logger.info(f"Selection detected ({source}, {len(text)} chars).")
        self._request_translation(text, mouse_x, mouse_y, source == "hold_to_translate", show_overlay=True)

    @Slot(str)
    def _handle_manual_translation(self, text: str) -> None:
        from PySide6.QtGui import QCursor

        point = QCursor.pos()
        self._request_translation(text, point.x(), point.y(), False, show_overlay=False)

    def _request_translation(self, text: str, x: int, y: int, is_hold: bool, show_overlay: bool) -> None:
        if not self.kernel_ready:
            self.main_window.show_result("", "Lõi dịch chưa sẵn sàng. Hãy kiểm tra Node.js và nhật ký hoạt động.")
            return
        cfg: AppConfig = self.settings_mgr.config

        def translate() -> None:
            try:
                result = self.kernel.translate(
                    text,
                    reverse_vi_to_en=cfg.reverse_vi_to_en,
                    pivot_cjk=cfg.pivot_cjk,
                    target_lang=cfg.target_lang,
                )
            except Exception as exc:
                result = TranslationResult(text, "", "", cfg.target_lang, [], 0.0, str(exc))
            self.signals.translated.emit(result, x, y, is_hold, show_overlay)

        threading.Thread(target=translate, name="reread-translate", daemon=True).start()

    @Slot(object, int, int, bool, bool)
    def _show_translation(self, result: TranslationResult, x: int, y: int, is_hold: bool, show_overlay: bool) -> None:
        self.logger.info(f"Translation completed ({result.src_lang} → {result.tgt_lang}, {result.duration_ms:.0f} ms).")
        if show_overlay:
            self.tooltip.show_result(result, x, y, is_hold=is_hold)
        else:
            self.main_window.show_result(result.translated_text, result.error or "")
            self._record_history(result)
        if result.error:
            self.main_window.set_status("Bản dịch chưa hoàn tất", self.kernel_ready)

    def _on_tooltip_shown(self, result: TranslationResult) -> None:
        self._record_history(result)

    def _record_history(self, result: TranslationResult) -> None:
        if self.settings_mgr.config.enable_history and result.translated_text:
            self.history_mgr.add_item(
                source_text=result.source_text,
                translated_text=result.translated_text,
                src_lang=result.src_lang,
                tgt_lang=result.tgt_lang,
                duration_ms=result.duration_ms,
            )
            self.main_window.refresh_history()

    @Slot(int, int)
    def _handle_click_outside(self, x: int, y: int) -> None:
        if self.tooltip.is_visible and not self.tooltip.is_click_inside(x, y):
            self.tooltip.hide()

    @Slot()
    def _handle_mouse_release(self) -> None:
        if self.tooltip.is_visible and self.tooltip.is_hold:
            self.tooltip.hide()

    @Slot()
    def _dismiss_overlay(self) -> None:
        if self.tooltip.is_visible:
            self.tooltip.hide()

    @Slot()
    def open_settings(self) -> None:
        self.main_window.show_page(PAGE_SETTINGS)
        self.show_main_window()

    @Slot()
    def open_history(self) -> None:
        self.main_window.show_page(PAGE_HISTORY)
        self.show_main_window()

    @Slot()
    def show_main_window(self) -> None:
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    @Slot()
    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if hasattr(self, "hook"):
            self.hook.set_paused(self._paused)
        self.main_window.set_paused(self._paused)
        self.pause_action.setText(translate("Tiếp tục" if self._paused else "Tạm dừng"))
        self.logger.info("Selection translation paused." if self._paused else "Selection translation resumed.")

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_main_window()

    @Slot(object)
    def _on_settings_updated(self, _config: AppConfig) -> None:
        self.tooltip.set_auto_close_seconds(self.settings_mgr.config.auto_close_seconds)
        self.logger.info("Settings updated.")

    @Slot()
    def shutdown(self) -> None:
        if self._shutdown_started:
            return
        self._shutdown_started = True
        self._is_running = False
        try:
            self.hook.stop()
        except Exception:
            pass
        try:
            self.kernel.stop()
        except Exception as exc:
            self.logger.error(f"Kernel shutdown failed: {exc}")
        self.tray.hide()
        self.tooltip.hide()
        self.application.quit()

    @Slot()
    def restart(self) -> None:
        self._restart_requested = True
        self.shutdown()

    @Slot(str)
    def install_update(self, installer_path: str) -> None:
        installer = Path(installer_path).resolve()
        if not installer.is_file():
            message = translate("Không tìm thấy bộ cài cập nhật đã tải.")
            self.main_window.settings_page.show_update_install_error(message)
            QMessageBox.warning(self.main_window, translate("Cập nhật ứng dụng"), message)
            return
        if not (getattr(sys, "frozen", False) or "__compiled__" in globals()):
            message = translate("Cập nhật tự động chỉ dùng trong bản đã cài đặt.")
            self.main_window.settings_page.show_update_install_error(message)
            QMessageBox.warning(self.main_window, translate("Cập nhật ứng dụng"), message)
            return

        executable_directory = Path(sys.executable).resolve().parent
        command = [
            str(installer),
            "/SP-",
            "/SILENT",
            "/NORESTART",
            f"/LANG={self.settings_mgr.config.ui_language}",
            f"/DIR={executable_directory}",
            "/RESTARTAPP=1",
        ]
        try:
            subprocess.Popen(command, cwd=installer.parent)
        except OSError as exc:
            installer.unlink(missing_ok=True)
            self.logger.error(f"Could not launch the update installer: {exc}")
            message = str(exc)
            self.main_window.settings_page.show_update_install_error(message)
            QMessageBox.warning(
                self.main_window,
                translate("Cập nhật ứng dụng"),
                translate("Không thể chạy bộ cài cập nhật: ") + message,
            )
            return

        self.logger.info("Starting verified application update.")
        self.shutdown()

    def start_uninstaller(self) -> None:
        uninstaller = Path(sys.executable).resolve().with_name("unins000.exe")
        if not uninstaller.is_file():
            QMessageBox.warning(
                self.main_window,
                translate("Gỡ cài đặt"),
                translate("Không tìm thấy trình gỡ cài đặt trong thư mục ứng dụng."),
            )
            return
        try:
            subprocess.Popen([str(uninstaller), "/SILENT"], cwd=uninstaller.parent)
        except OSError as exc:
            QMessageBox.warning(
                self.main_window,
                translate("Gỡ cài đặt"),
                translate("Không thể mở trình gỡ cài đặt: ") + str(exc),
            )
            return
        self.shutdown()

    def run(self) -> int:
        if self._setup_cancelled:
            return 0
        exit_code = self.application.exec()
        if self._restart_requested:
            command = [sys.executable]
            if not (getattr(sys, "frozen", False) or "__compiled__" in globals()):
                command.append(str(Path(sys.argv[0]).resolve()))
            command.extend(self._qt_args)
            if self._background:
                command.append("--background")
            try:
                subprocess.Popen(command)
            except OSError as exc:
                self.logger.error(f"Application restart failed: {exc}")
                QMessageBox.warning(
                    None,
                    translate("Không thể khởi động lại"),
                    translate("Không thể mở lại ứng dụng: ") + str(exc),
                )
                return 1
        return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="re/read offline desktop translator")
    parser.add_argument("--background", action="store_true", help="start minimized to the system tray")
    parser.add_argument("--ui-language", choices=("vi", "en"), help=argparse.SUPPRESS)
    parser.add_argument("--uninstall-cleanup", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--report-path", help=argparse.SUPPRESS)
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]
    if args.uninstall_cleanup:
        errors = cleanup_installed_data()
        if args.report_path:
            try:
                Path(args.report_path).write_text("\n".join(errors), encoding="utf-8")
            except OSError as exc:
                errors.append(f"Could not write cleanup report {args.report_path}: {exc}")
        elif errors:
            QApplication.instance() or QApplication(sys.argv[:1])
            QMessageBox.warning(None, "re/read · Gỡ cài đặt", "\n".join(errors))
        return 0
    app = RereadDesktopApp(background=args.background, initial_language=args.ui_language)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
