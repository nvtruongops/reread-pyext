from contextlib import redirect_stdout
from io import StringIO
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from reread_pyext.hook import selection_hook


class SelectionHookClipboardTests(unittest.TestCase):
    def make_hook(self, on_selection):
        hook = selection_hook.SelectionHook.__new__(selection_hook.SelectionHook)
        hook.min_text_len = 1
        hook.max_text_len = 3000
        hook._last_captured_text = ""
        hook._last_captured_time = 0.0
        hook.on_selection = on_selection
        return hook

    def test_restores_existing_text_clipboard_after_valid_capture(self):
        captured = []
        restored = []
        hook = self.make_hook(lambda *args: captured.append(args))

        with patch.object(selection_hook, "get_clipboard_text", side_effect=["old clipboard", "selected text"]), \
             patch.object(selection_hook, "set_clipboard_text", side_effect=restored.append), \
             patch.object(selection_hook, "clear_clipboard"), \
             patch.object(selection_hook, "send_ctrl_c"), \
             patch.object(selection_hook.time, "sleep"):
            hook._trigger_selection_capture(10, 20)

        self.assertEqual(captured[0], ("selected text", 10, 20, "mouse"))
        self.assertEqual(restored, ["old clipboard"])

    def test_leaves_clipboard_empty_after_valid_capture_when_it_started_empty(self):
        hook = self.make_hook(lambda *_args: None)

        with patch.object(selection_hook, "get_clipboard_text", side_effect=["", "selected text"]), \
             patch.object(selection_hook, "set_clipboard_text") as restore, \
             patch.object(selection_hook, "clear_clipboard") as clear, \
             patch.object(selection_hook, "send_ctrl_c"), \
             patch.object(selection_hook.time, "sleep"):
            hook._trigger_selection_capture(10, 20)

        restore.assert_not_called()
        self.assertEqual(clear.call_count, 2)

    def test_does_not_print_captured_text(self):
        hook = self.make_hook(lambda *_args: None)
        output = StringIO()

        with patch.object(selection_hook, "get_clipboard_text", side_effect=["", "private selection"]), \
             patch.object(selection_hook, "clear_clipboard"), \
             patch.object(selection_hook, "send_ctrl_c"), \
             patch.object(selection_hook.time, "sleep"), \
             redirect_stdout(output):
            hook._trigger_selection_capture(10, 20)

        self.assertNotIn("private selection", output.getvalue())

    def test_double_ctrl_c_does_not_print_clipboard_text(self):
        captured = []
        hook = self.make_hook(lambda *args: captured.append(args))
        hook._running = True
        hook._paused = False
        hook._last_ctrl_c_time = 0.9
        hook._ctrl_c_was_down = False
        hook._last_ctrl_v_time = 0.0
        hook._ctrl_v_was_down = False
        hook.settings_mgr = SimpleNamespace(config=SimpleNamespace(
            double_ctrl_c=True,
            double_ctrl_v_history=False,
            enable_history=False,
            auto_drag=False,
            hold_duration_seconds=2.0,
        ))
        output = StringIO()

        def stop_loop(_seconds):
            hook._running = False

        with patch.object(selection_hook, "is_alt_down", return_value=False), \
             patch.object(selection_hook, "is_key_down", side_effect=lambda key: key == 0x43), \
             patch.object(selection_hook, "is_ctrl_down", return_value=True), \
             patch.object(selection_hook, "is_lbutton_down", return_value=False), \
             patch.object(selection_hook, "get_clipboard_text", return_value="private selection"), \
             patch.object(selection_hook, "get_cursor_pos", return_value=(10, 20)), \
             patch.object(selection_hook.time, "time", return_value=1.0), \
             patch.object(selection_hook.time, "sleep", side_effect=stop_loop), \
             redirect_stdout(output):
            hook._monitor_loop()

        self.assertEqual(captured[0][0], "private selection")
        self.assertNotIn("private selection", output.getvalue())


if __name__ == "__main__":
    unittest.main()
