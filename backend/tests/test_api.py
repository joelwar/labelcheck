import base64

from fastapi.testclient import TestClient

import app.main as main
from app.models import ExtractedFields


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def setup_function() -> None:
    main.SUBMISSIONS.clear()
    main.SEEDED_KEYS.clear()
    main.NEXT_ID = 1


def test_upload_requires_valid_applicant_email() -> None:
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Old Tom Distillery, LLC",
            "applicant_email": "not-an-email",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Applicant email must look like name@example.com."


def test_upload_returns_applicant_and_page_image_urls(monkeypatch) -> None:
    async def fake_extract_fields(_: bytes, __: str, ___: str) -> ExtractedFields:
        return ExtractedFields(
            brand="Old Tom Gin",
            classType="Gin",
            abv="45% Alc./Vol.",
            netContents="750 ml",
            warning="GOVERNMENT WARNING:",
        )

    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Old Tom Distillery, LLC",
            "applicant_email": "regulatory@oldtomdistillery.example.com",
        },
        files={
            "application_file": ("application.png", PNG_BYTES, "image/png"),
            "label_file": ("label.png", PNG_BYTES, "image/png"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applicant_name"] == "Old Tom Distillery, LLC"
    assert payload["applicant_email"] == "regulatory@oldtomdistillery.example.com"
    assert payload["application_page_images"] == ["/api/submissions/sub_0001/files/application/page/1"]
    assert payload["label_page_images"] == ["/api/submissions/sub_0001/files/label/page/1"]

    image_response = client.get(payload["application_page_images"][0])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"

    queue_response = client.get("/api/submissions")
    assert queue_response.status_code == 200
    queue_item = queue_response.json()[0]
    assert queue_item["updated_at"] == queue_item["submitted_at"]


def test_queue_brand_uses_application_form_not_label(monkeypatch) -> None:
    async def fake_extract_fields(_: bytes, __: str, document_kind: str) -> ExtractedFields:
        if document_kind == "application":
            return ExtractedFields(
                brand="",
                classType="Gin",
                abv="45% Alc./Vol.",
                netContents="750 ml",
                warning="GOVERNMENT WARNING:",
            )
        return ExtractedFields(
            brand="Label Brand Should Not Win",
            classType="Gin",
            abv="45% Alc./Vol.",
            netContents="750 ml",
            warning="GOVERNMENT WARNING:",
        )

    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Old Tom Distillery, LLC",
            "applicant_email": "regulatory@oldtomdistillery.example.com",
        },
        files={
            "application_file": ("application.png", PNG_BYTES, "image/png"),
            "label_file": ("label.png", PNG_BYTES, "image/png"),
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_correction"

    queue_response = client.get("/api/submissions")
    assert queue_response.status_code == 200
    assert queue_response.json()[0]["brand"] == "Unidentified brand"


def test_partially_readable_extraction_compares_instead_of_manual_review(monkeypatch) -> None:
    async def fake_extract_fields(_: bytes, __: str, document_kind: str) -> ExtractedFields:
        if document_kind == "application":
            return ExtractedFields(
                brand="",
                classType="Gin",
                abv="45% Alc./Vol.",
                netContents="750 ml",
                warning="GOVERNMENT WARNING:",
            )
        return ExtractedFields(
            brand="Old Tom Gin",
            classType="Gin",
            abv="45% Alc./Vol.",
            netContents="750 ml",
            warning="GOVERNMENT WARNING:",
        )

    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Old Tom Distillery, LLC",
            "applicant_email": "regulatory@oldtomdistillery.example.com",
        },
        files={
            "application_file": ("application.png", PNG_BYTES, "image/png"),
            "label_file": ("label.png", PNG_BYTES, "image/png"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_correction"
    assert payload["extraction_ok"] is True
    assert payload["extraction_error"] is None
    assert payload["field_results"][0]["key"] == "brand"
    assert payload["field_results"][0]["status"] == "mismatch"


def test_unreadable_extraction_routes_to_manual_review(monkeypatch) -> None:
    async def fake_extract_fields(_: bytes, __: str, ___: str) -> ExtractedFields:
        return ExtractedFields()

    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Old Tom Distillery, LLC",
            "applicant_email": "regulatory@oldtomdistillery.example.com",
        },
        files={
            "application_file": ("application.png", PNG_BYTES, "image/png"),
            "label_file": ("label.png", PNG_BYTES, "image/png"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "to_review"
    assert payload["extraction_ok"] is False
    assert payload["field_results"] == []


def test_one_file_extraction_failure_still_routes_to_correction(monkeypatch) -> None:
    async def fake_extract_fields(_: bytes, __: str, document_kind: str) -> ExtractedFields:
        if document_kind == "application":
            raise RuntimeError("application extraction failed")
        return ExtractedFields(
            brand="Old Tom Gin",
            classType="Gin",
            abv="45% Alc./Vol.",
            netContents="750 ml",
            warning="GOVERNMENT WARNING:",
        )

    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "separate",
            "applicant_name": "Testing",
            "applicant_email": "test@gmail.com",
        },
        files={
            "application_file": ("application.png", PNG_BYTES, "image/png"),
            "label_file": ("label.png", PNG_BYTES, "image/png"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_correction"
    assert payload["extraction_ok"] is True
    assert payload["extraction_error"] is None
    assert all(row["status"] == "mismatch" for row in payload["field_results"])


def test_combined_upload_uses_page_one_for_form_and_page_two_for_label(monkeypatch) -> None:
    async def fake_read_upload(*_: object) -> main.UploadPayload:
        return main.UploadPayload(
            extraction_bytes=b"original pdf",
            extraction_media_type="application/pdf",
            display_bytes=b"original pdf",
            display_media_type="application/pdf",
            filename="combined.pdf",
            page_images=[
                main.PageImage(data=b"page-one-form", media_type="image/png", filename="page-1.png"),
                main.PageImage(data=b"page-two-label", media_type="image/png", filename="page-2.png"),
            ],
        )

    seen: list[tuple[bytes, str]] = []

    async def fake_extract_fields(data: bytes, _: str, document_kind: str) -> ExtractedFields:
        seen.append((data, document_kind))
        if document_kind == "application":
            return ExtractedFields(brand="Form Brand")
        return ExtractedFields(brand="Label Brand")

    monkeypatch.setattr(main, "_read_upload", fake_read_upload)
    monkeypatch.setattr(main, "extract_fields", fake_extract_fields)
    client = TestClient(main.app)

    response = client.post(
        "/api/submissions",
        data={
            "mode": "combined",
            "applicant_name": "Testing",
            "applicant_email": "test@gmail.com",
        },
        files={"combined_file": ("combined.pdf", b"unused", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert seen == [(b"page-one-form", "application"), (b"page-two-label", "label")]
    assert payload["application_page_images"] == ["/api/submissions/sub_0001/files/application/page/1"]
    assert payload["label_page_images"] == ["/api/submissions/sub_0001/files/label/page/1"]
    assert payload["status"] == "needs_correction"
