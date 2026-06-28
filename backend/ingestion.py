from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from db import SessionLocal
from models import DocumentChunk, Paper
from rag_text_demo import CHROMA_DIR, EMBEDDING_MODEL
from storage import download_file_from_storage

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )

    return splitter.split_documents(documents)

def ingest_paper(paper_id: str) -> Paper:
    db:Session = SessionLocal()

    try:
        paper = db.get(Paper, paper_id)

        if paper is None:
            raise ValueError(f"Paper not found: {paper_id}")

        paper.status = "processing"
        db.commit()

        with TemporaryDirectory() as temp_dir:
            local_pdf_path = Path(temp_dir) / paper.filename

            download_file_from_storage(
                storage_key=paper.storage_key,
                destination=local_pdf_path,
            )

            loader = PyMuPDFLoader(str(local_pdf_path))
            documents = loader.load()

            for doc in documents:
                doc.metadata["paper_id"] = paper.id
                doc.metadata["source"] = paper.filename

                page = doc.metadata.get("page")
                if page is not None:
                    doc.metadata["page"] = page + 1

            chunks = split_documents(documents)

            db.query(DocumentChunk).filter(
                DocumentChunk.paper_id == paper.id
            ).delete()

            chunk_rows = []

            for index, chunk in enumerate(chunks):
                chunk_row = DocumentChunk(
                    paper_id=paper.id,
                    chunk_index=index,
                    page=chunk.metadata.get("page"),
                    content=chunk.page_content,
                )
                db.add(chunk_row)
                chunk_rows.append(chunk_row)

            db.flush()

            chroma_ids = [chunk.id for chunk in chunk_rows]

            for chunk, chunk_row in zip(chunks, chunk_rows):
                chunk.metadata["paper_id"] = paper.id
                chunk.metadata["chunk_id"] = chunk_row.id
                chunk.metadata["source"] = paper.filename

            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

            Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(CHROMA_DIR),
                collection_name="research_texts",
                ids=chroma_ids,
            )

            for chunk_row in chunk_rows:
                chunk_row.chroma_id = chunk_row.id

            paper.status = "indexed"
            db.commit()
            db.refresh(paper)

            return paper

    except Exception:
        db.rollback()

        if "paper" in locals() and paper is not None:
            paper.status = "failed"
            db.commit()

        raise

    finally:
        db.close()