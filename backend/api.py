from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import get_db
from ingestion import ingest_paper
from models import DocumentChunk, Paper
from rag_text_demo import build_llm, format_docs, ingest, load_vector_store
from storage import S3_BUCKET_NAME, STORAGE_PROVIDER, upload_pdf_to_storage


app = FastAPI(title="PaperMind RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    id: str
    filename: str
    title: str | None = None
    status: str
    storage_provider: str
    file_size: int
    mime_type: str
    chunk_count: int
    uploaded_at: datetime


class UploadResponse(BaseModel):
    status: str
    paper_id: str
    filename: str
    storage_provider: str
    bucket: str
    storage_key: str
    paper_status: str
    message: str


class UrlIngestRequest(BaseModel):
    url: str


class WorkspaceRequest(BaseModel):
    paper_id: str | None = None
    paper_ids: list[str] | None = None


class ReviewSection(BaseModel):
    id: str
    title: str
    text: str
    source_count: int


class ReviewResponse(BaseModel):
    paper_id: str | None = None
    sections: list[ReviewSection]


class CompareRow(BaseModel):
    paper_id: str
    title: str
    status: str
    chunks: int
    methodology: str
    evidence: str
    risk: str


class CompareResponse(BaseModel):
    rows: list[CompareRow]


class ConflictItem(BaseModel):
    id: str
    severity: str
    title: str
    detail: str
    paper_ids: list[str]


class ConflictResponse(BaseModel):
    conflicts: list[ConflictItem]


class GraphNode(BaseModel):
    id: str
    label: str
    kind: str


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


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


def compact_text(value: str, max_chars: int = 280) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars].rstrip()}..."


def paper_title(paper: Paper) -> str:
    return paper.title or paper.filename.replace(".pdf", "")


def create_paper_record(
    *,
    background_tasks: BackgroundTasks,
    db: Session,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    title: str | None = None,
) -> UploadResponse:
    storage_key = upload_pdf_to_storage(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
    )

    paper = Paper(
        filename=filename,
        title=title,
        storage_provider=STORAGE_PROVIDER,
        storage_key=storage_key,
        file_size=len(file_bytes),
        mime_type=content_type,
        status="uploaded",
    )

    db.add(paper)
    db.commit()
    db.refresh(paper)
    background_tasks.add_task(ingest_paper, paper.id)

    return UploadResponse(
        status="ok",
        paper_id=paper.id,
        filename=paper.filename,
        storage_provider=paper.storage_provider,
        bucket=S3_BUCKET_NAME,
        storage_key=paper.storage_key,
        paper_status=paper.status,
        message="PDF uploaded and indexing started",
    )


def get_selected_papers(db: Session, request: WorkspaceRequest) -> list[Paper]:
    query = db.query(Paper).order_by(Paper.uploaded_at.desc())

    if request.paper_ids:
        return query.filter(Paper.id.in_(request.paper_ids)).all()

    if request.paper_id:
        paper = db.get(Paper, request.paper_id)
        return [paper] if paper else []

    return query.limit(6).all()


def get_chunks_for_papers(
    db: Session,
    paper_ids: list[str],
    limit: int = 18,
) -> list[DocumentChunk]:
    if not paper_ids:
        return []

    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.paper_id.in_(paper_ids))
        .order_by(DocumentChunk.paper_id, DocumentChunk.chunk_index)
        .limit(limit)
        .all()
    )


def resolve_source_url(url: str) -> tuple[bytes, str, str]:
    parsed = urlparse(url.strip())

    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="URL must start with http or https")

    pdf_url = url.strip()
    filename = parsed.path.rstrip("/").split("/")[-1] or "paper.pdf"

    if "arxiv.org" in parsed.netloc and "/abs/" in parsed.path:
        arxiv_id = parsed.path.split("/abs/", 1)[1]
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = f"{arxiv_id.replace('/', '_')}.pdf"
    elif "arxiv.org" in parsed.netloc and "/pdf/" in parsed.path:
        filename = f"{filename.replace('.pdf', '')}.pdf"
    elif not parsed.path.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only direct PDF URLs and arXiv URLs are supported right now",
        )

    request = Request(pdf_url, headers={"User-Agent": "PaperMind/0.1"})

    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "application/pdf").split(";")[0]
            file_bytes = response.read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not download source URL: {exc}") from exc

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Downloaded PDF is empty")

    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail=f"URL did not return a PDF: {content_type}")

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    return file_bytes, filename, "application/pdf"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db),
):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

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
        search_kwargs["filter"] = {"paper_id": request.paper_id}

    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)
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

    sources = [
        Source(
            source=doc.metadata.get("source", "unknown"),
            page=doc.metadata.get("page"),
        )
        for doc in retrieved_docs
    ]
    retrieved_chunks = [
        RetrievedChunk(
            source=doc.metadata.get("source", "unknown"),
            page=doc.metadata.get("page"),
            content=doc.page_content,
        )
        for doc in retrieved_docs
    ]

    return AskResponse(
        answer=response.content,
        sources=sources,
        retrieved_chunks=retrieved_chunks,
    )


@app.post("/ingest")
def ingest_documents():
    ingest()
    return {
        "status": "ok",
        "message": "Documents ingested successfully",
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now")

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have application/pdf content type",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")

    return create_paper_record(
        background_tasks=background_tasks,
        db=db,
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
    )


