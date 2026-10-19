import tempfile
import unittest
from pathlib import Path

from reread_pyext.config.settings import SettingsManager


class ModelDirectorySettingsTests(unittest.TestCase):
    def test_first_run_setup_creates_empty_model_folder_and_persists_choice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.json"
            model_directory = root / "custom-models"
            settings = SettingsManager(config_path=config_path)

            complete_setup = getattr(settings, "complete_first_run_setup", None)
            completed = complete_setup(model_directory) if complete_setup else False

            self.assertTrue(completed)
            self.assertTrue(model_directory.is_dir())
            self.assertEqual(list(model_directory.iterdir()), [])
            reloaded = SettingsManager(config_path=config_path)
            self.assertEqual(reloaded.config.model_directory, str(model_directory))
            self.assertTrue(reloaded.config.setup_complete)

    def test_first_run_setup_flag_defaults_false_and_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            settings = SettingsManager(config_path=config_path)

            self.assertFalse(getattr(settings.config, "setup_complete", False))
            settings.update(setup_complete=True)

            reloaded = SettingsManager(config_path=config_path)
            self.assertTrue(getattr(reloaded.config, "setup_complete", False))

    def test_custom_model_directory_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            model_directory = Path(temp_dir) / "external-models"

            settings = SettingsManager(config_path=config_path)
            settings.update(model_directory=str(model_directory))

            reloaded = SettingsManager(config_path=config_path)
            self.assertEqual(reloaded.config.model_directory, str(model_directory))


if __name__ == "__main__":
    unittest.main()
