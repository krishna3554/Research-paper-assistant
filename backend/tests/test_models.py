import re

from models import DocumentChunk, Paper, generate_id


def test_generate_id_format():
    result = generate_id("paper")
    assert result.startswith("paper_")
    assert len(result) == len("paper_") + 32
    assert re.match(r"^paper_[a-f0-9]{32}$", result)


def test_generate_id_unique():
    ids = {generate_id("chunk") for _ in range(100)}
    assert len(ids) == 100


def test_paper_default_values():
    paper = Paper(
        filename="test.pdf",
        storage_provider="s3",
        storage_key="papers/abc/test.pdf",
        file_size=1024,
        mime_type="application/pdf",
    )
    assert paper.filename == "test.pdf"
    assert paper.status == "uploaded"
    assert paper.id.startswith("paper_")
    assert paper.title is None


def test_document_chunk_default_values():
    chunk = DocumentChunk(
        paper_id="paper_123",
        chunk_index=0,
        content="Test content",
    )
    assert chunk.paper_id == "paper_123"
    assert chunk.chunk_index == 0
    assert chunk.content == "Test content"
    assert chunk.page is None
    assert chunk.chroma_id is None
    assert chunk.id.startswith("chunk_")
