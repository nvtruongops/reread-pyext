import json
import tempfile
import unittest
from pathlib import Path

from reread_pyext.config.history import HistoryManager


class HistoryRestoreTests(unittest.TestCase):
    def test_restores_cleared_items_and_persists_them(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            history = HistoryManager(history_file=path)
            history.add_item("hello", "xin chào", "en", "vi", 12)
            removed = history.get_items()
            history.clear()

            history.restore_items(removed)
            restored = HistoryManager(history_file=path).get_items()

        self.assertEqual(restored, removed)

    def test_imports_legacy_history_and_retains_all_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            legacy = [
                {
                    "source_text": f"old-{index}",
                    "translated_text": f"translated-{index}",
                    "src_lang": "en",
                    "tgt_lang": "vi",
                    "timestamp": f"10:00:0{index}",
                    "duration_ms": float(index),
                }
                for index in range(7)
            ]
            path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")

            history = HistoryManager(history_file=path)
            self.assertEqual(len(history.get_items()), 7)
            self.assertEqual(history.get_items()[0].source_text, "old-0")
            history.add_item("new", "mới", "en", "vi")

            reopened = HistoryManager(history_file=path)
            self.assertEqual(len(reopened.get_items()), 8)
            self.assertEqual(reopened.get_items()[0].source_text, "new")
            self.assertEqual(reopened.get_items()[1].source_text, "old-0")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), legacy)


if __name__ == "__main__":
    unittest.main()
