import io
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reread_pyext.update_checker import UpdateCheckResult, check_for_update, download_installer


class UpdateCheckerTests(unittest.TestCase):
    def _release_response(self, tag):
        return io.BytesIO(json.dumps({
            "tag_name": tag,
            "assets": [{
                "name": "reread_pyext_setup.exe",
                "browser_download_url": f"https://github.com/nvtruongops/reread-pyext/releases/download/{tag}/reread_pyext_setup.exe",
                "digest": "sha256:" + hashlib.sha256(b"installer").hexdigest(),
                "size": len(b"installer"),
            }],
        }).encode("utf-8"))

    def test_detects_newer_stable_version_and_builds_release_link(self):
        with patch("reread_pyext.update_checker.urllib.request.urlopen", return_value=self._release_response("v0.1.10")) as urlopen:
            result = check_for_update("0.1.9")

        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "0.1.10")
        self.assertEqual(result.release_url, "https://github.com/nvtruongops/reread-pyext/releases/tag/v0.1.10")
        self.assertEqual(result.installer_url, "https://github.com/nvtruongops/reread-pyext/releases/download/v0.1.10/reread_pyext_setup.exe")
        self.assertEqual(result.installer_sha256, hashlib.sha256(b"installer").hexdigest())
        self.assertEqual(result.installer_size, len(b"installer"))
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 8.0)

    def test_rejects_update_without_sha256_digest(self):
        release = json.loads(self._release_response("v0.1.10").read().decode("utf-8"))
        release["assets"][0]["digest"] = None
        with patch("reread_pyext.update_checker.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(release).encode("utf-8"))):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                check_for_update("0.1.9")

    def test_download_verifies_digest_and_size(self):
        payload = b"verified installer"
        result = UpdateCheckResult(
            latest_version="0.1.10",
            release_url="https://github.com/nvtruongops/reread-pyext/releases/tag/v0.1.10",
            update_available=True,
            installer_url="https://github.com/nvtruongops/reread-pyext/releases/download/v0.1.10/reread_pyext_setup.exe",
            installer_sha256=hashlib.sha256(payload).hexdigest(),
            installer_size=len(payload),
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "reread_pyext.update_checker.urllib.request.urlopen", return_value=io.BytesIO(payload)
        ):
            installer = download_installer(result, directory)
            self.assertEqual(installer.read_bytes(), payload)
            self.assertEqual(installer.suffix, ".exe")
            self.assertTrue(installer.name.startswith("reread-update-"))

    def test_download_deletes_installer_when_digest_does_not_match(self):
        result = UpdateCheckResult(
            latest_version="0.1.10",
            release_url="https://github.com/nvtruongops/reread-pyext/releases/tag/v0.1.10",
            update_available=True,
            installer_url="https://github.com/nvtruongops/reread-pyext/releases/download/v0.1.10/reread_pyext_setup.exe",
            installer_sha256="0" * 64,
            installer_size=3,
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "reread_pyext.update_checker.urllib.request.urlopen", return_value=io.BytesIO(b"bad")
        ):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                download_installer(result, directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_reports_same_version_as_current(self):
        with patch("reread_pyext.update_checker.urllib.request.urlopen", return_value=self._release_response("v0.1.5")):
            result = check_for_update("0.1.5")

        self.assertFalse(result.update_available)

    def test_rejects_release_tag_outside_stable_semver(self):
        with patch("reread_pyext.update_checker.urllib.request.urlopen", return_value=self._release_response("v0.1.6-rc1")):
            with self.assertRaises(ValueError):
                check_for_update("0.1.5")


if __name__ == "__main__":
    unittest.main()
