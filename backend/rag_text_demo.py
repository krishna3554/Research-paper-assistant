import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

TEXT_DIR = Path("data/texts")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "chroma_db"))
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

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )

    return splitter.split_documents(documents)


def build_vector_store(chunks):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="research_texts",
    )

    return vector_store

def build_llm():
    return ChatOpenAI(
        base_url=os.getenv("LLM_STUDIO_URL"),
        api_key=os.getenv("LLM_STUDIO_API_KEY"),
        model=os.getenv("LLM_STUDIO_MODEL_NAME"),
        temperature=0.2,
    )

def format_docs(docs):
    formatted = []

    for index, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        formatted.append(
            f"[Source {index}: {source}]\n{doc.page_content}"
        )
    
    return "\n\n".join(formatted)

def main():
    print("Loading text documents...")
    documents = load_text_documents()
    print(f"Loaded {len(documents)} documents")

    print("Splitting documents into chunks...")
    chunks = split_documents(documents)
    print(f"Split into {len(chunks)} chunks")

    print("Building vector store..")

    vector_store = build_vector_store(chunks)

    retriever = vector_store.as_retriever(
        search_kwargs={"k":3}
    )

    llm = build_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
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
        ]
    )

    print("\nRAG Demo Ready")
    print("Ask a question about the uploaded documents (type 'exit' to quit):")

    while True:
        question = input("\nQuestion: ").strip()

        if question.lower() in {"exit", "quit"}:
            break

        retrieved_docs = retriever.invoke(question)
        context = format_docs(retrieved_docs)

        messages = prompt.format_messages(
            context=context,
            question=question,
        )

        response = llm.invoke(messages)

        print("\nAnswers: ")
        print(response.content)

        print("\nRetrieved sources: ")
        for index, doc in enumerate(retrieved_docs, start=1):
            print(f"- Source {index} : {doc.metadata.get('source')}")
        print()

if __name__ == "__main__":
    main()


