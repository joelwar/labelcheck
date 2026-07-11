from __future__ import annotations

import asyncio
import logging
import os
import time
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional
from xml.etree import ElementTree

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.comparison import compare_fields, extraction_complete
from app.extraction import extract_combined_fields, extract_fields
from app.models import (
    DecidedBy,
    DecisionRequest,
    ExtractedFields,
    FieldResult,
    Mode,
    SubmissionDetail,
    SubmissionStatus,
    SubmissionSummary,
)


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
STATUS_ORDER = {"to_review": 0, "needs_correction": 1, "approved": 2}


@dataclass
class UploadPayload:
    extraction_bytes: bytes
    extraction_media_type: str
    display_bytes: bytes
    display_media_type: str
    filename: str


@dataclass
class StoredSubmission:
    id: str
    submitted_at: str
    status: SubmissionStatus
    decided_by: DecidedBy
    override_reason: str | None
    decided_at: str | None
    extraction_ok: bool
    extraction_error: str | None
    application_fields: ExtractedFields
    label_fields: ExtractedFields
    field_results: list[FieldResult]
    application_file: UploadPayload
    label_file: UploadPayload
    processing_time_ms: int


app = FastAPI(title="TTB Label Verification API")
SUBMISSIONS: dict[str, StoredSubmission] = {}
NEXT_ID = 1

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


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/submissions", response_model=SubmissionDetail)
async def create_submission(
    mode: Mode = Form(...),
    application_file: Optional[UploadFile] = File(default=None),
    label_file: Optional[UploadFile] = File(default=None),
    combined_file: Optional[UploadFile] = File(default=None),
) -> SubmissionDetail:
    started = time.perf_counter()

    if mode == "separate":
        app_upload = await _read_upload(application_file, "application_file")
        label_upload = await _read_upload(label_file, "label_file")
    else:
        combined_upload = await _read_upload(combined_file, "combined_file")
        app_upload = combined_upload
        label_upload = combined_upload

    application_fields = ExtractedFields()
    label_fields = ExtractedFields()
    field_results: list[FieldResult] = []
    extraction_ok = False
    extraction_error: str | None = None
    status: SubmissionStatus = "to_review"

    try:
        if mode == "separate":
            application_fields, label_fields = await asyncio.gather(
                extract_fields(app_upload.extraction_bytes, app_upload.extraction_media_type, "application"),
                extract_fields(label_upload.extraction_bytes, label_upload.extraction_media_type, "label"),
            )
        else:
            application_fields, label_fields = await extract_combined_fields(
                app_upload.extraction_bytes, app_upload.extraction_media_type
            )

        extraction_ok = extraction_complete(application_fields) and extraction_complete(label_fields)
        if extraction_ok:
            field_results, status = compare_fields(application_fields, label_fields)
        else:
            extraction_error = (
                "The system could not reliably read every required field. "
                "Please review the uploaded documents manually."
            )
    except Exception as exc:
        logger.warning("Extraction failed: %s", exc)
        extraction_error = (
            "The system could not complete automated extraction. "
            "Please review the uploaded documents manually."
        )

    stored = _store_submission(
        status=status,
        extraction_ok=extraction_ok,
        extraction_error=extraction_error,
        application_fields=application_fields,
        label_fields=label_fields,
        field_results=field_results,
        app_upload=app_upload,
        label_upload=label_upload,
        processing_time_ms=int((time.perf_counter() - started) * 1000),
    )
    return _detail(stored)


@app.get("/api/submissions", response_model=list[SubmissionSummary])
async def list_submissions(
    status: SubmissionStatus | None = Query(default=None),
) -> list[SubmissionSummary]:
    submissions = list(SUBMISSIONS.values())
    if status is not None:
        submissions = [submission for submission in submissions if submission.status == status]
    submissions.sort(
        key=lambda submission: (
            STATUS_ORDER[submission.status],
            submission.submitted_at,
        ),
        reverse=False,
    )
    return [_summary(submission) for submission in submissions]


@app.get("/api/submissions/{submission_id}", response_model=SubmissionDetail)
async def get_submission(submission_id: str) -> SubmissionDetail:
    return _detail(_get_submission(submission_id))


