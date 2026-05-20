"""
loaders.py
----------
Multi-format document loaders.

Each loader reads a specific data format and returns a list of
LangChain `Document` objects with rich metadata.

Supported formats:
  - PDF  (via PyPDFLoader)
  - CSV  (via pandas)
  - JSON (logs, metadata, policies)
"""

import json
import os
import traceback
from typing import Optional

import pandas as pd
from langchain_core.documents import Document


# ─────────────────────────────────────────────
# PDF Loader
# ─────────────────────────────────────────────

def load_pdf(file_path: str, metadata_override: Optional[dict] = None) -> list[Document]:
    """
    Load a PDF file and return a list of LangChain Documents (one per page).

    Args:
        file_path: Path to the PDF file.
        metadata_override: Extra metadata to merge into every page's metadata.

    Returns:
        List of Document objects, one per page.
    """
    try:
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        pages = loader.load()

        # Enrich metadata on each page
        for page in pages:
            page.metadata["source"] = os.path.basename(file_path)
            page.metadata["document_type"] = "pdf"
            if metadata_override:
                page.metadata.update(metadata_override)

        print(f"  📄  Loaded PDF: {os.path.basename(file_path)} ({len(pages)} pages)")
        return pages

    except Exception as e:
        print(f"  ⚠️  Failed to load PDF {file_path}: {e}")
        traceback.print_exc()
        return []


# ─────────────────────────────────────────────
# CSV Loader
# ─────────────────────────────────────────────

def load_csv(file_path: str, metadata_override: Optional[dict] = None) -> list[Document]:
    """
    Load a CSV file.

    Strategy:
      - Read the file with pandas.
      - Convert every row into a key=value text block.
      - Batch rows into groups of 10 to avoid micro-chunks.
      - Attach metadata to each batch Document.

    Args:
        file_path: Path to the CSV file.
        metadata_override: Extra metadata.

    Returns:
        List of Document objects.
    """
    try:
        df = pd.read_csv(file_path)
        documents: list[Document] = []

        # Group every BATCH_SIZE rows into a single Document
        BATCH_SIZE = 10
        source_name = os.path.basename(file_path)

        for start in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[start : start + BATCH_SIZE]

            # Build a human-readable text block
            rows_text = "\n".join(
                " | ".join(f"{col}: {row[col]}" for col in df.columns)
                for _, row in batch.iterrows()
            )
            text = f"[CSV Rows {start + 1}–{min(start + BATCH_SIZE, len(df))} of {source_name}]\n{rows_text}"

            meta = {
                "source": source_name,
                "document_type": "csv",
                "row_start": start + 1,
                "row_end": min(start + BATCH_SIZE, len(df)),
            }
            if metadata_override:
                meta.update(metadata_override)

            documents.append(Document(page_content=text, metadata=meta))

        print(f"  📊  Loaded CSV: {source_name} ({len(df)} rows → {len(documents)} chunks)")
        return documents

    except Exception as e:
        print(f"  ⚠️  Failed to load CSV {file_path}: {e}")
        traceback.print_exc()
        return []


# ─────────────────────────────────────────────
# JSON Log Loader
# ─────────────────────────────────────────────

def load_json_log(file_path: str, metadata_override: Optional[dict] = None) -> list[Document]:
    """
    Load a JSON log file (list of event objects).

    Strategy:
      - Parse the JSON array.
      - Batch every BATCH_SIZE entries into one Document.
      - Converts each entry to a readable key: value string.

    Args:
        file_path: Path to the JSON log file.
        metadata_override: Extra metadata.

    Returns:
        List of Document objects.
    """
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Support both list-of-objects and dict (flatten dict values)
        if isinstance(data, dict):
            entries = list(data.values()) if all(
                isinstance(v, dict) for v in data.values()
            ) else [data]
        else:
            entries = data

        BATCH_SIZE = 10
        source_name = os.path.basename(file_path)
        documents: list[Document] = []

        for start in range(0, len(entries), BATCH_SIZE):
            batch = entries[start : start + BATCH_SIZE]

            rows_text = "\n".join(
                "  ".join(f"{k}: {v}" for k, v in entry.items())
                for entry in batch
                if isinstance(entry, dict)
            )
            text = (
                f"[JSON Log Entries {start + 1}–{min(start + BATCH_SIZE, len(entries))} "
                f"of {source_name}]\n{rows_text}"
            )

            meta = {
                "source": source_name,
                "document_type": "json",
                "entry_start": start + 1,
                "entry_end": min(start + BATCH_SIZE, len(entries)),
            }
            if metadata_override:
                meta.update(metadata_override)

            documents.append(Document(page_content=text, metadata=meta))

        print(f"  🔐  Loaded JSON: {source_name} ({len(entries)} entries → {len(documents)} chunks)")
        return documents

    except Exception as e:
        print(f"  ⚠️  Failed to load JSON {file_path}: {e}")
        traceback.print_exc()
        return []


