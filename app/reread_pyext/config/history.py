"""SQLite-backed translation history manager."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .database import database_path, initialize_database, open_database
from ..paths import app_data_dir


@dataclass
class HistoryItem:
    source_text: str
    translated_text: str
    src_lang: str
    tgt_lang: str
    timestamp: str  # Formatted as HH:MM:SS
    duration_ms: float = 0.0


class HistoryManager:
    def __init__(self, history_file: Optional[Path | str] = None) -> None:
        if history_file is None:
            self.history_file = app_data_dir() / "history.json"
        else:
            self.history_file = Path(history_file)
        self.database_file = database_path(self.history_file.parent)
        initialize_database(self.database_file)
        self._import_legacy_history()
        self.load()

    def get_items(self) -> List[HistoryItem]:
        return self.load()

    def add_item(
        self,
        source_text: str,
        translated_text: str,
        src_lang: str,
        tgt_lang: str,
        duration_ms: float = 0.0,
    ) -> HistoryItem:
        now_str = time.strftime("%H:%M:%S")
        item = HistoryItem(
            source_text=source_text,
            translated_text=translated_text,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            timestamp=now_str,
            duration_ms=duration_ms,
        )
        with open_database(self.database_file) as database:
            database.execute(
                "INSERT INTO history "
                "(source_text, translated_text, src_lang, tgt_lang, timestamp, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (source_text, translated_text, src_lang, tgt_lang, now_str, duration_ms),
            )
        return item

    def clear(self) -> None:
        with open_database(self.database_file) as database:
            database.execute("DELETE FROM history")

    def restore_items(self, items: List[HistoryItem]) -> None:
        with open_database(self.database_file) as database:
            database.execute("DELETE FROM history")
            database.executemany(
                "INSERT INTO history "
                "(source_text, translated_text, src_lang, tgt_lang, timestamp, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        item.source_text,
                        item.translated_text,
                        item.src_lang,
                        item.tgt_lang,
                        item.timestamp,
                        item.duration_ms,
                    )
                    for item in reversed(items)
                ],
            )

    def clear_all(self) -> None:
        self.clear()

    def load(self) -> List[HistoryItem]:
        try:
            with open_database(self.database_file) as database:
                rows = database.execute(
                    "SELECT source_text, translated_text, src_lang, tgt_lang, timestamp, duration_ms "
                    "FROM history ORDER BY id DESC"
                ).fetchall()
            return [
                HistoryItem(
                    source_text=row[0],
                    translated_text=row[1],
                    src_lang=row[2],
                    tgt_lang=row[3],
                    timestamp=row[4],
                    duration_ms=float(row[5]),
                )
                for row in rows
            ]
        except Exception as e:
            print(f"[HistoryManager] Error loading history: {e}", flush=True)
            return []

    def _import_legacy_history(self) -> None:
        if not self.history_file.is_file():
            return
        source = f"history_json:{self.history_file.resolve()}"
        try:
            with open_database(self.database_file) as database:
                if database.execute("SELECT 1 FROM imports WHERE source = ?", (source,)).fetchone():
                    return
            with self.history_file.open("r", encoding="utf-8") as legacy_file:
                items = json.load(legacy_file)
            if not isinstance(items, list):
                raise ValueError("History JSON must contain a list")
            rows = [
                (
                    item.get("source_text", ""),
                    item.get("translated_text", ""),
                    item.get("src_lang", "en"),
                    item.get("tgt_lang", "vi"),
                    item.get("timestamp", ""),
                    float(item.get("duration_ms", 0.0)),
                )
                for item in items
            ]
            with open_database(self.database_file) as database:
                imported = database.execute(
                    "SELECT 1 FROM imports WHERE source = ?", (source,)
                ).fetchone()
                if imported:
                    return
                database.executemany(
                    "INSERT INTO history "
                    "(source_text, translated_text, src_lang, tgt_lang, timestamp, duration_ms) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    reversed(rows),
                )
                database.execute("INSERT INTO imports (source) VALUES (?)", (source,))
        except Exception as e:
            print(f"[HistoryManager] Error importing legacy history: {e}", flush=True)
