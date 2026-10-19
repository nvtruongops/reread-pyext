"""Shared SQLite storage for local translation history and activity logs."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..paths import app_data_dir


DATABASE_NAME = "reread.sqlite3"


def database_path(data_dir: Path | str | None = None) -> Path:
    return Path(data_dir) / DATABASE_NAME if data_dir is not None else app_data_dir() / DATABASE_NAME


@contextmanager
def open_database(path: Path | str) -> Iterator[sqlite3.Connection]:
    database_file = Path(path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_file, timeout=5)
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(path: Path | str) -> None:
    with open_database(path) as database:
        database.execute("PRAGMA journal_mode = WAL")
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                src_lang TEXT NOT NULL,
                tgt_lang TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_ms REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS imports (
                source TEXT PRIMARY KEY,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
