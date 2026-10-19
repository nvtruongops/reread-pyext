"""
Translation Kernel supervisor.
Manages the offline translation engine worker, language detection,
reverse translation routing, and batching.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..paths import migrate_legacy_data, models_dir as default_models_dir, resource_path

from .lang_detect import determine_translation_route


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    src_lang: str
    tgt_lang: str
    pipeline: List[str]
    duration_ms: float
    error: Optional[str] = None


class TranslationKernel:
    def __init__(self, node_executable: str = "node", models_dir: Path | str | None = None) -> None:
        self.node_executable = node_executable
        self._migrate_on_start = models_dir is None
        self.models_dir = Path(models_dir) if models_dir is not None else default_models_dir()
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._pending: Dict[int, tuple[threading.Event, Dict]] = {}
        self._seq = 0
        self._ready_event = threading.Event()
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None

    def start(self, timeout: float = 15.0) -> bool:
        """Starts the translation worker subprocess and waits for the ready signal."""
        if self._migrate_on_start:
            migrate_legacy_data()
        worker_script = resource_path("reread_pyext", "kernel", "bergamot_worker.cjs")
        if not worker_script.exists():
            raise FileNotFoundError(f"Worker script not found at {worker_script}")

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        worker_env = os.environ.copy()
        worker_env["REREAD_MODELS_DIR"] = str(self.models_dir)
        self._proc = subprocess.Popen(
            [self.node_executable, str(worker_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=worker_env,
            creationflags=creationflags,
        )

        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

        if not self._ready_event.wait(timeout=timeout):
            self.stop()
            raise TimeoutError("Translation kernel worker failed to become ready within timeout.")

        return True

    def _reader_loop(self) -> None:
        if not self._proc or not self._proc.stdout:
            return

        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except Exception:
                continue

            msg_type = data.get("type")
            if msg_type == "ready":
                self._ready_event.set()
                continue

            req_id = data.get("id")
            if req_id is not None:
                with self._lock:
                    pending_item = self._pending.get(req_id)
                if pending_item:
                    event, result_box = pending_item
                    result_box.update(data)
                    event.set()

    def translate(
        self,
        text: str,
        timeout: float = 10.0,
        reverse_vi_to_en: bool = True,
        pivot_cjk: bool = True,
        target_lang: str = "vi",
    ) -> TranslationResult:
        """
        Translates text with auto-routing based on target_lang:
        - target 'vi': Foreign -> vi; vi -> en
        - target 'en': Foreign -> en; en -> vi
        - target 'T' (ru, zh, ja, etc.): Text -> English -> T; T -> English
        """
        trimmed = text.strip()
        if not trimmed:
            return TranslationResult(
                source_text=text,
                translated_text="",
                src_lang="en",
                tgt_lang=target_lang or "vi",
                pipeline=[],
                duration_ms=0.0,
            )

        if not self._running or not self._proc or not self._proc.stdin:
            raise RuntimeError("Translation kernel is not running. Call start() first.")

        src_lang, tgt_lang, steps = determine_translation_route(
            trimmed,
            reverse_vi_to_en=reverse_vi_to_en,
            pivot_cjk=pivot_cjk,
            target_lang=target_lang,
        )

        pipeline_pairs = [f"{s[0]}{s[1]}" for s in steps]

        if not pipeline_pairs:
            return TranslationResult(
                source_text=text,
                translated_text="",
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                pipeline=[],
                duration_ms=0.0,
            )

        with self._lock:
            self._seq += 1
            req_id = self._seq
            event = threading.Event()
            result_box: Dict = {}
            self._pending[req_id] = (event, result_box)

        req_payload = {
            "id": req_id,
            "action": "translate",
            "pipeline": pipeline_pairs,
            "texts": [trimmed],
        }

        try:
            with self._lock:
                self._proc.stdin.write(json.dumps(req_payload) + "\n")
                self._proc.stdin.flush()
        except Exception as e:
            with self._lock:
                self._pending.pop(req_id, None)
            return TranslationResult(
                source_text=text,
                translated_text="",
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                pipeline=pipeline_pairs,
                duration_ms=0.0,
                error=f"Worker write error: {e}",
            )

        if not event.wait(timeout=timeout):
            with self._lock:
                self._pending.pop(req_id, None)
            return TranslationResult(
                source_text=text,
                translated_text="",
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                pipeline=pipeline_pairs,
                duration_ms=0.0,
                error="Translation request timed out.",
            )

        with self._lock:
            self._pending.pop(req_id, None)

        if result_box.get("type") == "error":
            return TranslationResult(
                source_text=text,
                translated_text="",
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                pipeline=pipeline_pairs,
                duration_ms=0.0,
                error=result_box.get("message", "Unknown translation error"),
            )

        results = result_box.get("results", [])
        translated_str = results[0] if results else ""
        duration = float(result_box.get("durationMs", 0.0))

        return TranslationResult(
            source_text=text,
            translated_text=translated_str,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            pipeline=pipeline_pairs,
            duration_ms=duration,
        )

    def preload_pairs(self, pairs: List[str]) -> None:
        """Warms up model weights into memory ahead of time."""
        for p in pairs:
            if not self._proc or not self._proc.stdin:
                break
            with self._lock:
                self._seq += 1
                req_id = self._seq
            payload = {"id": req_id, "action": "preload", "pair": p}
            with self._lock:
                self._proc.stdin.write(json.dumps(payload) + "\n")
                self._proc.stdin.flush()

    def stop(self) -> None:
        """Terminates the worker process gracefully."""
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
