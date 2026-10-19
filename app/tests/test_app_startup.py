import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import QCoreApplication, QObject, Qt

from reread_pyext import app as desktop_app
from reread_pyext.hook import selection_hook


class AppStartupTests(unittest.TestCase):
    def test_restart_relaunches_source_app_with_background_and_qt_arguments(self):
        app = SimpleNamespace(
            _setup_cancelled=False,
            _restart_requested=True,
            _background=True,
            _qt_args=("-platform", "offscreen"),
            application=SimpleNamespace(exec=Mock(return_value=0)),
            logger=Mock(),
        )

        with patch.object(desktop_app.subprocess, "Popen") as popen:
            self.assertEqual(desktop_app.RereadDesktopApp.run(app), 0)

        popen.assert_called_once_with([
            sys.executable,
            str(Path(sys.argv[0]).resolve()),
            "-platform",
            "offscreen",
            "--background",
        ])

    def test_cancelling_first_run_setup_exits_before_logging_or_kernel_startup(self):
        fake_application = Mock()
        settings = SimpleNamespace(config=SimpleNamespace(setup_complete=False))

        with patch.object(desktop_app, "QApplication") as qt_application, \
             patch.object(desktop_app, "migrate_legacy_data", return_value=[]), \
             patch.object(desktop_app, "SettingsManager", return_value=settings), \
             patch.object(desktop_app, "FirstRunSetupDialog") as setup_dialog, \
             patch.object(desktop_app, "setup_global_logging") as setup_logging, \
             patch.object(desktop_app.RereadDesktopApp, "_start_kernel") as start_kernel:
            qt_application.instance.return_value = fake_application
            setup_dialog.return_value.exec.return_value = desktop_app.QDialog.DialogCode.Rejected

            app = desktop_app.RereadDesktopApp()

        self.assertTrue(app._setup_cancelled)
        self.assertEqual(app.run(), 0)
        setup_dialog.return_value.exec.assert_called_once_with()
        setup_logging.assert_not_called()
        start_kernel.assert_not_called()

    def test_selection_hook_starts_without_waiting_for_translation_kernel(self):
        hook = Mock()
        kernel = Mock()
        kernel.start.side_effect = RuntimeError("Node unavailable")
        signals = SimpleNamespace(kernel_status=Mock())
        logger = Mock()
        app = SimpleNamespace(hook=hook, kernel=kernel, signals=signals, logger=logger)
        threads = []

        class DeferredThread:
            def __init__(self, target, **_kwargs):
                self.target = target

            def start(self):
                threads.append(self)

        with patch.object(desktop_app.threading, "Thread", DeferredThread):
            desktop_app.RereadDesktopApp._start_kernel(app)

        hook.start.assert_called_once_with()
        kernel.start.assert_not_called()
        self.assertEqual(len(threads), 1)

        threads[0].target()

        hook.start.assert_called_once_with()
        signals.kernel_status.emit.assert_called_once_with(
            "Không thể khởi động lõi dịch: Node unavailable", False
        )
        logger.error.assert_called_once_with("Translation kernel startup failed: Node unavailable")

    def test_alt_s_opens_settings_through_queued_app_signal(self):
        qt_app = QCoreApplication.instance() or QCoreApplication([])
        app = desktop_app.RereadDesktopApp.__new__(desktop_app.RereadDesktopApp)
        QObject.__init__(app)
        app.main_window = Mock()
        app.signals = desktop_app.AppSignals(app)
        app.signals.open_settings.connect(app.open_settings, Qt.ConnectionType.QueuedConnection)

        hook = selection_hook.SelectionHook.__new__(selection_hook.SelectionHook)
        hook._running = True
        hook._paused = False
        hook.on_hotkey_settings = app.signals.open_settings.emit
        hook.on_hotkey_dismiss = None
        hook.on_hotkey_pause = None
        hook.on_hotkey_quit = None
        hook.on_hotkey_history = None
        hook._ctrl_c_was_down = False
        hook._ctrl_v_was_down = False
        hook._last_ctrl_c_time = 0.0
        hook._last_ctrl_v_time = 0.0
        hook.settings_mgr = SimpleNamespace(config=SimpleNamespace(
            double_ctrl_c=False,
            double_ctrl_v_history=False,
            enable_history=False,
            auto_drag=False,
            hold_duration_seconds=2.0,
        ))

        def stop_loop(_seconds):
            hook._running = False

        with patch.object(selection_hook, "is_alt_down", return_value=True), \
             patch.object(selection_hook, "is_key_down", side_effect=lambda key: key == 0x53), \
             patch.object(selection_hook, "is_lbutton_down", return_value=False), \
             patch.object(selection_hook.time, "sleep", side_effect=stop_loop):
            hook._monitor_loop()

        qt_app.processEvents()
        app.main_window.show_page.assert_called_once_with(desktop_app.PAGE_SETTINGS)
        app.main_window.showNormal.assert_called_once_with()
        app.main_window.raise_.assert_called_once_with()
        app.main_window.activateWindow.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
