"""
rag_pipeline.py
---------------
Core RAG pipeline using:
- FAISS vector store
- Gemini embeddings (text-embedding-004)
- Gemini LLM (flash)
- RBAC security layer
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional, List

from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage

from prompts import RAG_PROMPT
from security import build_chroma_filter, check_access

load_dotenv()


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

FAISS_DIR = "./faiss_db"
GEMINI_MODEL = "gemini-2.5-flash"


# ─────────────────────────────────────────────
# RESULT OBJECT
# ─────────────────────────────────────────────

@dataclass
class RAGResult:
    answer: str = ""
    sources: List[str] = field(default_factory=list)
    retrieved_chunks: List[Document] = field(default_factory=list)
    role: str = ""
    username: str = ""
    access_granted: bool = False
    access_message: str = ""
    confidence: float = 0.0
    latency_seconds: float = 0.0
    error: Optional[str] = None


# ─────────────────────────────────────────────
# SINGLETONS
# ─────────────────────────────────────────────

_embeddings = None
_vectorstore = None
_llm = None


# ─────────────────────────────────────────────
# EMBEDDINGS (GEMINI)
# ─────────────────────────────────────────────

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
        )
    return _embeddings


# ─────────────────────────────────────────────
# FAISS VECTORSTORE
# ─────────────────────────────────────────────

def get_vectorstore():
    global _vectorstore

    if _vectorstore is None:
        if not os.path.exists(FAISS_DIR):
            raise RuntimeError(
                "FAISS index not found. Run ingestion script first:\n"
                "python ingest.py"
            )

        _vectorstore = FAISS.load_local(
            FAISS_DIR,
            get_embeddings(),
            allow_dangerous_deserialization=True
        )

    return _vectorstore


# ─────────────────────────────────────────────
# LLM (GEMINI)
# ─────────────────────────────────────────────

def get_llm():
    global _llm
    if _llm is None:
        # api_key = os.getenv("GOOGLE_API_KEY")
        import streamlit as st
        api_key = st.secrets["GOOGLE_API_KEY"]
        if not api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY in .env")

        _llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=1024,
        )
    return _llm


# ─────────────────────────────────────────────
# RETRIEVAL (FAISS)
# ─────────────────────────────────────────────

def retrieve_documents(query: str, role: str) -> List[Document]:
    vs = get_vectorstore()

    # FAISS does NOT support Chroma-style filters natively
    # So we do post-filtering using metadata

    results = vs.similarity_search_with_score(query, k=8)

    docs = []
    for doc, score in results:
        # lower score = better in FAISS
        if score < 1.2:
            docs.append(doc)

    if role.lower() == "admin":
        return docs

    allowed_filter = build_chroma_filter(role)

    if not allowed_filter:
        return docs

    allowed_dept = None
    if "$eq" in allowed_filter.get("department", {}):
        allowed_dept = [allowed_filter["department"]["$eq"]]

    if "$in" in allowed_filter.get("department", {}):
        allowed_dept = allowed_filter["department"]["$in"]

    filtered = []
    for d in docs:
        dept = d.metadata.get("department")
        if dept in allowed_dept:
            filtered.append(d)

    return filtered


# ─────────────────────────────────────────────
# CONTEXT BUILDER
# ─────────────────────────────────────────────

def assemble_context(docs: List[Document]) -> str:
    if not docs:
        return "No relevant context found."

    context_parts = []

    for i, d in enumerate(docs, start=1):
        source = d.metadata.get("source", "unknown")
        dept = d.metadata.get("department", "unknown")
        classification = d.metadata.get("classification", "unknown")

        chunk = f"""
        DOCUMENT {i}
        Source: {source}
        Department: {dept}
        Classification: {classification}

        Content:
        {d.page_content}
        """
        context_parts.append(chunk)

    return "\n\n".join(context_parts)

# ─────────────────────────────────────────────
# CONFIDENCE SCORE
# ─────────────────────────────────────────────

def estimate_confidence(docs: List[Document], answer: str) -> float:
    if not docs:
        return 0.0

    base = min(len(docs) / 5, 1.0) * 0.7
    bonus = 0.2 if len(answer) > 100 else 0.1
    return round(min(base + bonus, 1.0), 2)


# ─────────────────────────────────────────────
# GENERATION
# ─────────────────────────────────────────────

def generate_answer(query: str, context: str, role: str) -> str:
    llm = get_llm()

    prompt = RAG_PROMPT.format(
        role=role,
        context=context,
        question=query
    )

    res = llm.invoke([HumanMessage(content=prompt)])
    return res.content


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def run_rag_query(username: str, query: str) -> RAGResult:
    start = time.time()
    result = RAGResult(username=username)

    allowed, role, msg = check_access(username)
    result.role = role
    result.access_granted = allowed
    result.access_message = msg

    if not allowed:
        result.answer = "Access Denied"
        result.latency_seconds = time.time() - start
        return result

    try:
        docs = retrieve_documents(query, role)
        result.retrieved_chunks = docs
    except Exception as e:
        result.error = str(e)
        result.answer = "Retrieval failed"
        return result

    if not docs:
        result.answer = "No authorized information found for this query."
        return result

    context = assemble_context(docs)

    try:
        answer = generate_answer(query, context, role)
    except Exception as e:
        result.error = str(e)
        result.answer = "LLM generation failed"
        return result

    result.answer = answer
    result.sources = list({d.metadata.get("source", "unknown") for d in docs})
    result.confidence = estimate_confidence(docs, answer)
    result.latency_seconds = round(time.time() - start, 2)

    return result