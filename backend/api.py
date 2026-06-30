from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ingestion import ingest_paper
from db import get_db
from models import Paper
from rag_text_demo import PDF_DIR, build_llm, format_docs, load_vector_store, ingest
from storage import S3_BUCKET_NAME, STORAGE_PROVIDER, upload_pdf_to_storage
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
app = FastAPI(title="PaperMind RAG API")

class AskRequest(BaseModel):
    question: str
    paper_id: str | None = None

class Source(BaseModel):
    source: str
    page: int | None = None

class RetrievedChunk(BaseModel):
    source: str
    page: int | None = None
    content: str

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieved_chunks: list[RetrievedChunk]

class PaperStatusResponse(BaseModel):
    paper_id: str
    filename: str
    status: str

class PaperListItem(BaseModel):
    id:str
    filename:str
    status: str
    storage_provider: str
    uploaded_at: datetime

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a research paper assistant.
Answer using ONLY the provided context.

If the answer is not present in the context, say:
"Not found in the uploaded documents."

Cite sources using [Source N].
""".strip(),
    ),
    (
        "human",
        """
Context:
{context}

Question:
{question}
""".strip(),
    ),
])


@app.get("/health")
def health():
    return {"status" : "ok"}

@app.post("/ask", response_model=AskResponse)

def ask_question(
    request: AskRequest,
    db:Session = Depends(get_db),
    ):
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty",
        )

    if request.paper_id:
        paper = db.get(Paper, request.paper_id)

        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        if paper.status != "indexed":
            raise HTTPException(
                status_code=409,
                detail=f"Paper is not ready for Q&A. Current status: {paper.status}",
            )
    vector_store = load_vector_store()
    
    search_kwargs = {"k": 3}

    if request.paper_id:
        search_kwargs["filter"] = {
            "paper_id": request.paper_id,
        }

    retriever = vector_store.as_retriever(
        search_kwargs=search_kwargs
    )

    retrieved_docs = retriever.invoke(request.question)
    context = format_docs(retrieved_docs)

    messages = prompt.format_messages(
        context=context,
        question=request.question,
    )

    llm = build_llm()
    try:
        response = llm.invoke(messages)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider failed: {exc}",
        ) from exc

    sources = []

    for doc in retrieved_docs:
        sources.append(
            Source(
                source=doc.metadata.get("source", "unknown"),
                page=doc.metadata.get("page")
            )
        )
    retrieved_chunks = []

    for doc in retrieved_docs:
        retrieved_chunks.append(
            RetrievedChunk(
                source = doc.metadata.get("source", "unknown"),
                page = doc.metadata.get("page"),
                content = doc.page_content,
            )
        )
    return AskResponse(
        answer=response.content,
        sources=sources,
        retrieved_chunks=retrieved_chunks,
    )


@app.post("/ingest")

def ingest_documents():
    ingest()
    return {
        "status" : "ok",
        "messages" : "Documents ingested successfully",
    }

@app.post("/upload")

async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    if not file.filename.lower().endswith(".pdf"):
        return {
            "status" : "error",
            "message": "Only PDF files are supported right now",
        }
    file_bytes = await file.read()

    storage_key = upload_pdf_to_storage(
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )

    paper = Paper(
        filename=file.filename,
        storage_provider=STORAGE_PROVIDER,
        storage_key=storage_key,
        file_size=len(file_bytes),
        mime_type=file.content_type,
        status="uploaded",
    )
    
    db.add(paper)
    db.commit()
    db.refresh(paper)
    background_tasks.add_task(ingest_paper, paper.id)
    return {
        "status": "ok",
        "paper_id": paper.id,
        "filename": paper.filename,
        "storage_provider": paper.storage_provider,
        "bucket": S3_BUCKET_NAME,
        "storage_key": paper.storage_key,
        "paper_status": paper.status,
        "message": "PDF uploaded and metadata saved successfully",
    }

@app.get("/papers/{paper_id}/status", response_model=PaperStatusResponse)
def get_paper_status(
    paper_id: str,
    db: Session = Depends(get_db)
):
    paper = db.get(Paper, paper_id)

    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")

    return PaperStatusResponse(
        paper_id=paper.id,
        filename=paper.filename,
        status=paper.status,
    )

@app.get("/papers", response_model=list[PaperListItem])
def list_papers(db:Session = Depends(get_db)):
    papers = (
        db.query(Paper)
        .order_by(Paper.uploaded_at.desc())
        .all()
    )

    return [
        PaperListItem(
            id = paper.id,
            filename = paper.filename,
            status = paper.status,
            storage_provider = paper.storage_provider,
            uploaded_at = paper.uploaded_at,
        )
        for paper in papers
    ]
