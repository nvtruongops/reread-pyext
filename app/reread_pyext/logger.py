"""SQLite-backed logging and stream redirection for the desktop app."""

from __future__ import annotations

import io
import sys
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

from .config.database import database_path, initialize_database, open_database
from .paths import app_data_dir


class AppLogger:
    _instance: Optional[AppLogger] = None
    _lock = threading.Lock()

    def __init__(self, log_file: Optional[Path | str] = None, max_lines: int = 2000) -> None:
        if log_file is None:
            self.log_file = app_data_dir() / "app.log"
        else:
            self.log_file = Path(log_file)

        self.max_lines = max_lines
        self.database_file = database_path(self.log_file.parent)
        self._subscribers: List[Callable[[str], None]] = []
        self._file_lock = threading.Lock()
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        try:
            initialize_database(self.database_file)
            self._import_legacy_logs()
        except Exception as exc:
            print(f"[AppLogger] Error initializing SQLite log storage: {exc}", flush=True)

    @classmethod
    def get_instance(cls) -> AppLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = AppLogger()
            return cls._instance

    def log(self, message: str, level: str = "INFO") -> None:
        now_str = time.strftime("%H:%M:%S")
        line = f"[{now_str}] [{level}] {message}"
        with self._file_lock:
            try:
                with open_database(self.database_file) as database:
                    database.execute("INSERT INTO logs (line) VALUES (?)", (line,))
            except Exception:
                pass

        # Write to original stdout if present and not None
        if self._orig_stdout is not None:
            try:
                self._orig_stdout.write(line + "\n")
                self._orig_stdout.flush()
            except Exception:
                pass

        for sub in list(self._subscribers):
            try:
                sub(line)
            except Exception:
                pass

    def info(self, message: str) -> None:
        self.log(message, level="INFO")

    def warning(self, message: str) -> None:
        self.log(message, level="WARN")

    def error(self, message: str) -> None:
        self.log(message, level="ERROR")

    def get_all_logs(self) -> str:
        with self._file_lock:
            try:
                with open_database(self.database_file) as database:
                    rows = database.execute(
                        "SELECT line FROM logs ORDER BY id DESC LIMIT ?", (self.max_lines,)
                    ).fetchall()
                return "\n".join(row[0] for row in reversed(rows))
            except Exception:
                return ""

    def get_line_count(self) -> int:
        with self._file_lock:
            try:
                with open_database(self.database_file) as database:
                    count = database.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
                return min(count, self.max_lines)
            except Exception:
                return 0

    def clear(self) -> None:
        with self._file_lock:
            try:
                with open_database(self.database_file) as database:
                    database.execute("DELETE FROM logs")
            except Exception:
                pass

    def _import_legacy_logs(self) -> None:
        if not self.log_file.is_file():
            return
        source = f"app_log:{self.log_file.resolve()}"
        try:
            with open_database(self.database_file) as database:
                if database.execute("SELECT 1 FROM imports WHERE source = ?", (source,)).fetchone():
                    return
            lines = self.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            with open_database(self.database_file) as database:
                imported = database.execute(
                    "SELECT 1 FROM imports WHERE source = ?", (source,)
                ).fetchone()
                if imported:
                    return
                database.executemany("INSERT INTO logs (line) VALUES (?)", ((line,) for line in lines))
                database.execute("INSERT INTO imports (source) VALUES (?)", (source,))
        except Exception as exc:
            print(f"[AppLogger] Error importing legacy log: {exc}", flush=True)

    def subscribe(self, callback: Callable[[str], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)


class StreamRedirector(io.TextIOBase):
    """Redirects writes from print() or sys.stderr into AppLogger."""

    def __init__(self, logger: AppLogger, level: str = "INFO") -> None:
        super().__init__()
        self.logger = logger
        self.level = level
        self._line_buf = ""
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        if not s:
            return 0
        with self._lock:
            self._line_buf += s
            while "\n" in self._line_buf:
                line, self._line_buf = self._line_buf.split("\n", 1)
                line = line.strip("\r")
                if line:
                    self.logger.log(line, level=self.level)
        return len(s)

    def flush(self) -> None:
        with self._lock:
            if self._line_buf:
                line = self._line_buf.strip("\r\n")
                if line:
                    self.logger.log(line, level=self.level)
                self._line_buf = ""


def setup_global_logging() -> AppLogger:
    """Configures sys.stdout and sys.stderr redirection to AppLogger."""
    logger = AppLogger.get_instance()
    sys.stdout = StreamRedirector(logger, level="INFO")
    sys.stderr = StreamRedirector(logger, level="ERROR")
    return logger
