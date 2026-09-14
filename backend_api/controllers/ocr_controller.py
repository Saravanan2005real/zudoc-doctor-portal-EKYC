"""OCR HTTP routes proxying to the standalone OCR Engine microservice."""
from __future__ import annotations

import httpx
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(tags=["ocr"])
OCR_SERVICE_URL = "http://ocr_engine:5001"

@router.get("/health")
async def ocr_health():
    return {"status": "ok", "service": "ocr_proxy"}

@router.post("/api/v1/ocr")
async def run_ocr(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
):
    raw = await file.read()
    files = {"file": (file.filename or "upload.jpg", raw)}
    data = {"document_type": document_type} if document_type else {}
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{OCR_SERVICE_URL}/api/v1/ocr", files=files, data=data, timeout=300.0)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"OCR Engine unreachable: {e}")

@router.post("/api/v1/live_verify")
async def live_verify(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{OCR_SERVICE_URL}/api/v1/live_verify", json=payload, timeout=300.0)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"OCR Engine unreachable: {e}")

@router.post("/api/v1/live_face_check")
async def live_face_check(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{OCR_SERVICE_URL}/api/v1/live_face_check", json=payload, timeout=300.0)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"OCR Engine unreachable: {e}")
