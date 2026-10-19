import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reread_pyext.config.startup import StartupManager


class StartupCommandTests(unittest.TestCase):
    def test_default_command_uses_hidden_desktop_launcher(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            system_root = root / "Windows"
            wscript = system_root / "System32" / "wscript.exe"
            wscript.parent.mkdir(parents=True)
            wscript.touch()
            launcher = root / "services" / "windows" / "start_desktop_hidden.vbs"
            launcher.parent.mkdir(parents=True)
            launcher.touch()

            with patch.dict(os.environ, {"SystemRoot": str(system_root)}):
                with patch("reread_pyext.config.startup.sys.frozen", False, create=True):
                    command = StartupManager(root).get_default_command()

        self.assertIn(str(wscript), command)
        self.assertIn(str(launcher), command)
        self.assertNotIn("run_desktop.vbs", command)


if __name__ == "__main__":
    unittest.main()
