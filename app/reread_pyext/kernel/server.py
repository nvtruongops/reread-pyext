"""
Kernel Server daemon: Exposes the TranslationKernel over a lightweight local REST / JSON API.
Can be started via `python -m reread_pyext.kernel.server --port 8765`.
"""

from __future__ import annotations

import argparse
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from .kernel import TranslationKernel, TranslationResult

app = FastAPI(title="re/read Translation Kernel API", version="0.1.0")
kernel: Optional[TranslationKernel] = None


class TranslateRequest(BaseModel):
    text: str
    timeout: float = 10.0


class TranslateResponse(BaseModel):
    source_text: str
    translated_text: str
    src_lang: str
    tgt_lang: str
    pipeline: list[str]
    duration_ms: float
    error: Optional[str] = None


@app.on_event("startup")
def startup_event():
    global kernel
    kernel = TranslationKernel()
    kernel.start()
    # Preload envi and vien
    kernel.preload_pairs(["envi", "vien"])


@app.on_event("shutdown")
def shutdown_event():
    global kernel
    if kernel:
        kernel.stop()


@app.get("/health")
def health():
    return {"status": "ok", "engine": "bergamot-wasm"}


@app.post("/translate", response_model=TranslateResponse)
def api_translate(req: TranslateRequest):
    global kernel
    if not kernel:
        raise HTTPException(status_code=500, detail="Kernel not initialized")

    result = kernel.translate(req.text, timeout=req.timeout)
    if result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return TranslateResponse(
        source_text=result.source_text,
        translated_text=result.translated_text,
        src_lang=result.src_lang,
        tgt_lang=result.tgt_lang,
        pipeline=result.pipeline,
        duration_ms=result.duration_ms,
        error=result.error,
    )


def run_server(host: str = "127.0.0.1", port: int = 8765):
    uvicorn.run("reread_pyext.kernel.server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="re/read Translation Kernel Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()
    run_server(args.host, args.port)
