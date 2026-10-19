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
            completed = complete_setup(model_directory, "en") if complete_setup else False

            self.assertTrue(completed)
            self.assertTrue(model_directory.is_dir())
            self.assertEqual(list(model_directory.iterdir()), [])
            reloaded = SettingsManager(config_path=config_path)
            self.assertEqual(reloaded.config.model_directory, str(model_directory))
            self.assertTrue(reloaded.config.setup_complete)
            self.assertEqual(reloaded.config.ui_language, "en")

    def test_first_run_setup_persists_startup_preference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = SettingsManager(config_path=root / "config.json")

            completed = settings.complete_first_run_setup(root / "models", "en", True)

            self.assertTrue(completed)
            self.assertTrue(SettingsManager(config_path=root / "config.json").config.start_on_boot)

    def test_first_run_setup_keeps_startup_preference_when_not_provided(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            settings = SettingsManager(config_path=root / "config.json")
            settings.update(start_on_boot=True)

            settings.complete_first_run_setup(root / "models", "vi")

            self.assertTrue(settings.config.start_on_boot)

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

    def test_missing_or_invalid_ui_language_defaults_to_vietnamese(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text('{"target_lang": "en", "ui_language": "fr"}', encoding="utf-8")

            settings = SettingsManager(config_path=config_path)

            self.assertEqual(settings.config.target_lang, "en")
            self.assertEqual(settings.config.ui_language, "vi")

    def test_legacy_model_directory_marks_setup_complete_when_flag_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text('{"model_directory": "D:/re-read-models"}', encoding="utf-8")

            settings = SettingsManager(config_path=config_path)

            self.assertTrue(settings.config.setup_complete)

    def test_missing_model_directory_keeps_legacy_setup_incomplete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text('{"target_lang": "en"}', encoding="utf-8")

            settings = SettingsManager(config_path=config_path)

            self.assertFalse(settings.config.setup_complete)

    def test_explicit_incomplete_setup_flag_is_preserved_for_legacy_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                '{"model_directory": "D:/re-read-models", "setup_complete": false}',
                encoding="utf-8",
            )

            settings = SettingsManager(config_path=config_path)

            self.assertFalse(settings.config.setup_complete)


if __name__ == "__main__":
    unittest.main()
