import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from reread_pyext.config.history import HistoryManager
from reread_pyext.logger import AppLogger


class SQLiteStorageTests(unittest.TestCase):
    def test_imports_legacy_logs_and_persists_every_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_file = Path(temp_dir) / "app.log"
            legacy_text = "[10:00:00] [INFO] legacy one\n[10:00:01] [WARN] legacy two\n"
            legacy_file.write_text(legacy_text, encoding="utf-8")

            logger = AppLogger(log_file=legacy_file, max_lines=1)
            self.assertEqual(logger.get_all_logs(), "[10:00:01] [WARN] legacy two")
            logger.info("new entry")
            self.assertEqual(logger.get_line_count(), 1)
            self.assertTrue(logger.get_all_logs().endswith("[INFO] new entry"))

            reopened = AppLogger(log_file=legacy_file, max_lines=2)
            stored_lines = reopened.get_all_logs().splitlines()
            self.assertEqual(len(stored_lines), 2)
            self.assertEqual(stored_lines[0], "[10:00:01] [WARN] legacy two")
            self.assertTrue(stored_lines[-1].endswith("[INFO] new entry"))
            self.assertEqual(legacy_file.read_text(encoding="utf-8"), legacy_text)

            with closing(sqlite3.connect(reopened.database_file)) as database:
                self.assertEqual(database.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 3)

            reopened.clear()
            self.assertEqual(reopened.get_all_logs(), "")
            self.assertEqual(AppLogger(log_file=legacy_file).get_all_logs(), "")

    def test_history_and_logs_share_the_app_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data = Path(temp_dir)
            history = HistoryManager(history_file=data / "history.json")
            logger = AppLogger(log_file=data / "app.log")
            history.add_item("one", "một", "en", "vi")
            logger.info("one log")

            self.assertEqual(history.database_file, logger.database_file)
            with closing(sqlite3.connect(history.database_file)) as database:
                self.assertEqual(database.execute("SELECT COUNT(*) FROM history").fetchone()[0], 1)
                self.assertEqual(database.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
