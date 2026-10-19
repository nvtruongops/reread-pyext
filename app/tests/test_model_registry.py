import json
import tempfile
import unittest
from pathlib import Path

from reread_pyext.config.model_registry import (
    LANG_NAMES,
    LANG_NAMES_VI,
    ModelPackageInfo,
    ModelRegistryManager,
)


class InstalledModelDetectionTests(unittest.TestCase):
    def test_partial_model_download_is_not_marked_installed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            models = root / "data" / "models"
            package = {
                "pair": "envi",
                "from": "en",
                "to": "vi",
                "downloadBytes": 100,
                "bytes": 200,
                "architecture": "intgemm8",
                "files": [
                    {"role": "model", "url": "https://example.test/model.envi.intgemm.alphas.bin.gz"},
                    {"role": "shortlist", "url": "https://example.test/lex.50.50.envi.s2t.bin.gz"},
                    {"role": "vocab", "url": "https://example.test/vocab.envi.spm.gz"},
                ],
            }
            models.mkdir(parents=True)
            (models / "registry.json").write_text(json.dumps({"models": [package]}), encoding="utf-8")
            installed = models / "envi"
            installed.mkdir()
            (installed / "model.envi.intgemm.alphas.bin").write_bytes(b"model")
            (installed / "vocab.envi.spm").write_bytes(b"vocab")

            manager = ModelRegistryManager(root_dir=root)
            self.assertFalse(manager.get_available_packages()[0].is_installed)

            (installed / "lex.50.50.envi.s2t.bin").write_bytes(b"shortlist")
            self.assertTrue(manager.get_available_packages()[0].is_installed)


class ModelLanguageLabelTests(unittest.TestCase):
    def test_all_registered_languages_have_vietnamese_display_names(self):
        self.assertEqual(set(LANG_NAMES), set(LANG_NAMES_VI))

    def test_model_package_displays_vietnamese_names_with_unknown_code_fallback(self):
        package = ModelPackageInfo(
            pair="vien",
            from_lang="vi",
            to_lang="en",
            from_name="Vietnamese",
            to_name="English",
            download_bytes=0,
            unpacked_bytes=0,
            download_size_mb=0,
            unpacked_size_mb=0,
            architecture="intgemm8",
            is_installed=False,
        )
        self.assertEqual(package.from_display_name, "Tiếng Việt")
        self.assertEqual(package.to_display_name, "Tiếng Anh")

        unknown = ModelPackageInfo(
            pair="xxen",
            from_lang="xx",
            to_lang="en",
            from_name="X language",
            to_name="English",
            download_bytes=0,
            unpacked_bytes=0,
            download_size_mb=0,
            unpacked_size_mb=0,
            architecture="intgemm8",
            is_installed=False,
        )
        self.assertEqual(unknown.from_display_name, "X language")


if __name__ == "__main__":
    unittest.main()
