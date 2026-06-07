# AI Project Evaluation System Prototype

Phase 2 MVP setup for the project evaluation pipeline. The current slice includes the FastAPI app, PostgreSQL + pgvector schema, `POST /api/transcribe`, `POST /api/process-transcript-file`, `POST /api/analyze-repo`, `POST /api/extract-claims`, `POST /api/verify`, `POST /api/report`, `GET /api/reports`, `GET /api/reports/{projectId}`, `POST /api/search`, `POST /api/evaluate`, `POST /api/upload-video`, `GET /api/technologies`, `GET /api/projects/{projectId}`, and `DELETE /api/projects/{projectId}`.

## What Works Now

- Accept a local MP4/audio path and project ID.
- Extract audio with `ffmpeg` when the input is a video.
- Call OpenAI Whisper (`whisper-1`) for transcription.
- Chunk transcript text into overlapping 250-350 token chunks.
- Embed chunks with `text-embedding-3-small`.
- Store video or manual transcript chunks and embeddings in PostgreSQL/pgvector when `DATABASE_URL` is configured.
- Upload a `.txt` transcript instead of a video and store the same chunk embeddings for semantic search.
- Return the standard transcribe JSON response.
- Clone a public GitHub repository.
- Parse dependency files and scan imports for known technologies.
- Return detected technologies with file, line, snippet, and confidence evidence.
- Extract claimed technologies from a project description.
- Normalize claim names and aliases against the shared technology database.
- Compare claimed technologies against repository and transcript evidence.
- Assign verification status and confidence scores.
- Assemble endpoint outputs into a standard JSON evaluation report.
- Search stored transcript chunks with pgvector similarity.
- Run the full backend evaluation pipeline from one request.
- Upload local video files and receive a `file://` path for evaluation.
- Expose the supported technology database for UI controls and reporting.
- Inspect project upload and transcript status for UI state.
- Delete uploaded files and stored transcript data for a project.
- Persist and retrieve generated JSON reports by project ID.
- List saved reports for dashboard-style UI views.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. Keep `DATABASE_URL` pointed at Docker PostgreSQL unless you are using another pgvector database:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/eval_db
```

Start pgvector:

```bash
docker compose up -d
```

Confirm the database container is running:

```bash
docker ps
```

The first startup runs `scripts/init.sql`, which enables `vector`, creates `transcripts`, creates `transcript_chunks` with `embedding vector(1536)`, and adds the cosine `ivfflat` index used by `/api/search`.

For the MVP, uploaded `.mp4` and `.webm` files are sent directly to OpenAI transcription. OpenAI audio uploads are limited to 25 MB, so use a short sample video or manual transcript mode with an uploaded `.txt` transcript for larger demos. `ffmpeg` is optional and only used for formats that need local audio extraction.

Run the API:

```bash
uvicorn app.main:app --reload
```

Open the UI:

```bash
http://localhost:8000
```

The UI can upload a video or transcript `.txt` plus a README/Markdown project description, then run the evidence workflow from the **Upload Inputs** button: transcript processing, claim extraction, repository evidence analysis, verification decisions, JSON report assembly, report download, and saved report loading. Intermediate transcript search and rerun controls remain available for inspection/debugging.

## Default Inputs

Browser file inputs cannot be pre-filled for security reasons. For repeat local testing, set default file paths in `.env` and use **Load Defaults** in Step 1:

```bash
DEFAULT_PROJECT_ID=proj-local-demo
DEFAULT_REPO_URL=https://github.com/your-org/your-repo
DEFAULT_VIDEO_PATH=/absolute/path/to/demo.mp4
DEFAULT_TRANSCRIPT_PATH=/absolute/path/to/transcript.txt
DEFAULT_README_PATH=/absolute/path/to/README.md
```

You only need one of `DEFAULT_VIDEO_PATH` or `DEFAULT_TRANSCRIPT_PATH`. If a default transcript is configured, the run workflow chunks, embeds, and stores it directly in pgvector without uploading it through the browser.

## Endpoint: Transcribe

`POST /api/transcribe`

Request:

```json
{
  "videoPath": "file:///absolute/path/to/demo.mp4",
  "projectId": "proj-123"
}
```

Response:

```json
{
  "projectId": "proj-123",
  "transcript": "full text...",
  "chunks": [
    {
      "id": "proj-123-chunk-1",
      "text": "chunk text...",
      "startTime": 0.0,
      "endTime": 15.5,
      "embedding": [0.123]
    }
  ],
  "duration": 420
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -H "Content-Type: application/json" \
  -d @samples/transcribe-request.json
```

## Endpoint: Analyze Repository

`POST /api/analyze-repo`

Request:

```json
{
  "repoUrl": "https://github.com/vercel/next.js",
  "projectId": "proj-123"
}
```

Response:

```json
{
  "projectId": "proj-123",
  "repoUrl": "https://github.com/vercel/next.js.git",
  "detectedTechs": [
    {
      "key": "react",
      "name": "React",
      "category": "frontend",
      "confidence": "high",
      "evidence": [
        {
          "file": "package.json",
          "line": 10,
          "snippet": "\"react\": \"...\"",
          "source": "dependencies"
        }
      ]
    }
  ],
  "repository": {
    "scannedFiles": 120,
    "evidenceCount": 24,
    "truncated": false,
    "cloneSeconds": 4.2
  }
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/analyze-repo \
  -H "Content-Type: application/json" \
  -d @samples/analyze-repo-request.json
```

## Endpoint: Extract Claims

`POST /api/extract-claims`

Request:

```json
{
  "projectId": "proj-123",
  "description": "Built with React frontend and Node.js backend. Uses PostgreSQL and Docker."
}
```

Response:

```json
{
  "projectId": "proj-123",
  "claimedTechs": [
    {
      "key": "react",
      "name": "React",
      "category": "frontend",
      "matchedText": "React",
      "sourceQuote": "Built with React frontend and Node.js backend...",
      "confidence": "claimed"
    }
  ],
  "summary": {
    "descriptionLength": 75,
    "claimCount": 4
  }
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/extract-claims \
  -H "Content-Type: application/json" \
  -d @samples/extract-claims-request.json
```

## Endpoint: Verify Claims

`POST /api/verify`

Request:

```json
{
  "projectId": "proj-123",
  "claimedTechs": ["React", "Node.js", "PostgreSQL"],
  "detectedTechs": [
    {
      "key": "react",
      "name": "React",
      "confidence": "high",
      "evidence": [
        {
          "file": "package.json",
          "line": 12,
          "snippet": "\"react\": \"^18.2.0\"",
          "source": "dependencies"
        }
      ]
    }
  ],
  "transcriptChunks": [
    {
      "id": "chunk-1",
      "text": "We built the UI with React.",
      "startTime": 0,
      "endTime": 12
    }
  ]
}
```

Response:

```json
{
  "projectId": "proj-123",
  "claimVerification": [
    {
      "key": "react",
      "claimed": "React",
      "detected": true,
      "transcriptMentioned": true,
      "status": "verified",
      "confidence": 0.9,
      "evidence": [],
      "notes": []
    }
  ],
  "summary": {
    "totalClaims": 3,
    "verified": 1,
    "partial": 0,
    "unverified": 2,
    "contradicted": 0
  }
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d @samples/verify-request.json
```

## Endpoint: Report

`POST /api/report`

This endpoint assembles outputs from the previous endpoints into the standard JSON report shape. In the current MVP, it accepts the prior endpoint outputs in the request body instead of loading them from persistent project state.

Request:

```json
{
  "projectId": "proj-123",
  "repoUrl": "https://github.com/example/recipe-recommender",
  "description": "A recipe recommender built with React and Node.js.",
  "transcription": {},
  "repositoryAnalysis": {},
  "claimExtraction": {},
  "verification": {}
}
```

Response:

```json
{
  "project_metadata": {
    "projectId": "proj-123",
    "repoUrl": "https://github.com/example/recipe-recommender.git",
    "generatedAt": "2026-05-13T00:00:00Z",
    "systemVersion": "0.1.0",
    "modelVersions": {
      "whisper": "whisper-1",
      "embedding": "text-embedding-3-small"
    }
  },
  "summary": {
    "totalClaims": 3,
    "verifiedClaims": 2,
    "partialClaims": 0,
    "unverifiedClaims": 1,
    "contradictedClaims": 0,
    "detectedTechnologies": 2,
    "transcriptChunks": 2,
    "riskLevel": "medium"
  },
  "claims": {},
  "detection": {},
  "verification": {},
  "transcript": {},
  "repository": {},
  "company_relevance": {},
  "risks_and_gaps": {},
  "evaluation_notes": {}
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d @samples/report-request.json
```

Reports generated by `/api/report` and `/api/evaluate` are saved in `reports/` for later retrieval.

## Endpoint: List Saved Reports

`GET /api/reports`

Returns a summary list of saved reports ordered by most recently modified first.

Example call:

```bash
curl http://localhost:8000/api/reports
```

Response:

```json
{
  "reports": [
    {
      "projectId": "proj-123",
      "repoUrl": "https://github.com/example/recipe-recommender.git",
      "generatedAt": "2026-05-14T00:00:00Z",
      "riskLevel": "medium",
      "totalClaims": 3,
      "verifiedClaims": 2,
      "unverifiedClaims": 1,
      "contradictedClaims": 0,
      "path": "reports/proj-123.json"
    }
  ],
  "count": 1
}
```

## Endpoint: Get Saved Report

`GET /api/reports/{projectId}`

Returns the latest saved report JSON for a project.

Example call:

```bash
curl http://localhost:8000/api/reports/proj-123
```

If no report has been generated for the project, the endpoint returns `404`.

## Endpoint: Search Transcript

`POST /api/search`

This endpoint searches transcript chunks stored by `POST /api/transcribe`. It requires `DATABASE_URL`, a running pgvector database, and `OPENAI_API_KEY` because it embeds the search query with `text-embedding-3-small`.

Request:

```json
{
  "projectId": "proj-123",
  "query": "React frontend",
  "limit": 5,
  "similarityThreshold": 0.7
}
```

Response:

```json
{
  "projectId": "proj-123",
  "query": "React frontend",
  "results": [
    {
      "id": "proj-123-chunk-1",
      "text": "We built the UI with React...",
      "startTime": 0,
      "endTime": 15.5,
      "similarity": 0.92,
      "metadata": {
        "source": "whisper"
      }
    }
  ],
  "resultCount": 1,
  "embeddingModel": "text-embedding-3-small"
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d @samples/search-request.json
```

## Endpoint: Evaluate

`POST /api/evaluate`

This endpoint runs the backend pipeline in one request:

1. Transcribe video and embed chunks.
2. Analyze GitHub repository.
3. Extract claimed technologies from the description.
4. Verify claims against repository and transcript evidence.
5. Assemble the final report.

Request:

```json
{
  "projectId": "proj-123",
  "videoPath": "file:///absolute/path/to/demo.mp4",
  "repoUrl": "https://github.com/pallets/flask",
  "description": "A Flask API project that uses Redis for background jobs."
}
```

For development smoke tests without OpenAI/video input, use `skipTranscription` with transcript text. In the browser UI, manual transcript mode asks for a `.txt`, `.md`, or `.markdown` transcript file:

```json
{
  "projectId": "proj-smoke",
  "videoPath": "file:///tmp/not-used-when-skipping.mp4",
  "repoUrl": "https://github.com/pallets/flask",
  "description": "A Flask API project that uses Redis.",
  "skipTranscription": true,
  "transcriptOverride": "This project is a Flask API and uses Redis."
}
```

Example call:

```bash
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d @samples/evaluate-request.json
```

Smoke-test call:

```bash
curl -X POST http://localhost:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d @samples/evaluate-smoke-request.json
```

The upload UI is available at `http://localhost:8000` and calls `/api/evaluate` after upload.

## Endpoint: Upload Video

`POST /api/upload-video`

This endpoint accepts a multipart video upload and stores it in `uploads/`. The returned `videoPath` can be passed directly to `/api/evaluate`.

Request:

```bash
curl -X POST http://localhost:8000/api/upload-video \
  -F "projectId=proj-123" \
  -F "file=@/absolute/path/to/demo.mp4"
```

Response:

```json
{
  "projectId": "proj-123",
  "filename": "proj-123-abc123-demo.mp4",
  "originalFilename": "demo.mp4",
  "videoPath": "file:///Users/jiaseow/Phase2/uploads/proj-123-abc123-demo.mp4",
  "contentType": "video/mp4",
  "sizeBytes": 123456
}
```

Supported extensions: `.mp4`, `.mov`, `.m4v`, `.webm`. Upload limit: 750 MB.

## Endpoint: Technologies

`GET /api/technologies`

Returns the supported technology database as a flat list plus category groupings.

Example call:

```bash
curl http://localhost:8000/api/technologies
```

Response:

```json
{
  "technologies": [
    {
      "key": "react",
      "name": "React",
      "category": "frontend",
      "confidenceTier": "high",
      "aliases": ["react", "reactjs", "react.js"]
    }
  ],
  "categories": {
    "frontend": ["react"]
  },
  "count": 40
}
```

## Endpoint: Project Status

`GET /api/projects/{projectId}`

Returns upload and transcript persistence status for a project. The endpoint still returns upload information if Postgres is not configured or unavailable.

Example call:

```bash
curl http://localhost:8000/api/projects/proj-123
```

Response:

```json
{
  "projectId": "proj-123",
  "uploads": [
    {
      "filename": "proj-123-abc123-demo.mp4",
      "videoPath": "file:///Users/jiaseow/Phase2/uploads/proj-123-abc123-demo.mp4",
      "sizeBytes": 123456,
      "modifiedAt": "2026-05-13T18:00:00-07:00"
    }
  ],
  "transcript": {
    "available": false,
    "storageAvailable": true,
    "chunkCount": 0,
    "duration": null,
    "createdAt": null,
    "error": null
  },
  "readyForEvaluation": true
}
```

## Endpoint: Delete Project Data

`DELETE /api/projects/{projectId}`

Deletes uploaded videos for a project and removes stored transcript rows when Postgres is configured.

Example call:

```bash
curl -X DELETE http://localhost:8000/api/projects/proj-123
```

Response:

```json
{
  "projectId": "proj-123",
  "deletedUploads": 1,
  "deletedTranscript": true,
  "storageAvailable": true,
  "error": null
}
```
