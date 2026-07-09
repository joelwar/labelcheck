from __future__ import annotations

import asyncio
import logging
import os
import time
import zipfile
from collections.abc import Awaitable, Callable
from io import BytesIO
from typing import Optional
from xml.etree import ElementTree

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.comparison import compare_fields
from app.extraction import extract_combined_fields, extract_fields
from app.models import Mode, VerifyResponse


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("labelcheck")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
DIRECTLY_SUPPORTED_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}

app = FastAPI(title="TTB Label Verification API")

origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("%s %s %s %sms", request.method, request.url.path, status, duration_ms)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _read_upload(file: Optional[UploadFile], field_name: str) -> tuple[bytes, str]:
    if file is None:
        raise HTTPException(status_code=400, detail=f"{field_name} is required.")

    media_type = file.content_type or ""
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename or field_name} is not a supported file type. Please upload a PDF, PNG, JPG, or DOCX file.",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"{file.filename or field_name} is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{file.filename or field_name} is too large. The limit is {MAX_UPLOAD_MB} MB per file.",
        )
    if media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _docx_to_text(data, file.filename or field_name), "text/plain"
    if media_type not in DIRECTLY_SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="This file type cannot be read by the prototype yet. Please upload a PDF, PNG, JPG, or DOCX file.",
        )
    return data, media_type


def _docx_to_text(data: bytes, filename: str) -> bytes:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        raise HTTPException(status_code=400, detail=f"{filename} could not be read as a DOCX file.")

    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        if text.strip():
            paragraphs.append(text.strip())
    extracted = "\n".join(paragraphs).encode("utf-8")
    if not extracted:
        raise HTTPException(status_code=400, detail=f"{filename} does not contain readable text.")
    return extracted


@app.post("/api/verify", response_model=VerifyResponse)
async def verify(
    mode: Mode = Form(...),
    application_file: Optional[UploadFile] = File(default=None),
    label_file: Optional[UploadFile] = File(default=None),
    combined_file: Optional[UploadFile] = File(default=None),
) -> VerifyResponse:
    started = time.perf_counter()

    if mode == "separate":
        app_upload = await _read_upload(application_file, "application_file")
        label_upload = await _read_upload(label_file, "label_file")
        application_fields, label_fields = await asyncio.gather(
            extract_fields(app_upload[0], app_upload[1], "application"),
            extract_fields(label_upload[0], label_upload[1], "label"),
        )
    else:
        combined_upload = await _read_upload(combined_file, "combined_file")
        application_fields, label_fields = await extract_combined_fields(
            combined_upload[0], combined_upload[1]
        )

    results, overall = compare_fields(application_fields, label_fields)
    return VerifyResponse(
        application_fields=application_fields,
        label_fields=label_fields,
        results=results,
        overall_status=overall,
        processing_time_ms=int((time.perf_counter() - started) * 1000),
    )
