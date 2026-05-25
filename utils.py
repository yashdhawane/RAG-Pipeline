"""
utils.py
--------
Shared utility functions used across the project.
"""

import json
import os
from datetime import datetime


def check_setup() -> tuple[bool, list[str]]:
    """
    Pre-flight check before running the app.

    Verifies:
      - data/ directory and subdirectories exist
      - chroma_db/ exists (ingestion has been run)
      - .env file exists with GOOGLE_API_KEY

    Returns:
        (is_ready: bool, list_of_issues: list[str])
    """
    issues = []

    # Check data directories
    required_dirs = [
        "data/pdfs",
        "data/csv",
        "data/json_logs",
        "data/metadata",
        "data/access_policies",
        "data/user_roles",
    ]
    for d in required_dirs:
        if not os.path.isdir(d):
            issues.append(f"Missing directory: {d}")
        elif len(os.listdir(d)) == 0:
            issues.append(f"Empty directory: {d}")

    # Check vector DB
    if not os.path.isdir("faiss_db"):
        issues.append("FAISS index not found. Run: python ingest.py")

    # Check .env
    # if not os.path.exists(".env"):
    #     issues.append(".env file missing. Copy .env.example and add your GOOGLE_API_KEY.")
    # else:
    #     from dotenv import dotenv_values
    #     env = dotenv_values(".env")
    #     if not env.get("GOOGLE_API_KEY") or env.get("GOOGLE_API_KEY") == "your_api_key_here":
    #         issues.append("GOOGLE_API_KEY not set in .env file.")

    try:
        import streamlit as st
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            issues.append("GOOGLE_API_KEY not set in Streamlit secrets")
    except:
        pass  # Running locally, not on Streamlit Cloud

    return len(issues) == 0, issues


def format_timestamp(dt: datetime | None = None) -> str:
    """Return a formatted timestamp string."""
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def truncate_text(text: str, max_chars: int = 400) -> str:
    """Truncate a string and add ellipsis if over limit."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


def get_demo_queries(role: str) -> list[str]:
    """
    Return a list of demo queries appropriate for a given role.
    Used to pre-populate the Streamlit UI.
    """
    queries = {
        "HR": [
            "What is the annual leave policy?",
            "How are performance reviews conducted?",
            "Show employee leave balance information.",
            "What is the recruitment process?",
            "Describe the code of conduct policy.",
        ],
        "Finance": [
            "Summarize Q2 2024 revenue.",
            "What was the net profit margin in Q2?",
            "Show recent finance transactions.",
            "What are the operating expenses breakdown?",
            "Explain the Q3 revenue forecast.",
        ],
        "Security": [
            "Show recent failed login attempts.",
            "What critical vulnerabilities were found in the audit?",
            "List recent security alerts.",
            "What is the remediation status of CVE-2024-1234?",
            "Summarize the security audit findings.",
        ],
        "Admin": [
            "Give me a summary of all departments.",
            "Show all recent security alerts and finance highlights.",
            "What documents are in the system?",
            "Summarize HR policies and finance report.",
            "What are the operations metrics for Q1 2024?",
        ],
    }
    return queries.get(role, ["What information is available to me?"])


def role_badge_color(role: str) -> str:
    """Return a color hex code for role badges in the UI."""
    colors = {
        "HR": "#28a745",        # green
        "Finance": "#007bff",   # blue
        "Security": "#dc3545",  # red
        "Admin": "#6f42c1",     # purple
    }
    return colors.get(role, "#6c757d")


def load_json_file(path: str) -> dict | list | None:
    """Safely load a JSON file; return None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None