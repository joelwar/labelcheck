# TTB Label Verification Prototype

This monorepo contains a working prototype for TTB-style alcohol beverage label review.

- `frontend`: Next.js 16, TypeScript, Tailwind CSS
- `backend`: FastAPI, Gemini extraction, in-memory submission queue, field comparison logic

The app accepts applicant contact details plus either two files, one application form and one label image, or one combined PDF containing both. Submissions are stored in an in-memory queue so agents can confirm, override, or manually decide review outcomes.

Experiment files can be kept in `sample_files/`. Add application PDFs, label images, or combined two-page PDFs there when you want local/demo files for trying the app (optional). You may also load straight from your machine.

## Local Setup

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

PDF previews use Poppler through `pdf2image`. On macOS, install it with `brew install poppler` before running the backend locally.

Backend environment variables:

- `GEMINI_API_KEY`: required Gemini API key
- `ALLOWED_ORIGINS`: comma-separated frontend origins, defaults to `http://localhost:3000`
- `MAX_UPLOAD_MB`: per-file upload cap, defaults to `15`
- `GEMINI_MODEL`: optional, defaults to `gemini-3.1-flash-lite`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set `BACKEND_API_URL=http://localhost:8000` locally. The browser talks to the Next.js frontend, and the frontend server proxies requests to the backend.

## Product Flow

The prototype is a review-for-automation queue:

1. Upload a new submission from the queue page. This queue is also fed by website submissions done by applicants.
2. The backend extracts fields and creates a stored submission using hyper fast LLM model.
3. If extraction succeeds, the system sets `approved` or `needs_correction`.
4. If extraction fails, the system sets `to_review` and shows the source files for manual review.
5. An agent confirms, overrides, or manually decides the submission. It list the records as part of the overall set of submissions with their statuses.

## API

- `GET /api/health`: health check
- `POST /api/submissions`: upload and create a submission
- `GET /api/submissions`: queue list, optional `?status=to_review`
- `GET /api/submissions/{id}`: full submission detail
- `GET /api/submissions/{id}/files/application`: uploaded application/source file
- `GET /api/submissions/{id}/files/label`: uploaded label/source file
- `GET /api/submissions/{id}/files/application/page/{page}`: rendered application page image
- `GET /api/submissions/{id}/files/label/page/{page}`: rendered label page image
- `POST /api/seed`: load any complete seed folders that have not already been loaded
- `POST /api/submissions/{id}/decision`: agent decision endpoint

`POST /api/submissions` accepts multipart fields:

- `mode`: `separate` or `combined`
- `applicant_name`: required applicant/company name
- `applicant_email`: required applicant email address
- `application_file` and `label_file`: required for `separate`
- `combined_file`: required for `combined`

Supported upload content:

- PDF
- PNG/JPG
- DOCX for typed application-form content

Older binary `.doc` files are not parsed in this prototype; export them to PDF or DOCX first.

## Status Model

Every submission has one status:

- `approved`: all compared fields passed the prototype rules.
- `needs_correction`: extraction succeeded, but one or more fields mismatched.
- `to_review`: extraction failed or a required field could not be read reliably (very rare ocurrance).

Every submission also records `decided_by`:

- `system`: automated status has not yet been reviewed by an agent.
- `agent_confirmed`: agent agreed with the automated result.
- `agent_override`: agent changed an automated result and supplied a reason.
- `agent_manual`: agent decided a `to_review` case from scratch.

Overrides store `override_reason` and all agent actions set `decided_at`.

## Extraction Approach

The backend sends each document to Gemini in a single request and asks for JSON only:

```json
{ "brand": "", "classType": "", "abv": "", "netContents": "", "warning": "" }
```

For two-file submissions, application and label extraction run concurrently. For combined submissions, the PDF is sent once and Gemini returns both `application_fields` and `label_fields`.

The warning field is prompted for exact transcription, preserving capitalization and wording. PDFs and images are passed inline to avoid file persistence in the model integration.

## Matching Logic

Each field result is `match` or `mismatch`. There is no per-field `review` state in this prototype.

- Brand and class/type must match exactly after trimming. Case or punctuation-only differences are mismatches.
- ABV is parsed numerically where possible, so `45% Alc./Vol. (90 Proof)` and `45% ALC/VOL` match.
- Net contents are normalized to milliliters where possible, so `750 ml` and `0.75 L` match.
- Government warning is strict, case-sensitive, exact-text comparison. It is never normalized.

This deliberately simplifies the real TTB process. The prototype does not implement a conditionally-approved applicant correction loop; any mismatch routes to `needs_correction`.

## Persistence

The backend uses an in-memory dictionary keyed by submission id. This keeps the prototype simple and lets the queue persist across requests within one running backend process. Data is lost when the backend restarts or redeploys.

Uploaded files are kept only in that in-memory queue so agents can view them on detail/manual review screens. Do not treat this as production storage.


## Known Limitations

- No authentication.
- No applicant-facing portal, email delivery, notification, or accept/decline workflow.
- No COLA system integration.
- No persistence beyond the in-memory process.
- Batch endpoint is not implemented; multiple uploads appear as queue rows one at a time.
- DOCX support extracts typed text only; image-heavy Word files should be exported to PDF.
- Extraction accuracy depends on source image quality and model response quality.
