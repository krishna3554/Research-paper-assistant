# PaperMind Backend

FastAPI backend for PaperMind, a research paper assistant with citation-backed RAG over uploaded PDFs.

## Stack

- FastAPI for HTTP APIs
- PostgreSQL with the `pgvector/pgvector:pg16` image for structured metadata and future vector support
- MinIO for local S3-compatible object storage
- Chroma for the current local vector store
- LangChain for retrieval and LLM orchestration
- LM Studio for local OpenAI-compatible LLM inference
- Alembic for database migrations

## Local Services

Start PostgreSQL and MinIO from the project root:

```bash
docker compose up -d
```

PostgreSQL:

```text
localhost:5432
```

MinIO:

```text
API: http://localhost:9000
Console: http://localhost:9001
```

MinIO local login:

```text
Username: papermind
Password: papermind_password
```

Create this bucket in the MinIO console:

```text
papermind-papers
```

## Environment

Create `backend/.env` from `backend/.env.example`.

Required local values:

```env
LLM_PROVIDER=lmstudio

LLM_STUDIO_URL=http://127.0.0.1:1234/v1
LLM_STUDIO_API_KEY=lm-studio
LLM_STUDIO_MODEL_NAME=deepseek/deepseek-r1-0528-qwen3-8b

DATABASE_URL=postgresql+psycopg://papermind:papermind_password@localhost:5432/papermind

STORAGE_PROVIDER=minio
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=papermind-papers
S3_ACCESS_KEY_ID=papermind
S3_SECRET_ACCESS_KEY=papermind_password
S3_REGION=us-east-1

CHROMA_DIR=chroma_db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

For AWS S3 later, keep the same storage interface and change only the S3 environment variables:

```env
STORAGE_PROVIDER=aws
S3_ENDPOINT_URL=
S3_BUCKET_NAME=your-production-bucket
S3_ACCESS_KEY_ID=your-aws-access-key
S3_SECRET_ACCESS_KEY=your-aws-secret-key
S3_REGION=ap-south-1
```

The frontend API base URL can be configured from the project root:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Install

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database

Apply migrations:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Check the active migration:

```bash
alembic current
```

Expected tables:

```text
alembic_version
papers
document_chunks
```

`create_tables.py` was useful during early learning, but Alembic is now the official schema path.

## Run API

Start LM Studio first and enable its local OpenAI-compatible server at:

```text
http://127.0.0.1:1234/v1
```

Then run:

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Endpoint Summary

Core:

```text
GET  /health
GET  /papers
GET  /papers/{paper_id}/status
POST /upload
POST /sources/url
POST /ask
POST /ingest
```

Workspace intelligence:

```text
POST /review
POST /compare
POST /conflicts
GET  /graph?paper_id=paper_xxx
```

`POST /upload` accepts a PDF file and starts background indexing.

`POST /sources/url` accepts direct PDF URLs and arXiv URLs:

```json
{
  "url": "https://arxiv.org/abs/1706.03762"
}
```

DOI and publisher pages are not fully resolved yet unless they are direct PDF URLs.

`POST /ask` supports corpus-wide Q&A and paper-scoped Q&A:

```json
{
  "question": "what is a transformer?"
}
```

```json
{
  "question": "what is the main contribution?",
  "paper_id": "paper_xxx"
}
```

Workspace endpoints accept this shared request shape:

```json
{
  "paper_id": "paper_xxx",
  "paper_ids": null
}
```

`paper_id` scopes a panel to one paper. If omitted, the endpoint uses recent papers.

## Current RAG Flow

```text
Upload PDF or submit arXiv/direct PDF URL
  -> store original PDF in MinIO/S3-compatible storage
  -> create paper row in PostgreSQL
  -> start background ingestion
  -> download PDF temporarily for processing
  -> extract text with PyMuPDF
  -> split text into chunks
  -> save chunk metadata in PostgreSQL
  -> save embeddings in Chroma
  -> mark paper as indexed
  -> answer questions with retrieved citations
```

## Workspace Feature Flow

The frontend workspace now uses backend-backed data for:

```text
Library list       -> GET /papers
Upload             -> POST /upload
arXiv/PDF URL      -> POST /sources/url
Indexing status    -> GET /papers/{paper_id}/status
Chat Q&A           -> POST /ask
Review panel       -> POST /review
Compare panel      -> POST /compare
Conflict panel     -> POST /conflicts
Graph panel        -> GET /graph
```

Review, compare, conflicts, and graph currently compute lightweight structured outputs from PostgreSQL chunk metadata and indexed text. They are backend-backed, but not yet persisted as separate report tables.

Workspace collections currently work client-side:

```text
Library opens by default
Uploaded backend papers appear under the Uploaded collection
Collection counts are derived from the visible paper list
New collection prompts for a name
The active paper is assigned to the new collection
Custom collections and paper assignments are saved in browser localStorage
```

These client-side collection keys are used:

```text
papermind.collections
papermind.paperCollections
```

Future production work should move collections into PostgreSQL once user accounts and multi-device persistence are added.

## Storage Model

PostgreSQL stores metadata and chunk audit records:

```text
papers.storage_provider
papers.storage_key
papers.file_size
papers.mime_type
papers.status
document_chunks.content
document_chunks.chroma_id
```

Object storage stores original PDFs:

```text
MinIO locally now
AWS S3 later
```

Chroma stores vector embeddings for semantic retrieval.

## Verification

Backend syntax and app import from the project root:

```bash
backend/.venv/bin/python -m py_compile backend/api.py backend/config.py backend/db.py backend/storage.py backend/rag_text_demo.py backend/ingestion.py backend/models.py
backend/.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); import api; print(len(api.app.routes))"
```


Manual smoke test:

```text
1. docker compose up -d
2. Start LM Studio local server
3. cd backend && source .venv/bin/activate && uvicorn api:app --reload
4. Open http://127.0.0.1:8000/docs
5. Upload a PDF or submit an arXiv URL
6. Poll paper status until indexed
7. Test /ask, /review, /compare, /conflicts, and /graph
8. Open the frontend workspace and confirm all panels load backend data
9. Confirm Library, Uploaded, seeded collections, and New collection filtering work
```
