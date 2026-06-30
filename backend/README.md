# PaperMind Backend

FastAPI backend for PaperMind, a research paper assistant with citation-backed RAG over uploaded PDFs.

## Stack

- FastAPI for HTTP APIs
- PostgreSQL with pgvector image for structured metadata today and future vector support
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

PostgreSQL runs at:

```text
localhost:5432
```

MinIO runs at:

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
alembic upgrade head
```

Check the active migration:

```bash
alembic current
```

The database should include:

```text
alembic_version
papers
document_chunks
```

`create_tables.py` was useful during early learning, but Alembic is now the official schema path.

## Run API

Start the LM Studio local server first. It should expose an OpenAI-compatible endpoint at:

```text
http://127.0.0.1:1234/v1
```

Then run:

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

## Main Endpoints

```text
GET /health
POST /upload
GET /papers
GET /papers/{paper_id}/status
POST /ask
POST /ingest
```

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

## RAG Flow

```text
Upload PDF
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

## Storage Model

PostgreSQL stores metadata, not the original PDF bytes:

```text
papers.storage_provider
papers.storage_key
papers.file_size
papers.mime_type
papers.status
```

Object storage stores the original PDF:

```text
MinIO locally now
AWS S3 later
```

Chroma stores vector embeddings for semantic retrieval. The chunk rows in PostgreSQL keep the text auditable and link each chunk to a paper.

## Do Not Commit

These local/generated paths should stay out of git:

```text
backend/.env
backend/.venv
backend/chroma_db
backend/tmp
__pycache__
```
