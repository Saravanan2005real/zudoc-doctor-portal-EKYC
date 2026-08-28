"""OCR HTTP routes on the same FastAPI process (port 8080)."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from ocr.inproc import post_live_verify, post_ocr

router = APIRouter(tags=["ocr"])


@router.get("/health")
async def ocr_health():
    return {"status": "ok", "service": "ocr"}


@router.post("/api/v1/ocr")
async def run_ocr(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
):
    raw = await file.read()
    code, data = await asyncio.to_thread(post_ocr, raw, file.filename or "upload.jpg", document_type)
    return JSONResponse(content=data, status_code=code)


@router.post("/api/v1/live_verify")
async def live_verify(request: Request):
    payload = await request.json()
    code, data = await asyncio.to_thread(post_live_verify, payload)
    return JSONResponse(content=data, status_code=code)
