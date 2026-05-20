"""
Enterprise RAG - FAISS Ingestion Pipeline (STABLE VERSION)

Fixes:
- Gemini rate limit (429)
- FAISS batching issues
- embedding instability
- metadata corruption

Pipeline:
1. Load documents
2. Chunk
3. Embed (Gemini API)
4. Store in FAISS
5. Save locally
"""

import os
import sys
import time

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

from loaders import load_all_documents

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VECTOR_DIR = "./faiss_db"

# ⚠️ safe Gemini embedding model
EMBED_MODEL = "gemini-embedding-001"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# 🔥 IMPORTANT: keep small to avoid quota issues
EMBED_BATCH_SIZE = 10

SLEEP_BETWEEN_BATCHES = 65  # prevents 429

REQUIRED_METADATA_KEYS = [
    "source",
    "department",
    "role",
    "document_type",
    "classification"
]

# ─────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────

def ensure_metadata(docs):
    for doc in docs:
        for key in REQUIRED_METADATA_KEYS:
            doc.metadata.setdefault(key, "unknown")
    return docs


def sanitize_metadata(docs):
    for doc in docs:
        clean = {}
        for k, v in doc.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        doc.metadata = clean
    return docs


# ─────────────────────────────────────────────
# CHUNKING
# ─────────────────────────────────────────────

def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_documents(documents)

    print(f"✂️ Chunked {len(documents)} → {len(chunks)} chunks")
    return chunks


# ─────────────────────────────────────────────
# EMBEDDINGS
# ─────────────────────────────────────────────

def get_embeddings():
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ Missing GOOGLE_API_KEY in .env")
        sys.exit(1)

    print(f"🔢 Using Gemini embedding model: {EMBED_MODEL}")

    return GoogleGenerativeAIEmbeddings(
        model=EMBED_MODEL,
        google_api_key=api_key,
        task_type="retrieval_document"
    )


# ─────────────────────────────────────────────
# FAISS BUILDER (RATE LIMIT SAFE)
# ─────────────────────────────────────────────

def build_vector_store(chunks, embeddings):
    print(f"🗄️ Building FAISS index at {VECTOR_DIR}")

    vectorstore = None
    total_batches = (len(chunks) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE

    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        batch_num = i // EMBED_BATCH_SIZE + 1

        print(f"⏳ Batch {batch_num}/{total_batches}")

        texts = [d.page_content for d in batch]
        metas = [d.metadata for d in batch]

        try:
            if vectorstore is None:
                vectorstore = FAISS.from_texts(
                    texts=texts,
                    embedding=embeddings,
                    metadatas=metas
                )
            else:
                vectorstore.add_texts(
                    texts=texts,
                    metadatas=metas
                )

        except Exception as e:
            print(f"⚠️ Batch failed: {e}")
            print("⏳ Sleeping 60s then retrying...")
            time.sleep(60)

            if vectorstore is None:
                vectorstore = FAISS.from_texts(
                    texts=texts,
                    embedding=embeddings,
                    metadatas=metas
                )
            else:
                vectorstore.add_texts(
                    texts=texts,
                    metadatas=metas
                )

        # 🔥 CRITICAL RATE LIMIT CONTROL
        time.sleep(SLEEP_BETWEEN_BATCHES)

    vectorstore.save_local(VECTOR_DIR)

    print(f"✅ FAISS saved at {VECTOR_DIR}")
    return vectorstore


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def run_ingestion(data_dir="data"):
    print("\n" + "=" * 60)
    print(" ENTERPRISE RAG - FAISS INGESTION")
    print("=" * 60)

    print("\n📂 Loading documents...")
    documents = load_all_documents(base_dir=data_dir)

    if not documents:
        print("❌ No documents found")
        sys.exit(1)

    print("🔍 Validating metadata...")
    documents = ensure_metadata(documents)
    documents = sanitize_metadata(documents)

    print("✂️ Chunking documents...")
    chunks = chunk_documents(documents)
    chunks = sanitize_metadata(chunks)

    print("🔢 Creating embeddings + FAISS index...")
    embeddings = get_embeddings()

    build_vector_store(chunks, embeddings)

    print("\n" + "=" * 60)
    print("✅ INGESTION COMPLETE")
    print(f"Total chunks: {len(chunks)}")
    print(f"Vector DB: {VECTOR_DIR}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_ingestion()