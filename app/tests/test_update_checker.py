import io
import json
import unittest
from unittest.mock import patch

from reread_pyext.update_checker import check_for_update


class UpdateCheckerTests(unittest.TestCase):
    def _release_response(self, tag):
        return io.BytesIO(json.dumps({"tag_name": tag}).encode("utf-8"))

    def test_detects_newer_stable_version_and_builds_release_link(self):
        with patch("reread_pyext.update_checker.urllib.request.urlopen", return_value=self._release_response("v0.1.10")) as urlopen:
            result = check_for_update("0.1.9")

        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "0.1.10")
        self.assertEqual(result.release_url, "https://github.com/nvtruongops/reread-pyext/releases/tag/v0.1.10")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 8.0)

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
