import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reread_pyext.paths import migrate_legacy_data, models_dir


class LegacyDataMigrationTests(unittest.TestCase):
    def test_copies_legacy_data_without_removing_or_overwriting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy"
            destination = root / "user-data"
            (legacy / "data" / "models" / "envi").mkdir(parents=True)
            (legacy / "data" / "config.json").write_text('{"target_lang":"vi"}', encoding="utf-8")
            (legacy / "data" / "history.json").write_text("[]", encoding="utf-8")
            (legacy / "data" / "models" / "envi" / "model.bin").write_bytes(b"legacy-model")
            (destination / "config.json").parent.mkdir(parents=True)
            (destination / "config.json").write_text('{"target_lang":"en"}', encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with patch("reread_pyext.paths.package_root", return_value=legacy):
                    with patch("reread_pyext.paths.app_data_dir", return_value=destination):
                        copied = migrate_legacy_data()
                        model_dir = destination / "models" / "reread_pyext"
                        self.assertEqual((model_dir / "envi" / "model.bin").read_bytes(), b"legacy-model")
                        shutil.rmtree(model_dir / "envi")
                        copied_again = migrate_legacy_data()

            self.assertEqual(json.loads((destination / "config.json").read_text(encoding="utf-8"))["target_lang"], "en")
            self.assertTrue((destination / "history.json").is_file())
            self.assertFalse((destination / "models" / "reread_pyext" / "envi").exists())
            self.assertTrue((legacy / "data" / "config.json").is_file())
            self.assertTrue((legacy / "data" / "models" / "envi" / "model.bin").is_file())
            self.assertEqual(copied, ["history.json", "models/reread_pyext/envi"])
            self.assertEqual(copied_again, [])


class ModelDirectoryTests(unittest.TestCase):
    def test_uses_configured_model_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            custom = Path(temp_dir) / "portable-models"
            self.assertEqual(models_dir(str(custom)), custom)

    def test_defaults_to_new_app_model_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_data = Path(temp_dir) / "re-read"
            with patch.dict(os.environ, {"REREAD_DATA_DIR": str(app_data)}, clear=True):
                self.assertEqual(models_dir(), app_data / "models" / "reread_pyext")


if __name__ == "__main__":
    unittest.main()
