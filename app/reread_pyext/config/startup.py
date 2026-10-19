"""
Windows Startup Service Manager for re/read Python Desktop.
Manages automatic startup on boot via Windows Registry (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run)
and provides tools to register, inspect, and clear auto-launch keys.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None  # Non-Windows fallback


class StartupManager:
    REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    PRIMARY_KEY_NAME = "RereadDesktopService"
    KNOWN_KEY_ALIASES = [
        "RereadDesktopService",
        "re/read Service",
        "RereadDesktop",
        "reread_desktop",
        "RereadService",
    ]

    def __init__(self, root_dir: Optional[Path | str] = None) -> None:
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parent.parent.parent
        else:
            self.root_dir = Path(root_dir)

    @property
    def registry_display_path(self) -> str:
        return f"HKCU\\{self.REG_SUBKEY}"

    def get_default_command(self) -> str:
        """Builds the command used to start the app in background mode at login."""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --background'

        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        wscript = Path(system_root) / "System32" / "wscript.exe"
        vbs_script = self.root_dir / "services" / "windows" / "start_desktop_hidden.vbs"

        if wscript.exists() and vbs_script.exists():
            return f'"{wscript}" //nologo "{vbs_script}"'

        # Fallback to pythonw.exe module execution
        py_exe = Path(sys.executable)
        pyw_exe = py_exe.parent / "pythonw.exe"
        runner = pyw_exe if pyw_exe.exists() else py_exe
        return f'"{runner}" -m reread_pyext.app --background'

    def is_registered(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """Checks if a startup key is registered in HKCU Run registry.

        Returns:
            (is_registered, matched_key_name, registered_command)
        """
        if winreg is None:
            return False, None, None

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_SUBKEY, 0, winreg.KEY_READ) as key:
                # 1. Check known aliases
                for name in self.KNOWN_KEY_ALIASES:
                    try:
                        val, _ = winreg.QueryValueEx(key, name)
                        return True, name, str(val)
                    except FileNotFoundError:
                        continue

                # 2. Enumerate all values to catch any entry pointing to this repository
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, idx)
                        val_str = str(val).lower()
                        if "reread" in val_str or str(self.root_dir).lower() in val_str:
                            return True, name, str(val)
                        idx += 1
                    except OSError:
                        break

        except Exception as e:
            print(f"[StartupManager] Error querying registry: {e}", flush=True)

        return False, None, None

    def register(self, command: Optional[str] = None) -> Tuple[bool, str]:
        """Registers or updates the startup key in HKCU Run registry.

        Returns:
            (success, status_message)
        """
        if winreg is None:
            return False, "Windows Registry is only supported on Windows OS."

        cmd_to_set = command.strip() if command else self.get_default_command()

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.PRIMARY_KEY_NAME, 0, winreg.REG_SZ, cmd_to_set)
            return True, f"Startup key '{self.PRIMARY_KEY_NAME}' registered successfully in {self.registry_display_path}."
        except Exception as e:
            return False, f"Failed to write registry key: {e}"

    def clear_keys(self) -> Tuple[bool, str, int]:
        """Cleans/removes all registered startup keys for re/read service from Windows Registry
        and Windows Startup folder.

        Returns:
            (success, message, count_deleted)
        """
        if winreg is None:
            return False, "Windows Registry is only supported on Windows OS.", 0

        deleted_keys: List[str] = []

        # 1. Clear from HKCU Registry
        try:
            # First collect matching key names
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_SUBKEY, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(key, idx)
                        val_str = str(val).lower()
                        if name in self.KNOWN_KEY_ALIASES or "reread" in val_str or str(self.root_dir).lower() in val_str:
                            deleted_keys.append(name)
                        idx += 1
                    except OSError:
                        break

            # Now delete collected keys
            if deleted_keys:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
                    for name in set(deleted_keys):
                        try:
                            winreg.DeleteValue(key, name)
                        except FileNotFoundError:
                            pass

        except Exception as e:
            print(f"[StartupManager] Registry clear warning: {e}", flush=True)

        # 2. Check and clean Windows Startup folder shortcuts
        shortcut_deleted = 0
        appdata = os.environ.get("APPDATA")
        if appdata:
            startup_dir = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
            if startup_dir.exists():
                for item in startup_dir.glob("*"):
                    if "reread" in item.name.lower():
                        try:
                            item.unlink()
                            shortcut_deleted += 1
                        except Exception:
                            pass

        total_cleaned = len(deleted_keys) + shortcut_deleted
        if total_cleaned > 0:
            msg = f"Successfully cleared {total_cleaned} startup service key(s) from Windows Registry and Startup folder."
            return True, msg, total_cleaned
        else:
            return True, "No registered startup service keys found to delete.", 0