@app.post("/sources/url", response_model=UploadResponse)
def ingest_source_url(
    request: UrlIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    file_bytes, filename, content_type = resolve_source_url(request.url)

    return create_paper_record(
        background_tasks=background_tasks,
        db=db,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        title=filename.replace(".pdf", ""),
    )


@app.get("/papers/{paper_id}/status", response_model=PaperStatusResponse)
def get_paper_status(
    paper_id: str,
    db: Session = Depends(get_db),
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
def list_papers(db: Session = Depends(get_db)):
    chunk_counts = dict(
        db.query(DocumentChunk.paper_id, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.paper_id)
        .all()
    )
    paper_rows = db.query(Paper).order_by(Paper.uploaded_at.desc()).all()

    return [
        PaperListItem(
            id=paper.id,
            filename=paper.filename,
            title=paper.title,
            status=paper.status,
            storage_provider=paper.storage_provider,
            file_size=paper.file_size,
            mime_type=paper.mime_type,
            chunk_count=chunk_counts.get(paper.id, 0),
            uploaded_at=paper.uploaded_at,
        )
        for paper in paper_rows
    ]


@app.post("/review", response_model=ReviewResponse)
def build_review(request: WorkspaceRequest, db: Session = Depends(get_db)):
    selected = get_selected_papers(db, request)

    if request.paper_id and not selected:
        raise HTTPException(status_code=404, detail="Paper not found")

    chunks = get_chunks_for_papers(db, [paper.id for paper in selected], limit=12)

    if not chunks:
        raise HTTPException(status_code=409, detail="No indexed chunks available for review")

    intro = " ".join(compact_text(chunk.content, 180) for chunk in chunks[:3])
    methods = " ".join(compact_text(chunk.content, 160) for chunk in chunks[3:7] or chunks[:3])
    gaps = " ".join(compact_text(chunk.content, 150) for chunk in chunks[7:10] or chunks[-3:])

    return ReviewResponse(
        paper_id=request.paper_id,
        sections=[
            ReviewSection(id="summary", title="Source-grounded summary", text=compact_text(intro, 620), source_count=min(3, len(chunks))),
            ReviewSection(id="methods", title="Method and evidence trail", text=compact_text(methods, 620), source_count=min(4, len(chunks))),
            ReviewSection(id="gaps", title="Open questions and limitations", text=compact_text(gaps, 520), source_count=min(3, len(chunks))),
        ],
    )


@app.post("/compare", response_model=CompareResponse)
def compare_papers(request: WorkspaceRequest, db: Session = Depends(get_db)):
    selected = get_selected_papers(db, request)

    if request.paper_id and not selected:
        raise HTTPException(status_code=404, detail="Paper not found")

    rows = []

    for paper in selected:
        chunks = get_chunks_for_papers(db, [paper.id], limit=2)
        evidence = compact_text(chunks[0].content, 220) if chunks else "No indexed evidence available yet."
        risk = "Ready for Q&A" if paper.status == "indexed" else f"Indexing status: {paper.status}"
        rows.append(
            CompareRow(
                paper_id=paper.id,
                title=paper_title(paper),
                status=paper.status,
                chunks=len(paper.chunks),
                methodology=compact_text(evidence, 160),
                evidence=evidence,
                risk=risk,
            )
        )

    return CompareResponse(rows=rows)


@app.post("/conflicts", response_model=ConflictResponse)
def find_conflicts(request: WorkspaceRequest, db: Session = Depends(get_db)):
    selected = get_selected_papers(db, request)

    if request.paper_id and not selected:
        raise HTTPException(status_code=404, detail="Paper not found")

    chunks = get_chunks_for_papers(db, [paper.id for paper in selected], limit=18)
    markers = ("however", "but", "although", "whereas", "limitation", "conflict", "contradict")
    conflict_chunks = [
        chunk for chunk in chunks
        if any(marker in chunk.content.lower() for marker in markers)
    ]

    if not conflict_chunks and chunks:
        conflict_chunks = chunks[: min(3, len(chunks))]

    conflicts = [
        ConflictItem(
            id=f"conflict-{index}",
            severity="medium" if index > 1 else "high",
            title=f"Evidence tension on page {chunk.page or 'unknown'}",
            detail=compact_text(chunk.content, 260),
            paper_ids=[chunk.paper_id],
        )
        for index, chunk in enumerate(conflict_chunks[:5], start=1)
    ]

    return ConflictResponse(conflicts=conflicts)


@app.get("/graph", response_model=GraphResponse)
def graph(paper_id: str | None = None, db: Session = Depends(get_db)):
    request = WorkspaceRequest(paper_id=paper_id)
    selected = get_selected_papers(db, request)

    if paper_id and not selected:
        raise HTTPException(status_code=404, detail="Paper not found")

    chunks = get_chunks_for_papers(db, [paper.id for paper in selected], limit=12)
    nodes = []
    edges = []

    for paper in selected:
        paper_node = f"paper:{paper.id}"
        status_node = f"status:{paper.status}"
        nodes.append(GraphNode(id=paper_node, label=paper_title(paper), kind="paper"))
        nodes.append(GraphNode(id=status_node, label=paper.status, kind="status"))
        edges.append(GraphEdge(source=paper_node, target=status_node, label="has status"))

    for chunk in chunks:
        chunk_node = f"chunk:{chunk.id}"
        nodes.append(GraphNode(id=chunk_node, label=f"Chunk {chunk.chunk_index + 1}", kind="chunk"))
        edges.append(GraphEdge(source=f"paper:{chunk.paper_id}", target=chunk_node, label="contains"))

        if chunk.page:
            page_node = f"page:{chunk.paper_id}:{chunk.page}"
            nodes.append(GraphNode(id=page_node, label=f"Page {chunk.page}", kind="page"))
            edges.append(GraphEdge(source=chunk_node, target=page_node, label="cites"))

    unique_nodes = {node.id: node for node in nodes}
    unique_edges = {(edge.source, edge.target, edge.label): edge for edge in edges}

    return GraphResponse(
        nodes=list(unique_nodes.values()),
        edges=list(unique_edges.values()),
    )