@app.post("/api/submissions/{submission_id}/decision", response_model=SubmissionDetail)
async def decide_submission(submission_id: str, decision: DecisionRequest) -> SubmissionDetail:
    submission = _get_submission(submission_id)
    now = _now()

    if decision.action == "confirm":
        if not submission.extraction_ok:
            raise HTTPException(status_code=400, detail="Manual review cases cannot be confirmed.")
        submission.decided_by = "agent_confirmed"
        submission.decided_at = now
        submission.override_reason = None
    elif decision.action == "override":
        if not submission.extraction_ok:
            raise HTTPException(status_code=400, detail="Use manual decision for extraction-failure cases.")
        if decision.new_status not in ("approved", "needs_correction"):
            raise HTTPException(status_code=400, detail="Choose Approved or Needs Correction.")
        if not decision.reason or not decision.reason.strip():
            raise HTTPException(status_code=400, detail="A reason is required when overriding.")
        submission.status = decision.new_status
        submission.decided_by = "agent_override"
        submission.override_reason = decision.reason.strip()
        submission.decided_at = now
    else:
        if submission.extraction_ok:
            raise HTTPException(status_code=400, detail="Manual decisions are only for extraction-failure cases.")
        if decision.new_status not in ("approved", "needs_correction"):
            raise HTTPException(status_code=400, detail="Choose Approved or Needs Correction.")
        submission.status = decision.new_status
        submission.decided_by = "agent_manual"
        submission.override_reason = decision.reason.strip() if decision.reason else None
        submission.decided_at = now

    return _detail(submission)


@app.get("/api/submissions/{submission_id}/files/{file_kind}")
async def get_submission_file(submission_id: str, file_kind: str) -> Response:
    submission = _get_submission(submission_id)
    if file_kind == "application":
        upload = submission.application_file
    elif file_kind == "label":
        upload = submission.label_file
    else:
        raise HTTPException(status_code=404, detail="File not found.")

    headers = {"Content-Disposition": f'inline; filename="{upload.filename}"'}
    return Response(content=upload.display_bytes, media_type=upload.display_media_type, headers=headers)


async def _read_upload(file: Optional[UploadFile], field_name: str) -> UploadPayload:
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

    filename = file.filename or field_name
    if media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        extraction_bytes = _docx_to_text(data, filename)
        return UploadPayload(
            extraction_bytes=extraction_bytes,
            extraction_media_type="text/plain",
            display_bytes=extraction_bytes,
            display_media_type="text/plain; charset=utf-8",
            filename=f"{filename}.txt" if not filename.endswith(".txt") else filename,
        )
    if media_type not in DIRECTLY_SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="This file type cannot be read by the prototype yet. Please upload a PDF, PNG, JPG, or DOCX file.",
        )
    return UploadPayload(
        extraction_bytes=data,
        extraction_media_type=media_type,
        display_bytes=data,
        display_media_type=media_type,
        filename=filename,
    )


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


def _store_submission(
    *,
    status: SubmissionStatus,
    extraction_ok: bool,
    extraction_error: str | None,
    application_fields: ExtractedFields,
    label_fields: ExtractedFields,
    field_results: list[FieldResult],
    app_upload: UploadPayload,
    label_upload: UploadPayload,
    processing_time_ms: int,
) -> StoredSubmission:
    global NEXT_ID
    submission_id = f"sub_{NEXT_ID:04d}"
    NEXT_ID += 1
    stored = StoredSubmission(
        id=submission_id,
        submitted_at=_now(),
        status=status,
        decided_by="system",
        override_reason=None,
        decided_at=None,
        extraction_ok=extraction_ok,
        extraction_error=extraction_error,
        application_fields=application_fields,
        label_fields=label_fields,
        field_results=field_results,
        application_file=app_upload,
        label_file=label_upload,
        processing_time_ms=processing_time_ms,
    )
    SUBMISSIONS[submission_id] = stored
    return stored


def _get_submission(submission_id: str) -> StoredSubmission:
    submission = SUBMISSIONS.get(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return submission


def _summary(submission: StoredSubmission) -> SubmissionSummary:
    return SubmissionSummary(
        id=submission.id,
        brand=_brand(submission),
        submitted_at=submission.submitted_at,
        status=submission.status,
        decided_by=submission.decided_by,
    )


def _detail(submission: StoredSubmission) -> SubmissionDetail:
    return SubmissionDetail(
        id=submission.id,
        submitted_at=submission.submitted_at,
        status=submission.status,
        decided_by=submission.decided_by,
        override_reason=submission.override_reason,
        decided_at=submission.decided_at,
        extraction_ok=submission.extraction_ok,
        extraction_error=submission.extraction_error,
        application_fields=submission.application_fields,
        label_fields=submission.label_fields,
        field_results=submission.field_results,
        application_file_url=f"/api/submissions/{submission.id}/files/application",
        label_file_url=f"/api/submissions/{submission.id}/files/label",
        processing_time_ms=submission.processing_time_ms,
    )


def _brand(submission: StoredSubmission) -> str:
    return (
        submission.application_fields.brand.strip()
        or submission.label_fields.brand.strip()
        or "Unidentified brand"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
