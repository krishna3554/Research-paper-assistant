from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Depends 
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Paper
from rag_text_demo import PDF_DIR, build_llm, format_docs, load_vector_store, ingest
from storage import S3_BUCKET_NAME, STORAGE_PROVIDER, upload_pdf_to_storage
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI(title="PaperMind RAG API")

class AskRequest(BaseModel):
    question: str

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
    retireved_chunks: list[RetrievedChunk]


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

def ask_question(request: AskRequest):
    vector_store = load_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={"k":3}
    )

    retrieved_docs = retriever.invoke(request.question)
    context = format_docs(retrieved_docs)

    messages = prompt.format_messages(
        context=context,
        question=request.question,
    )

    llm = build_llm();
    response = llm.invoke(messages)

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
            RetrirevedChunk(
                source = doc.metadata.get("source", "unknown"),
                page = docs.metadata.get("page"),
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

    return {
        "status": "ok",
        "paper_id": paper.id,
        "filename": paper.filename,
        "storage_provider": paper.storage_provider,
        "bucket": S3_BUCKET_NAME,
        "storage_key": paper.storage_key,
        "message": "PDF uploaded and metadata saved successfully",
    }