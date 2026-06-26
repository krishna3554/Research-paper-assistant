import os
from pathlib import Path
import sys
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TEXT_DIR = BASE_DIR / "data" / "texts"
PDF_DIR = BASE_DIR / "data" / "pdfs"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", BASE_DIR / "chroma_db"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def load_text_documents():
    documents = []

    for path in TEXT_DIR.glob("*.txt"):
        loader = TextLoader(str(path), encoding="utf-8")
        loaded_docs = loader.load()

        for doc in loaded_docs:
            doc.metadata["source"] = path.name

        documents.extend(loaded_docs)
    
    return documents

def load_pdf_documents():
    documents = []

    for path in PDF_DIR.glob("*.pdf"):
        loader = PyMuPDFLoader(str(path))
        loaded_docs = loader.load()

        for doc in loaded_docs:
            doc.metadata["source"] = path.name

            page = doc.metadata.get("page")
            if page is not None:
                doc.metadata["page"] = page + 1
        documents.extend(loaded_docs)

    return documents

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )

    return splitter.split_documents(documents)


def create_vector_store(chunks):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="research_texts",
    )

    return vector_store

def load_vector_store():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vector_store = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name="research_texts",
    )
    return vector_store

def ingest():
    print("Loading text and PDF documents...")
    text_documents = load_text_documents()
    pdf_documents = load_pdf_documents()

    documents = text_documents + pdf_documents

    print(f"Loaded {len(text_documents)} text document(s).")
    print(f"Loaded {len(pdf_documents)} PDF page document(s).")
    print(f"Loaded {len(documents)} total document(s).")

    if not documents:
        print("No documents found. Add files to data/texts or pdfs.")
        return
    
    print("Splitting documents into chunks...")
    chunks = split_documents(documents)
    print(f"Created {len(chunks)} chunk(s).")

    print("Creating vector store...")
    create_vector_store(chunks)

    print("Ingestion complete.")


def build_llm():

    provider = os.getenv("LLM_PROVIDER", "lmstudio").lower()

    if provider == "lmstudio":
        return ChatOpenAI(
            base_url=os.getenv("LLM_STUDIO_URL"),
            api_key=os.getenv("LLM_STUDIO_API_KEY"),
            model=os.getenv("LLM_STUDIO_MODEL_NAME"),
            temperature=0.2,
            timeout=120,
        )

    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required when "
                "LLM_PROVIDER=openrouter"
            )

        if not api_key.startswith("sk-or-"):
            raise ValueError(
                "OPENROUTER_API_KEY should be your OpenRouter chat API key. "
                "It usually starts with 'sk-or-'."
            )

        return ChatOpenAI(
            base_url=os.getenv(
                "OPENROUTER_URL",
                "https://openrouter.ai/api/v1"
            ),
            openai_api_key=api_key,
            model=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324"),
            temperature=0.2,
            timeout=120,
            default_headers={
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "PaperMind",
            },
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider}. "
        "Use 'lmstudio' or 'openrouter'."
    )

def format_docs(docs):
    formatted = []

    for index, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")

        if page is not None:
            citations = f"{source}, page {page}"
        else:
            citations = source

        formatted.append(
            f"[Source {index}: {citations}]\n{doc.page_content}"
        )
    
    return "\n\n".join(formatted)

def main():
    if len(sys.argv) < 2:
        print("Usage: ")
        print("  python rag_text_demo.py ingest")
        print("  python rag_text_demo.py ask")
        return
    
    command = sys.argv[1].lower()

    if command == "ingest":
        ingest()
    elif command == "ask":
        ask()
    else:
        print(f"Unknown command: {command}")
        print("Use either: ingest or ask")

def ask():
    print("Loading vector store...")
    vector_store = load_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={"k":3}
    )

    provider = os.getenv("LLM_PROVIDER", "lmstudio")
    print(f"Using LLM provider: {provider}")

    llm = build_llm()

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
    print("\nRAG ask mode ready")
    print("Ask a question about indexed documents. Type 'exit' to quit.\n")

    while True:
        question = input("Question: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        retrieved_docs = retriever.invoke(question)
        context = format_docs(retrieved_docs)

        messages = prompt.format_messages(
            context=context,
            question=question,
        )

        response = llm.invoke(messages)

        print("\nAnswer: ")
        print(response.content)

        print("\nRetrieved sources: ")

        for index, doc in enumerate(retrieved_docs, start=1):
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page")

            if page is not None:
                print(f"- Source {index}: {source}, page {page}")
            else:
                print(f"- Source {index} : {source}")
        print() 
    

if __name__ == "__main__":
    main()
