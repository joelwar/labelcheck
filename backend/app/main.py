from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional
from xml.etree import ElementTree

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageDraw
from pdf2image import convert_from_bytes

from app.comparison import compare_fields
from app.extraction import extract_fields
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
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SEED_DATA_DIR = Path(__file__).resolve().parents[1] / "seed_data"


@dataclass
class PageImage:
    data: bytes
    media_type: str
    filename: str


@dataclass
class UploadPayload:
    extraction_bytes: bytes
    extraction_media_type: str
    display_bytes: bytes
    display_media_type: str
    filename: str
    page_images: list[PageImage]


@dataclass
class StoredSubmission:
    id: str
    applicant_name: str
    applicant_email: str
    seed_key: str | None
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
SEEDED_KEYS: set[str] = set()
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


@app.on_event("startup")
async def seed_on_startup() -> None:
    if SUBMISSIONS:
        return
    created = await seed_submissions()
    if created:
        logger.info("Loaded %s seed submissions.", len(created))


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
    applicant_name: str = Form(...),
    applicant_email: str = Form(...),
    application_file: Optional[UploadFile] = File(default=None),
    label_file: Optional[UploadFile] = File(default=None),
    combined_file: Optional[UploadFile] = File(default=None),
) -> SubmissionDetail:
    applicant_name = _validate_required_text(applicant_name, "Applicant / company name")
    applicant_email = _validate_email(applicant_email)

    process_mode: Mode = "separate"
    if mode == "separate":
        app_upload = await _read_upload(application_file, "application_file")
        label_upload = await _read_upload(label_file, "label_file")
    else:
        combined_upload = await _read_upload(combined_file, "combined_file")
        app_upload, label_upload = _split_combined_upload(combined_upload)

    stored = await _process_submission(
        mode=process_mode,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        app_upload=app_upload,
        label_upload=label_upload,
    )
    return _detail(stored)


@app.post("/api/seed")
async def seed_now() -> dict[str, object]:
    created = await seed_submissions()
    return {
        "created": len(created),
        "submissions": [{"id": item.id, "status": item.status, "brand": _brand(item)} for item in created],
    }


async def seed_submissions() -> list[StoredSubmission]:
    created: list[StoredSubmission] = []
    if not SEED_DATA_DIR.exists():
        logger.info("Seed data directory not found: %s", SEED_DATA_DIR)
        return created

    for folder in sorted(path for path in SEED_DATA_DIR.iterdir() if path.is_dir()):
        seed_key = folder.name
        if seed_key in SEEDED_KEYS or any(item.seed_key == seed_key for item in SUBMISSIONS.values()):
            continue

        application_path = folder / "application_form.pdf"
        label_path = folder / "label_image.png"
        if not application_path.exists() or not label_path.exists():
            logger.info("Skipping seed folder %s; expected application_form.pdf and label_image.png.", folder.name)
            continue

        metadata = _seed_metadata(folder)
        try:
            stored = await _process_submission(
                mode="separate",
                applicant_name=metadata["applicant_name"],
                applicant_email=metadata["applicant_email"],
                app_upload=_read_seed_file(application_path, "application/pdf"),
                label_upload=_read_seed_file(label_path, "image/png"),
                seed_key=seed_key,
            )
            created.append(stored)
        except Exception as exc:
            logger.warning("Seed folder %s failed: %s", folder.name, exc)
    return created


def _seed_metadata(folder: Path) -> dict[str, str]:
    metadata_path = folder / "metadata.json"
    fallback = {
        "applicant_name": f"Sample Submission - {folder.name}",
        "applicant_email": "demo@example.com",
    }
    if not metadata_path.exists():
        return fallback
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return {
            "applicant_name": _validate_required_text(
                str(payload.get("applicant_name") or fallback["applicant_name"]),
                "Applicant / company name",
            ),
            "applicant_email": _validate_email(str(payload.get("applicant_email") or fallback["applicant_email"])),
        }
    except Exception as exc:
        logger.warning("Using fallback metadata for %s: %s", folder.name, exc)
        return fallback


