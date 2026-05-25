"""
app.py
------
Enterprise RAG — Streamlit UI

Features:
  - User login via dropdown (simulated)
  - Auto role detection
  - Query input with demo suggestions
  - RBAC-filtered response generation
  - Citations and explainability panel
  - Confidence score + latency indicator
  - Expandable retrieved chunks viewer
  - Access policy info sidebar
"""

import streamlit as st

from langchain_core.documents import Document

from rag_pipeline import run_rag_query
from security import get_all_users, get_user_role, get_role_summary
from utils import check_setup, get_demo_queries, role_badge_color, truncate_text


# ─────────────────────────────────────────────
# Page Config (MUST be first Streamlit call)
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# Custom CSS — enterprise-style dark theme
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* Main layout */
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* Header */
    .rag-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #e94560;
    }
    .rag-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .rag-header p  { color: #94a3b8; margin: 0.3rem 0 0; font-size: 0.9rem; }

    /* Role badge */
    .role-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: white;
        margin: 0.3rem 0;
    }

    /* Answer card */
    .answer-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin: 0.8rem 0;
        line-height: 1.7;
        color: #1e293b;
    }

    /* Access denied */
    .access-denied {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-left: 4px solid #e53e3e;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        color: #c53030;
        font-weight: 500;
    }

    /* Source chip */
    .source-chip {
        display: inline-block;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1d4ed8;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.78rem;
        margin: 0.2rem;
        font-family: monospace;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e40af;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Sidebar section header */
    .sidebar-header {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94a3b8;
        margin: 1rem 0 0.3rem;
    }

    /* Chunk preview */
    .chunk-text {
        font-size: 0.82rem;
        background: #f1f5f9;
        border-radius: 8px;
        padding: 0.7rem;
        line-height: 1.5;
        color: #334155;
        font-family: monospace;
    }

    /* Access granted banner */
    .access-granted {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #22c55e;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.85rem;
        color: #15803d;
    }

    /* Security info box */
    .security-box {
        background: #fefce8;
        border: 1px solid #fde047;
        border-radius: 8px;
        padding: 0.8rem;
        font-size: 0.82rem;
        color: #713f12;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Pre-flight Setup Check
# ─────────────────────────────────────────────

def show_setup_error(issues: list[str]) -> None:
    """Display a clear setup guide if system is not ready."""
    st.error("⚠️ System not ready. Please complete the setup steps below.")

    st.markdown("### 🛠️ Setup Required")
    with st.expander("View setup instructions", expanded=True):
        st.markdown("""
**Step 1: Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 2: Add your Gemini API key**
```bash
cp .env.example .env
# Edit .env and add: GOOGLE_API_KEY=your_key_here
# Get a free key at: https://aistudio.google.com/app/apikey
```

**Step 3: Generate sample data**
```bash
python dataset_generator.py
```

**Step 4: Ingest documents**
```bash
python ingest.py
```

**Step 5: Run the app**
```bash
streamlit run app.py
```
""")
        st.markdown("**Issues detected:**")
        for issue in issues:
            st.error(f"• {issue}")
    st.stop()


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

def render_sidebar(selected_user: str, role: str) -> None:
    """Render the sidebar with user info, role details, and access policy."""
    with st.sidebar:
        st.markdown("## 🏢 Enterprise RAG")
        st.markdown("*Acme Corp Internal Assistant*")
        st.divider()

        # User & Role info
        st.markdown('<div class="sidebar-header">Current Session</div>', unsafe_allow_html=True)
        st.markdown(f"**User:** `{selected_user}`")

        # Role badge
        color = role_badge_color(role)
        st.markdown(
            f'<span class="role-badge" style="background:{color};">{role}</span>',
            unsafe_allow_html=True,
        )

        # Role permissions summary
        if role:
            st.divider()
            st.markdown('<div class="sidebar-header">Access Policy</div>', unsafe_allow_html=True)
            try:
                summary = get_role_summary(role)

                if summary["is_admin"]:
                    st.success("🔓 Full access (Admin)")
                else:
                    st.markdown("**Allowed Sources:**")
                    for src in summary.get("allowed_sources", []):
                        st.markdown(f"  • `{src}`")

                    st.markdown("**Classifications:**")
                    for c in summary.get("allowed_classifications", []):
                        st.markdown(f"  • {c}")

                    caps = []
                    if summary.get("can_export"):
                        caps.append("Export")
                    if summary.get("can_edit"):
                        caps.append("Edit")
                    if caps:
                        st.markdown(f"**Capabilities:** {', '.join(caps)}")
                    else:
                        st.markdown("**Capabilities:** Read-only")

            except Exception:
                st.warning("Could not load role summary.")

        # Security notice
        st.divider()
        st.markdown(
            '<div class="security-box">🔐 <strong>RBAC Active</strong><br>'
            "All queries are filtered by your role. "
            "Unauthorized documents never reach the AI model.</div>",
            unsafe_allow_html=True,
        )

        # About
        st.divider()
        st.markdown('<div class="sidebar-header">System Info</div>', unsafe_allow_html=True)
        st.markdown("**LLM:** Gemini 2.5 Flash")
        st.markdown("**Embeddings:** gemini-embedding-001")
        st.markdown("**Vector DB:** FAISS")
        st.markdown("**Framework:** LangChain")


# ─────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────

def main() -> None:
    # ── Pre-flight check ──────────────────────
    is_ready, issues = check_setup()
    if not is_ready:
        show_setup_error(issues)

    # ── Header ────────────────────────────────
    st.markdown("""
    <div class="rag-header">
        <h1>🏢 Enterprise RAG Assistant</h1>
        <p>Secure AI-powered knowledge retrieval with Role-Based Access Control</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Layout: two columns ───────────────────
    left_col, right_col = st.columns([3, 1])

    with left_col:
        # ── User Selection ────────────────────
        st.markdown("### 👤 Login")
        col1, col2 = st.columns([2, 1])

        with col1:
            users = get_all_users()
            selected_user = st.selectbox(
                "Select your username:",
                options=users,
                index=0,
                help="In a real system this would be your SSO login.",
            )

        role = get_user_role(selected_user) or "Unknown"

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            color = role_badge_color(role)
            st.markdown(
                f'<div style="margin-top:0.5rem;">'
                f'Role: <span class="role-badge" style="background:{color};">{role}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

        # Access status
        if role != "Unknown":
            st.markdown(
                f'<div class="access-granted">✅ Authenticated — {role} role permissions active</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Query Section ─────────────────────
        st.markdown("### 💬 Ask a Question")

        # Demo query suggestions
        demo_queries = get_demo_queries(role)
        selected_demo = st.selectbox(
            "Try a demo query:",
            options=["(Type your own question below)"] + demo_queries,
            index=0,
        )

        # Populate text area with demo if chosen
        prefill = "" if selected_demo.startswith("(") else selected_demo

        query = st.text_area(
            "Your question:",
            value=prefill,
            height=100,
            placeholder="Ask anything about your department's data…",
        )

        # Submit button
        col_btn1, col_btn2 = st.columns([1, 5])
        with col_btn1:
            submit = st.button("🔍 Ask", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🧹 Clear", use_container_width=False):
                query = ""
                st.rerun()

    # Sidebar (rendered after we know the user/role)
    render_sidebar(selected_user, role)

    # ── Results Section ───────────────────────
    if submit and query.strip():
        with st.spinner("🔄 Retrieving and generating answer…"):
            result = run_rag_query(username=selected_user, query=query.strip())

        st.divider()
        st.markdown("## 📋 Results")

        # ── Metrics row ───────────────────────
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            conf_pct = int(result.confidence * 100)
            conf_color = "#22c55e" if conf_pct >= 60 else "#f59e0b" if conf_pct >= 30 else "#ef4444"
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value" style="color:{conf_color}">{conf_pct}%</div>'
                f'<div class="metric-label">Confidence</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{len(result.retrieved_chunks)}</div>'
                f'<div class="metric-label">Chunks Retrieved</div></div>',
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{len(result.sources)}</div>'
                f'<div class="metric-label">Sources</div></div>',
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{result.latency_seconds}s</div>'
                f'<div class="metric-label">Latency</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Access Decision ───────────────────
        with st.expander("🔐 Access Control Decision", expanded=False):
            if result.access_granted:
                st.success(f"✅ {result.access_message}")
            else:
                st.error(f"⛔ {result.access_message}")

            st.markdown(f"**Role applied:** `{result.role}`")
            st.markdown(f"**Filter:** RBAC metadata filtering active")

            if result.role and result.access_granted:
                from security import build_chroma_filter
                filt = build_chroma_filter(result.role)
                if filt:
                    st.markdown(f"**VectorDB filter:** `{filt}`")
                else:
                    st.markdown("**VectorDB filter:** None (Admin — full access)")

        # ── Answer ────────────────────────────
        st.markdown("### 🤖 Answer")

        if not result.access_granted or "Access Denied" in result.answer:
            st.markdown(
                f'<div class="access-denied">⛔ {result.answer}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="answer-card">{result.answer}</div>',
                unsafe_allow_html=True,
            )

        # ── Sources / Citations ───────────────
        if result.sources:
            st.markdown("### 📎 Sources & Citations")
            chips = "".join(
                f'<span class="source-chip">📄 {src}</span>'
                for src in result.sources
            )
            st.markdown(chips, unsafe_allow_html=True)

        # ── Retrieved Chunks (Expandable) ─────
        if result.retrieved_chunks:
            st.markdown("### 🔎 Retrieved Chunks")
            for i, doc in enumerate(result.retrieved_chunks, 1):
                source = doc.metadata.get("source", "unknown")
                dept = doc.metadata.get("department", "—")
                doc_type = doc.metadata.get("document_type", "—")
                classif = doc.metadata.get("classification", "—")

                with st.expander(f"Chunk {i} — {source}", expanded=(i == 1)):
                    cols = st.columns(3)
                    cols[0].markdown(f"**Dept:** `{dept}`")
                    cols[1].markdown(f"**Type:** `{doc_type}`")
                    cols[2].markdown(f"**Class:** `{classif}`")

                    st.markdown(
                        f'<div class="chunk-text">{truncate_text(doc.page_content, 500)}</div>',
                        unsafe_allow_html=True,
                    )

        # ── Error Details (if any) ────────────
        if result.error:
            with st.expander("⚠️ Error Details"):
                st.code(result.error)

    elif submit and not query.strip():
        st.warning("Please enter a question before submitting.")

    # ── Footer ────────────────────────────────
    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#94a3b8;font-size:0.8rem;'>"
        "🏢 Acme Corp Enterprise RAG | Powered by Gemini + ChromaDB + LangChain | "
        "Built with ❤️ for hackathon demo</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()