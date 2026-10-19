"""
Windows global mouse selection and clipboard hook using pywin32.
Native 64-bit memory safety, zero access-violation crashes.

Supported Hotkeys & Triggers:
1. Alt + S: Open/Toggle Settings & Logs Dialog
2. Alt + P: Pause / Resume selection capture (silent)
3. Alt + Q: Quit/Exit the application completely
4. Hold-to-Translate: Hold mouse button for X seconds while selecting text to show translation, release to hide
5. Double Ctrl+C: Translate selected text
6. Double Ctrl+V (Ctrl+V+V): Open Translation History popup (last 5 records)
"""

from __future__ import annotations

import math
import sys
import threading
import time
from typing import Callable, Optional

import win32api
import win32clipboard
import win32con
import win32gui

from ..config.settings import AppConfig, SettingsManager


def get_cursor_pos() -> tuple[int, int]:
    try:
        return win32api.GetCursorPos()
    except Exception:
        return (0, 0)


def is_lbutton_down() -> bool:
    try:
        return bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
    except Exception:
        return False


def is_alt_down() -> bool:
    try:
        return bool(win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000)
    except Exception:
        return False


def is_ctrl_down() -> bool:
    try:
        return bool(win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000)
    except Exception:
        return False


def is_key_down(vk: int) -> bool:
    try:
        return bool(win32api.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def send_ctrl_c() -> None:
    """Simulates pressing and releasing Ctrl + C with proper key delays."""
    try:
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        time.sleep(0.015)
        win32api.keybd_event(0x43, 0, 0, 0)  # 'C' key
        time.sleep(0.035)
        win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.015)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[send_ctrl_c error] {e}", flush=True)


def get_clipboard_text() -> str:
    """Reads unicode text from Windows clipboard safely using pywin32."""
    for _ in range(6):
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    return str(data) if data else ""
                return ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            time.sleep(0.02)
    return ""


def set_clipboard_text(text: str) -> None:
    """Restores text to Windows clipboard safely using pywin32."""
    if not text:
        return
    for _ in range(6):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                break
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            time.sleep(0.02)


def clear_clipboard() -> None:
    for _ in range(6):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                break
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            time.sleep(0.02)


