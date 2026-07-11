# TTB Label Verification Prototype

This monorepo contains a working prototype for comparing TTB alcohol beverage application data against label artwork.

- `frontend`: Next.js 16, TypeScript, Tailwind CSS
- `backend`: FastAPI, Gemini extraction, field comparison logic

The app accepts either two files, one application form and one label image, or one combined PDF containing both. Uploaded files are processed in memory for the request and are not persisted.

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

Set these backend environment variables:

- `GEMINI_API_KEY`: required Gemini API key
- `ALLOWED_ORIGINS`: comma-separated frontend origins, defaults to `http://localhost:3000`
- `MAX_UPLOAD_MB`: per-file upload cap, defaults to `15`
- `GEMINI_MODEL`: optional, defaults to `gemini-3.5-flash`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Set `BACKEND_API_URL=http://localhost:8000` locally.

## API

- `GET /api/health`: health check
- `POST /api/verify`: multipart verification endpoint

`/api/verify` fields:

- `mode`: `separate` or `combined`
- `application_file` and `label_file`: required for `separate`
- `combined_file`: required for `combined`

Supported upload content:

- PDF
- PNG/JPG
- DOCX for typed application-form content

Older binary `.doc` files are not parsed in this prototype; export them to PDF or DOCX first.

## Extraction Approach

The backend sends each document to Gemini in a single request and asks for JSON only:

```json
{ "brand": "", "classType": "", "abv": "", "netContents": "", "warning": "" }
```

For two-file submissions, the application and label are extracted concurrently. For combined submissions, the PDF is sent once and Gemini is asked to return both `application_fields` and `label_fields`.

The warning field is treated specially in the prompt: Gemini is instructed to transcribe it exactly as it appears, preserving capitalization and wording. PDFs and images are passed inline to avoid retaining uploaded files beyond the request lifecycle.

## Matching Logic

Each field returns `match`, `review`, or `fail`.

- Brand and class/type use exact matching first, then case/punctuation/whitespace-insensitive fuzzy matching. Fuzzy-only matches become `review`.
- ABV is parsed numerically where possible, so `45% Alc./Vol. (90 Proof)` and `45% ALC/VOL` match.
- Net contents are normalized to milliliters where possible, so `750 ml` and `0.75 L` match.
- Government warning is strict, case-sensitive, exact-text comparison. It is never fuzzy matched.

Overall status is `fail` if any field fails, `review` if any field needs review, otherwise `match`.

## Railway Deployment

Create two Railway services from this same repository.

### Backend Service

Railway settings:

- Root directory: `/backend`
- Build command: leave as Nixpacks default
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Environment variables:

- `GEMINI_API_KEY`
- `ALLOWED_ORIGINS=https://your-frontend-service.up.railway.app`
- `MAX_UPLOAD_MB=15`

### Frontend Service

Railway settings:

- Root directory: `/frontend`
- Build command: `npm run build`
- Start command: `npm run start -- -p $PORT`

Environment variables:

- `BACKEND_API_URL=https://your-backend-service.up.railway.app`

After both services deploy, update backend `ALLOWED_ORIGINS` to the final frontend Railway domain and redeploy the backend.

## Testing

Run backend comparison tests:

```bash
cd backend
pytest
```

Manual fixture checks should confirm:

- Perfect match: all fields `match`, overall `match`
- ABV mismatch: only alcohol content `fail`, overall `fail`
- Warning format mismatch: warning `fail`, never `review`
- Multiple differences: each differing field `fail`, overall `fail`

## Known Limitations

- No authentication, persistence, audit history, or COLA integration.
- Uploaded files are not retained after the request.
- Batch verification endpoint is not implemented.
- DOCX support extracts typed text only; image-heavy Word files should be exported to PDF.
- Extraction accuracy depends on source image quality and model response quality.