# ─────────────────────────────────────────────
# Metadata JSON Loader
# ─────────────────────────────────────────────

def load_metadata_json(file_path: str, metadata_override: Optional[dict] = None) -> list[Document]:
    """
    Load a metadata or catalog JSON file as a single Document.

    Used for document_metadata.json and dataset_catalog.json.

    Args:
        file_path: Path to the metadata JSON.
        metadata_override: Extra metadata.

    Returns:
        List with a single Document.
    """
    try:
        with open(file_path) as f:
            data = json.load(f)

        text = f"[Metadata: {os.path.basename(file_path)}]\n{json.dumps(data, indent=2)}"

        meta = {
            "source": os.path.basename(file_path),
            "document_type": "metadata",
            "department": "admin",
            "role": "Admin",
        }
        if metadata_override:
            meta.update(metadata_override)

        print(f"  📋  Loaded metadata: {os.path.basename(file_path)}")
        return [Document(page_content=text, metadata=meta)]

    except Exception as e:
        print(f"  ⚠️  Failed to load metadata {file_path}: {e}")
        return []


# ─────────────────────────────────────────────
# Convenience: Load All Data
# ─────────────────────────────────────────────

def load_all_documents(base_dir: str = "data") -> list[Document]:
    """
    Master loader — calls all individual loaders and returns
    the combined list of Documents with proper metadata.

    Args:
        base_dir: Root data directory.

    Returns:
        Combined list of all Document objects.
    """

    # Per-file metadata lookup (department + role for RBAC filtering)
    FILE_META: dict[str, dict] = {
        # PDFs
        "finance_report.pdf":      {"department": "finance",  "role": "Finance",  "classification": "confidential"},
        "hr_policy.pdf":           {"department": "hr",       "role": "HR",       "classification": "internal"},
        "security_audit.pdf":      {"department": "security", "role": "Security", "classification": "restricted"},
        # CSVs
        "employee_records.csv":    {"department": "hr",       "role": "HR",       "classification": "confidential"},
        "finance_transactions.csv":{"department": "finance",  "role": "Finance",  "classification": "confidential"},
        "operations_metrics.csv":  {"department": "operations","role": "Admin",   "classification": "internal"},
        # JSON logs
        "security_logs.json":      {"department": "security", "role": "Security", "classification": "restricted"},
        "audit_trail.json":        {"department": "security", "role": "Security", "classification": "restricted"},
        "alerts.json":             {"department": "security", "role": "Security", "classification": "restricted"},
    }

    all_docs: list[Document] = []

    # ── PDFs ──────────────────────────────────
    pdf_dir = os.path.join(base_dir, "pdfs")
    for fname in os.listdir(pdf_dir):
        if fname.endswith(".pdf"):
            docs = load_pdf(
                os.path.join(pdf_dir, fname),
                metadata_override=FILE_META.get(fname),
            )
            all_docs.extend(docs)

    # ── CSVs ──────────────────────────────────
    csv_dir = os.path.join(base_dir, "csv")
    for fname in os.listdir(csv_dir):
        if fname.endswith(".csv"):
            docs = load_csv(
                os.path.join(csv_dir, fname),
                metadata_override=FILE_META.get(fname),
            )
            all_docs.extend(docs)

    # ── JSON Logs ─────────────────────────────
    log_dir = os.path.join(base_dir, "json_logs")
    for fname in os.listdir(log_dir):
        if fname.endswith(".json"):
            docs = load_json_log(
                os.path.join(log_dir, fname),
                metadata_override=FILE_META.get(fname),
            )
            all_docs.extend(docs)

    # ── Metadata (Admin only) ─────────────────
    meta_dir = os.path.join(base_dir, "metadata")
    for fname in os.listdir(meta_dir):
        if fname.endswith(".json"):
            docs = load_metadata_json(os.path.join(meta_dir, fname))
            all_docs.extend(docs)

    print(f"\n📦  Total documents loaded: {len(all_docs)}\n")
    return all_docs