async def _process_submission(
    *,
    mode: Mode,
    applicant_name: str,
    applicant_email: str,
    app_upload: UploadPayload,
    label_upload: UploadPayload,
    seed_key: str | None = None,
) -> StoredSubmission:
    started = time.perf_counter()
    application_fields = ExtractedFields()
    label_fields = ExtractedFields()
    field_results: list[FieldResult] = []
    extraction_ok = False
    extraction_error: str | None = None
    status: SubmissionStatus = "to_review"

    try:
        if mode == "separate":
            (application_fields, app_error), (label_fields, label_error) = await asyncio.gather(
                _safe_extract_fields(app_upload, "application"),
                _safe_extract_fields(label_upload, "label"),
            )
            if app_error:
                logger.warning("Application extraction failed: %s", app_error)
            if label_error:
                logger.warning("Label extraction failed: %s", label_error)
        else:
            raise RuntimeError("Unsupported processing mode.")

        if _has_readable_fields(application_fields) or _has_readable_fields(label_fields):
            extraction_ok = True
            field_results, status = compare_fields(application_fields, label_fields)
        else:
            status = "to_review"
            extraction_error = (
                "The system could not read usable field data from one or more uploaded documents. "
                "Please review the files manually."
            )
    except Exception as exc:
        logger.warning("Extraction failed: %s", exc)
        status = "to_review"
        extraction_error = (
            "The system could not read usable field data from one or more uploaded documents. "
            "Please review the files manually."
        )

    stored = _store_submission(
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        seed_key=seed_key,
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
    return stored


async def _safe_extract_fields(
    upload: UploadPayload, kind: Literal["application", "label"]
) -> tuple[ExtractedFields, str | None]:
    try:
        return await extract_fields(upload.extraction_bytes, upload.extraction_media_type, kind), None
    except Exception as exc:
        return ExtractedFields(), str(exc)


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
    upload = _file_for_kind(submission, file_kind)

    headers = {"Content-Disposition": f'inline; filename="{upload.filename}"'}
    return Response(content=upload.display_bytes, media_type=upload.display_media_type, headers=headers)


@app.get("/api/submissions/{submission_id}/files/{file_kind}/page/{page_number}")
async def get_submission_page_image(submission_id: str, file_kind: str, page_number: int) -> Response:
    submission = _get_submission(submission_id)
    upload = _file_for_kind(submission, file_kind)
    if page_number < 1 or page_number > len(upload.page_images):
        raise HTTPException(status_code=404, detail="Page not found.")
    page = upload.page_images[page_number - 1]
    headers = {"Content-Disposition": f'inline; filename="{page.filename}"'}
    return Response(content=page.data, media_type=page.media_type, headers=headers)


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
        display_name = f"{filename}.txt" if not filename.endswith(".txt") else filename
        return UploadPayload(
            extraction_bytes=extraction_bytes,
            extraction_media_type="text/plain",
            display_bytes=extraction_bytes,
            display_media_type="text/plain; charset=utf-8",
            filename=display_name,
            page_images=_text_pages(extraction_bytes, display_name),
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
        page_images=_page_images(data, media_type, filename),
    )


def _split_combined_upload(upload: UploadPayload) -> tuple[UploadPayload, UploadPayload]:
    if upload.extraction_media_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Combined submissions must be uploaded as a PDF.")
    if len(upload.page_images) < 2:
        raise HTTPException(
            status_code=400,
            detail="Combined submissions must include at least two pages: page 1 application form, page 2 label image.",
        )

    stem = Path(upload.filename).stem or "combined"
    return (
        _page_upload(upload.page_images[0], f"{stem}-application-page-1.png"),
        _page_upload(upload.page_images[1], f"{stem}-label-page-2.png"),
    )


def _page_upload(page: PageImage, filename: str) -> UploadPayload:
    page_image = PageImage(data=page.data, media_type=page.media_type, filename=filename)
    return UploadPayload(
        extraction_bytes=page.data,
        extraction_media_type=page.media_type,
        display_bytes=page.data,
        display_media_type=page.media_type,
        filename=filename,
        page_images=[page_image],
    )


def _read_seed_file(path: Path, media_type: str) -> UploadPayload:
    data = path.read_bytes()
    return UploadPayload(
        extraction_bytes=data,
        extraction_media_type=media_type,
        display_bytes=data,
        display_media_type=media_type,
        filename=path.name,
        page_images=_page_images(data, media_type, path.name),
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
    applicant_name: str,
    applicant_email: str,
    seed_key: str | None,
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
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        seed_key=seed_key,
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
    if seed_key:
        SEEDED_KEYS.add(seed_key)
    return stored


def _get_submission(submission_id: str) -> StoredSubmission:
    submission = SUBMISSIONS.get(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")
    return submission


def _summary(submission: StoredSubmission) -> SubmissionSummary:
    return SubmissionSummary(
        id=submission.id,
        applicant_name=submission.applicant_name,
        applicant_email=submission.applicant_email,
        brand=_brand(submission),
        submitted_at=submission.submitted_at,
        updated_at=submission.decided_at or submission.submitted_at,
        status=submission.status,
        decided_by=submission.decided_by,
    )


def _detail(submission: StoredSubmission) -> SubmissionDetail:
    return SubmissionDetail(
        id=submission.id,
        applicant_name=submission.applicant_name,
        applicant_email=submission.applicant_email,
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
        application_page_images=[
            f"/api/submissions/{submission.id}/files/application/page/{index}"
            for index in range(1, len(submission.application_file.page_images) + 1)
        ],
        label_page_images=[
            f"/api/submissions/{submission.id}/files/label/page/{index}"
            for index in range(1, len(submission.label_file.page_images) + 1)
        ],
        processing_time_ms=submission.processing_time_ms,
    )


def _brand(submission: StoredSubmission) -> str:
    return submission.application_fields.brand.strip() or "Unidentified brand"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_required_text(value: str, label: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail=f"{label} is required.")
    return cleaned


def _validate_email(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="Applicant email is required.")
    if not EMAIL_PATTERN.match(cleaned):
        raise HTTPException(status_code=422, detail="Applicant email must look like name@example.com.")
    return cleaned


def _has_readable_fields(fields: ExtractedFields) -> bool:
    return any(
        value.strip()
        for value in (
            fields.brand,
            fields.classType,
            fields.abv,
            fields.netContents,
            fields.warning,
        )
    )


def _file_for_kind(submission: StoredSubmission, file_kind: str) -> UploadPayload:
    if file_kind == "application":
        return submission.application_file
    if file_kind == "label":
        return submission.label_file
    raise HTTPException(status_code=404, detail="File not found.")


def _page_images(data: bytes, media_type: str, filename: str) -> list[PageImage]:
    if media_type == "application/pdf":
        return _pdf_pages(data, filename)
    if media_type in {"image/png", "image/jpeg"}:
        return [PageImage(data=data, media_type=media_type, filename=filename)]
    if media_type.startswith("text/plain"):
        return _text_pages(data, filename)
    return [_placeholder_page(filename, "Preview unavailable")]


def _pdf_pages(data: bytes, filename: str) -> list[PageImage]:
    try:
        images = convert_from_bytes(data, fmt="png", dpi=140)
    except Exception as exc:
        logger.warning("PDF page rendering failed for %s: %s", filename, exc)
        return [_placeholder_page(filename, "PDF preview unavailable")]

    pages: list[PageImage] = []
    for index, image in enumerate(images, start=1):
        output = BytesIO()
        image.save(output, format="PNG")
        pages.append(
            PageImage(
                data=output.getvalue(),
                media_type="image/png",
                filename=f"{Path(filename).stem}-page-{index}.png",
            )
        )
    return pages or [_placeholder_page(filename, "PDF had no pages")]


def _text_pages(data: bytes, filename: str) -> list[PageImage]:
    text = data.decode("utf-8", errors="replace")[:4000] or "No readable text."
    return [_placeholder_page(filename, text)]


def _placeholder_page(filename: str, text: str) -> PageImage:
    image = Image.new("RGB", (1000, 1300), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 970, 1270), outline="#d9d4c6", width=3)
    draw.text((60, 60), filename, fill="#1c2a24")
    y = 110
    for line in _wrap_text(text, 92):
        draw.text((60, y), line, fill="#33362e")
        y += 24
        if y > 1220:
            break
    output = BytesIO()
    image.save(output, format="PNG")
    return PageImage(
        data=output.getvalue(),
        media_type="image/png",
        filename=f"{Path(filename).stem or 'preview'}.png",
    )


def _wrap_text(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > width and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines
