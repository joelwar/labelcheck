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