class SelectionHook:
    def __init__(
        self,
        on_selection: Callable[[str, int, int], None],
        on_click_outside: Optional[Callable[[int, int], None]] = None,
        on_mouse_release: Optional[Callable[[], None]] = None,
        on_hotkey_settings: Optional[Callable[[], None]] = None,
        on_hotkey_pause: Optional[Callable[[], None]] = None,
        on_hotkey_quit: Optional[Callable[[], None]] = None,
        on_hotkey_history: Optional[Callable[[], None]] = None,
        on_hotkey_dismiss: Optional[Callable[[], None]] = None,
        settings_mgr: Optional[SettingsManager] = None,
        min_drag_distance: int = 6,
        min_text_len: int = 1,
        max_text_len: int = 3000,
    ) -> None:
        self.on_selection = on_selection
        self.on_click_outside = on_click_outside
        self.on_mouse_release = on_mouse_release
        self.on_hotkey_settings = on_hotkey_settings
        self.on_hotkey_pause = on_hotkey_pause
        self.on_hotkey_quit = on_hotkey_quit
        self.on_hotkey_history = on_hotkey_history
        self.on_hotkey_dismiss = on_hotkey_dismiss
        self.settings_mgr = settings_mgr or SettingsManager()

        self.min_drag_distance = min_drag_distance
        self.min_text_len = min_text_len
        self.max_text_len = max_text_len

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_captured_text = ""
        self._last_captured_time = 0.0

        self._last_ctrl_c_time = 0.0
        self._ctrl_c_was_down = False

        self._last_ctrl_v_time = 0.0
        self._ctrl_v_was_down = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def toggle_pause(self) -> bool:
        self._paused = not self._paused
        return self._paused

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _monitor_loop(self) -> None:
        was_down = False
        start_pos = (0, 0)
        down_start_time = 0.0
        hold_triggered = False

        # Key state tracking to prevent repeated triggers when holding keys
        alt_s_was_down = False
        alt_p_was_down = False
        alt_q_was_down = False
        esc_was_down = False

        print("[SelectionHook] System shortcuts active:", flush=True)
        print("  - Alt + S: Open/Close Settings & Logs dashboard", flush=True)
        print("  - Alt + P: Pause / Resume text selection capture (silent)", flush=True)
        print("  - Alt + Q: Terminate application process", flush=True)
        print("  - Ctrl + V + V: Open Translation History (Last 5)", flush=True)

        while self._running:
            alt_pressed = is_alt_down()

            # Escape dismisses the floating translation card without taking focus.
            esc_pressed = is_key_down(0x1B)
            if esc_pressed and not esc_was_down and self.on_hotkey_dismiss:
                try:
                    self.on_hotkey_dismiss()
                except Exception as e:
                    print(f"[SelectionHook] on_hotkey_dismiss error: {e}", flush=True)
            esc_was_down = esc_pressed

            # 1. Hotkey: Alt + S (Settings & Logs)
            s_pressed = is_key_down(0x53)  # 'S' key
            alt_s = alt_pressed and s_pressed
            if alt_s and not alt_s_was_down:
                print("\n[Hotkey Alt + S] Open Settings & Logs dashboard", flush=True)
                if self.on_hotkey_settings:
                    try:
                        self.on_hotkey_settings()
                    except Exception as e:
                        print(f"[SelectionHook] on_hotkey_settings error: {e}", flush=True)
            alt_s_was_down = alt_s

            # 2. Hotkey: Alt + P (Pause / Resume - Silent)
            p_pressed = is_key_down(0x50)  # 'P' key
            alt_p = alt_pressed and p_pressed
            if alt_p and not alt_p_was_down:
                print("\n[Hotkey Alt + P] Toggle Pause / Resume state", flush=True)
                if self.on_hotkey_pause:
                    try:
                        self.on_hotkey_pause()
                    except Exception as e:
                        print(f"[SelectionHook] on_hotkey_pause error: {e}", flush=True)
            alt_p_was_down = alt_p

            # 3. Hotkey: Alt + Q (Quit / Exit)
            q_pressed = is_key_down(0x51)  # 'Q' key
            alt_q = alt_pressed and q_pressed
            if alt_q and not alt_q_was_down:
                print("\n[Hotkey Alt + Q] Exiting application process...", flush=True)
                if self.on_hotkey_quit:
                    try:
                        self.on_hotkey_quit()
                    except Exception as e:
                        print(f"[SelectionHook] on_hotkey_quit error: {e}", flush=True)
                break
            alt_q_was_down = alt_q

            # If paused, skip mouse and clipboard translation triggers
            if self._paused:
                time.sleep(0.03)
                continue

            cfg = self.settings_mgr.config

            # 4. Double Ctrl+C Trigger
            if cfg.double_ctrl_c:
                ctrl_pressed = is_ctrl_down()
                c_pressed = is_key_down(0x43)  # 'C' key
                ctrl_c = ctrl_pressed and c_pressed
                if ctrl_c and not self._ctrl_c_was_down:
                    now = time.time()
                    if (now - self._last_ctrl_c_time) < 0.45:
                        time.sleep(0.04)
                        clip = get_clipboard_text().strip()
                        if clip and len(clip) >= self.min_text_len:
                            cur_x, cur_y = get_cursor_pos()
                            print(f"[Double Ctrl+C Trigger] Captured selection ({len(clip)} chars)", flush=True)
                            try:
                                self.on_selection(clip, cur_x, cur_y, "double_ctrl_c")
                            except Exception as e:
                                print(f"[SelectionHook] on_selection error: {e}", flush=True)
                    self._last_ctrl_c_time = now
                self._ctrl_c_was_down = ctrl_c

            # 5. Double Ctrl+V Trigger (Translation History)
            if cfg.double_ctrl_v_history and cfg.enable_history:
                ctrl_pressed = is_ctrl_down()
                v_pressed = is_key_down(0x56)  # 'V' key
                ctrl_v = ctrl_pressed and v_pressed
                if ctrl_v and not self._ctrl_v_was_down:
                    now = time.time()
                    if (now - self._last_ctrl_v_time) < 0.45:
                        print("\n[Double Ctrl+V Trigger] Open Translation History", flush=True)
                        if self.on_hotkey_history:
                            try:
                                self.on_hotkey_history()
                            except Exception as e:
                                print(f"[SelectionHook] on_hotkey_history error: {e}", flush=True)
                    self._last_ctrl_v_time = now
                self._ctrl_v_was_down = ctrl_v

            # 6. Mouse Drag Hold-to-Translate Trigger
            down = is_lbutton_down()

            if down and not was_down:
                start_pos = get_cursor_pos()
                down_start_time = time.time()
                last_hold_update_time = down_start_time
                was_down = True
                hold_triggered = False
                self._last_captured_text = ""
                if self.on_click_outside:
                    try:
                        self.on_click_outside(start_pos[0], start_pos[1])
                    except Exception as e:
                        print(f"[SelectionHook] on_click_outside error: {e}", flush=True)

            elif down and was_down:
                # Mouse is being held down
                cur_pos = get_cursor_pos()
                if cfg.auto_drag and not hold_triggered:
                    dx = cur_pos[0] - start_pos[0]
                    dy = cur_pos[1] - start_pos[1]
                    dist = math.hypot(dx, dy)

                    if dist >= self.min_drag_distance:
                        elapsed = time.time() - down_start_time
                        if elapsed >= cfg.hold_duration_seconds:
                            hold_triggered = True
                            last_hold_update_time = time.time()
                            self._trigger_selection_capture(cur_pos[0], cur_pos[1], source="hold_to_translate")

                elif cfg.auto_drag and hold_triggered:
                    # Mouse is still held down: periodically re-read selection (every 1.0s) to update if user dragged more text
                    now = time.time()
                    if (now - last_hold_update_time) >= 1.0:
                        last_hold_update_time = now
                        self._trigger_selection_capture(cur_pos[0], cur_pos[1], source="hold_to_translate")

            elif not down and was_down:
                # Mouse released
                was_down = False
                if hold_triggered:
                    # User released mouse button after hold translation -> hide tooltip
                    if self.on_mouse_release:
                        try:
                            self.on_mouse_release()
                        except Exception as e:
                            print(f"[SelectionHook] on_mouse_release error: {e}", flush=True)
                    hold_triggered = False

            time.sleep(0.02)


    def _trigger_selection_capture(self, mouse_x: int, mouse_y: int, source: str = "mouse") -> None:
        time.sleep(0.06)
        old_clip = get_clipboard_text()
        new_clip = ""
        try:
            clear_clipboard()
            send_ctrl_c()
            time.sleep(0.06)
            new_clip = get_clipboard_text().strip()
        finally:
            if old_clip:
                set_clipboard_text(old_clip)
            else:
                clear_clipboard()

        now = time.time()
        if new_clip and self.min_text_len <= len(new_clip) <= self.max_text_len:
            if new_clip != self._last_captured_text or (now - self._last_captured_time) > 1.0:
                self._last_captured_text = new_clip
                self._last_captured_time = now
                print(f"[{source}] Captured selection ({len(new_clip)} chars)", flush=True)
                self.on_selection(new_clip, mouse_x, mouse_y, source)
