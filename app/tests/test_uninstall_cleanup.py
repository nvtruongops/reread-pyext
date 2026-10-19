import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reread_pyext.uninstall_cleanup import cleanup_installed_data, cleanup_user_data


class UninstallCleanupTests(unittest.TestCase):
    def _registry(self, path: Path) -> Path:
        path.write_text(json.dumps({"models": [{
            "pair": "envi",
            "files": [
                {"url": "https://models.example/model.envi.bin.gz"},
                {"url": "https://models.example/vocab.envi.spm.gz"},
            ],
        }]}), encoding="utf-8")
        return path

    def test_removes_app_data_and_registered_model_files_but_keeps_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "local" / "re-read"
            app_data.mkdir(parents=True)
            (app_data / "history.sqlite3").write_text("history", encoding="utf-8")
            model_root = root / "custom-models"
            pair_dir = model_root / "envi"
            pair_dir.mkdir(parents=True)
            for name in ("model.envi.bin", "model.envi.bin.gz", "vocab.envi.spm", "vocab.envi.spm.gz"):
                (pair_dir / name).write_bytes(b"model")
            (pair_dir / "notes.txt").write_text("keep", encoding="utf-8")
            registry = self._registry(root / "registry.json")

            errors = cleanup_user_data(app_data, model_root, registry)

            self.assertEqual(errors, [])
            self.assertFalse(app_data.exists())
            self.assertEqual(sorted(path.name for path in pair_dir.iterdir()), ["notes.txt"])
            self.assertTrue(model_root.is_dir())
            self.assertEqual((pair_dir / "notes.txt").read_text(encoding="utf-8"), "keep")

    def test_refuses_to_delete_app_data_root_that_is_a_reparse_point(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "re-read"
            app_data.mkdir()
            (app_data / "keep.txt").write_text("keep", encoding="utf-8")
            registry = self._registry(root / "registry.json")

            with patch("reread_pyext.uninstall_cleanup._is_reparse_point", return_value=True):
                errors = cleanup_user_data(app_data, None, registry)

            self.assertTrue(errors)
            self.assertEqual((app_data / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_model_directory_inside_app_data_is_removed_with_app_data_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "re-read"
            model_root = app_data / "models" / "reread_pyext"
            (model_root / "envi").mkdir(parents=True)
            (model_root / "envi" / "model.envi.bin").write_bytes(b"model")
            registry = self._registry(root / "registry.json")

            errors = cleanup_user_data(app_data, model_root, registry)

            self.assertEqual(errors, [])
            self.assertFalse(app_data.exists())

    def test_leaves_reparse_point_custom_model_directory_untouched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "re-read"
            app_data.mkdir()
            model_root = root / "custom-models"
            pair_dir = model_root / "envi"
            pair_dir.mkdir(parents=True)
            model_file = pair_dir / "model.envi.bin"
            model_file.write_bytes(b"model")
            registry = self._registry(root / "registry.json")

            def is_reparse_point(path):
                return Path(path) == model_root

            with patch("reread_pyext.uninstall_cleanup._is_reparse_point", side_effect=is_reparse_point):
                errors = cleanup_user_data(app_data, model_root, registry)

            self.assertTrue(errors)
            self.assertTrue(model_file.is_file())

    def test_skips_relative_custom_model_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "re-read"
            app_data.mkdir()
            registry = self._registry(root / "registry.json")

            errors = cleanup_user_data(app_data, "relative-models", registry)

            self.assertTrue(any("not absolute" in error for error in errors))

    def test_installed_cleanup_ignores_override_and_removes_data_when_config_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_data = root / "local" / "re-read"
            app_data.mkdir(parents=True)
            (app_data / "config.json").write_text("{invalid", encoding="utf-8")
            override = root / "development-data"
            override.mkdir()
            (override / "keep.txt").write_text("keep", encoding="utf-8")
            registry = self._registry(root / "registry.json")

            with patch.dict("os.environ", {"REREAD_DATA_DIR": str(override)}):
                with patch("reread_pyext.uninstall_cleanup.canonical_app_data_dir", return_value=app_data):
                    with patch("reread_pyext.uninstall_cleanup.resource_path", return_value=registry):
                        errors = cleanup_installed_data()

            self.assertTrue(any("Could not read app settings" in error for error in errors))
            self.assertFalse(app_data.exists())
            self.assertEqual((override / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
