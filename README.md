# 🏢 Enterprise RAG Assistant

Secure AI-powered knowledge retrieval with Role-Based Access Control, built with LangChain, Gemini, and FAISS.

**Table of Contents**
- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [RAG Pipeline Workflow](#rag-pipeline-workflow)
- [User Query Execution](#user-query-execution)
- [Engineering Concepts](#engineering-concepts)
- [Key Metrics](#key-metrics)
- [Security Architecture](#security-architecture)
- [Project Workflow](#project-workflow)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Free Gemini API key from [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 4-Step Setup

#### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env and add your free Gemini API key
# GOOGLE_API_KEY=your_key_here
```

#### Step 3: Generate Sample Data
```bash
python dataset_generator.py
```
This creates synthetic enterprise data in the `data/` directory (PDFs, CSVs, JSON logs, policies, user mappings).

#### Step 4: Ingest & Run
```bash
python ingest.py               # Embed documents into FAISS vector DB
streamlit run app.py           # Launch web UI
```

The app will be available at `http://localhost:8501`

---

## 🏗️ Architecture Overview

This is an **Enterprise RAG (Retrieval-Augmented Generation) System** combining secure document retrieval with AI-powered responses. The system prioritizes **Role-Based Access Control (RBAC)** and **security-first design**.

### Core Components

1. **Data Layer** — Multi-format document sources
   - PDFs (Finance reports, HR policies, Security audits)
   - CSVs (Employee records, financial transactions, operations metrics)
   - JSON logs (Audit trails, alerts, security events)
   - Metadata catalogs

2. **Ingestion Pipeline** — Data preparation & vectorization
3. **Vector Store** — FAISS for semantic search
4. **Security Engine** — RBAC enforcement
5. **RAG Core** — Retrieval + generation
6. **UI Layer** — Streamlit web interface

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        📊 DATA LAYER                            │
│   PDFs  │  CSVs  │  JSON Logs  │  Metadata Catalogs            │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ⚙️ INGESTION PIPELINE                          │
│  Load → Chunk → Enrich Metadata → Embed → Store in FAISS       │
│  (loaders.py / ingest.py)                                       │
│  • Chunk size: 500 chars, 50 overlap                            │
│  • Embeddings: Gemini API (batch safe)                          │
│  • Metadata: department, role, classification                   │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🗄️ VECTOR STORE (FAISS)                      │
│  768-dimensional embeddings + metadata                          │
│  Lightweight, CPU-based, serverless                             │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌──────────────┐  ┌──────────────────────┐
│🔐 SECURITY   │  │ 🧠 RAG CORE         │
│LAYER         │  │ • Retrieve (k=8)    │
│              │  │ • Filter (score<1.2)│
│1. Auth       │  │ • Assemble context  │
│2. RBAC       │  │ • Generate answer   │
│3. Filter     │  │ • Confidence score  │
└──────────────┘  └──────────────────────┘
                        │
                        ▼
                  ┌──────────────────┐
                  │💻 UI LAYER       │
                  │(Streamlit)       │
                  │• Results display │
                  │• Citations       │
                  │• Metrics         │
                  └──────────────────┘
```

---

## 🔄 RAG Pipeline Workflow

### Phase 1: INGESTION (`ingest.py` + `loaders.py`)

```
Data Files → Load → Chunk → Enrich Metadata → Embed → Store in FAISS
```

#### Step 1: Document Loading
- **PDFs**: One page per document using `PyPDFLoader`
- **CSVs**: Batched (10 rows per chunk) for readability
- **JSON**: Batched (10 entries per chunk)
- **Result**: Each chunk gets metadata: `source`, `department`, `role`, `classification`

#### Step 2: Chunking
- **Size**: 500 characters with 50-character overlap
- **Splitter**: `RecursiveCharacterTextSplitter` (hierarchical: paragraphs → sentences → words)
- **Goal**: Semantic coherence while fitting LLM context windows

#### Step 3: Metadata Enrichment
- Attach department (`finance`, `hr`, `security`)
- Attach required access role
- Add classification level (`confidential`, `internal`, `restricted`)
- **Critical**: This metadata enables RBAC filtering

#### Step 4: Embedding Generation
- **Model**: Gemini Embedding 001 (768-dimensional vectors)
- **Batch size**: 10 documents (API rate-limit safe)
- **Sleep**: 65 seconds between batches to avoid 429 errors
- **Result**: Converts text → mathematical vectors for semantic search

#### Step 5: Vector Store Creation
- **Framework**: FAISS (Facebook AI Similarity Search)
- **Storage**: Lightweight, CPU-based, no server needed
- **Location**: `./faiss_db/` directory
- **Preservation**: Metadata travels with vectors

---

### Phase 2: QUERY EXECUTION (`rag_pipeline.py`)

```
User Query → Authentication → RBAC Filter → Retrieval → Context Assembly → LLM Generation → Confidence Score → Results
```

#### Step 1: User Authentication
- Lookup username in `user_role_mapping.json`
- Resolve role: `Admin`, `HR`, `Finance`, `Security`, or `Unknown`
- If role not found → **Access Denied immediately** (fail-safe)

#### Step 2: RBAC Permission Check
Build a metadata filter based on role:
- **Admin role**: `None` filter (sees everything)
- **HR role**: `{"department": {"$eq": "hr"}}`
- **Finance role**: `{"department": {"$eq": "finance"}}`
- **Security role**: `{"department": {"$eq": "security"}}`
- **Unknown role**: `{"department": {"$eq": "__DENY_ALL__"}}` (impossible match)

#### Step 3: Document Retrieval
1. Convert user question to vector via Gemini embeddings
2. FAISS similarity search: Find k=8 most similar chunks
3. Post-filtering: Keep only chunks with similarity score < 1.2
4. RBAC filtering: Filter chunks by allowed department metadata
5. **Result**: ~3-8 authorized chunks relevant to query

#### Step 4: Context Assembly
- Combine retrieved chunks into structured text format
- Format: `DOCUMENT 1: Source | Department | Classification | Content`
- Result: Combined context string (~1000-2000 chars)

#### Step 5: LLM Generation
- **LLM**: Gemini 2.5 Flash (fast, cost-effective)
- **Prompt**: Enforces context-only answers (no hallucination)
- **Temperature**: 0.2 (deterministic, factual)
- **Max tokens**: 1024

Prompt rules:
- Answer ONLY from retrieved context
- Mention sources
- Use bullet points
- Admit missing information gracefully
- Do not invent or hallucinate

#### Step 6: Confidence Scoring
```
base = min(num_docs/5, 1.0) * 0.7
bonus = 0.2 if answer_length > 100 else 0.1
confidence = min(base + bonus, 1.0)  # Range: 0.0–1.0
```
- More docs + longer answer = higher confidence
- Displayed as percentage in UI

#### Step 7: Result Packaging
Return structured `RAGResult`:
- Answer text
- Sources list
- Retrieved chunks
- Confidence score (0.0–1.0)
- Latency (milliseconds)
- Access grant/denial status

---

## 👥 User Query Execution

### Complete Flow Sequence

```
1. User selects username from dropdown
   ↓
2. System verifies role in user_role_mapping.json
   ↓
3. UI displays role-specific demo queries
   ↓
4. User enters question
   ↓
5. UI displays access policy summary in sidebar
   ↓
6. User clicks "Ask" button
   ↓
7. System validates access (check_access)
   ├─ Access Denied → Show error message
   └─ Access Granted → Continue
   ↓
8. run_rag_query() executes pipeline:
   ├─ Embed question (Gemini Embeddings)
   ├─ Search FAISS index (k=8)
   ├─ Post-filter by similarity score
   ├─ Apply RBAC metadata filter
   ├─ Assemble context from chunks
   ├─ Generate answer (Gemini LLM)
   ├─ Calculate confidence score
   └─ Measure latency
   ↓
9. UI renders complete result:
   ├─ Confidence % (color-coded)
   ├─ Chunks retrieved count
   ├─ Unique sources count
   ├─ Latency in seconds
   ├─ Access decision details
   ├─ Answer text (styled card)
   └─ Expandable chunks viewer
   ↓
10. User sees citations and metadata
```

---

## 🛠️ Engineering Concepts Applied

### 1. **Retrieval-Augmented Generation (RAG)**
- **Why**: Combines LLM's reasoning with external knowledge to prevent hallucinations
- **How**: 
  - Retrieval: Find relevant documents via semantic similarity
  - Augmentation: Embed documents into LLM prompt as context
  - Generation: LLM generates answer based only on provided context
- **Benefit**: Answers are grounded in actual data; no fabrication

### 2. **Role-Based Access Control (RBAC)**
- **Why**: Enforce fine-grained security at the data level
- **How**:
  - Users mapped to roles in `user_role_mapping.json`
  - Each role has allowed departments (metadata tags)
  - Filters applied **before** LLM sees documents
  - Unauthorized chunks never enter pipeline
- **Benefit**: Multi-tenant safety; compliance-ready (HIPAA, SOX, GDPR)

### 3. **Vector Embeddings & Semantic Search**
- **Model**: Gemini Embedding 001 (768 dimensions)
- **Why**: Convert text to mathematical vectors to capture semantic meaning
- **How**: "Employee leave policy" and "annual vacation" map to similar vectors
- **Benefit**: Semantic matching > keyword matching (better UX)

### 4. **Metadata-Driven Filtering**
- **Architecture**: Every chunk carries metadata: `{source, department, role, classification}`
- **Retrieval**: Apply RBAC filter to retrieved chunks
- **Benefit**: Decouples security from vector search; enables role-specific results

### 5. **Singleton Pattern (Connection Pooling)**
```python
_embeddings = None
_vectorstore = None
_llm = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(...)
    return _embeddings
```
- **Why**: Avoid recreating expensive API connections on every query
- **Benefit**: Performance optimization; reduced API calls

### 6. **Batching & Rate-Limit Handling**
- **Issue**: Gemini API has strict rate limits (429 errors)
- **Solution**: 
  - Batch embeddings: 10 chunks per request
  - Sleep 65 seconds between batches
  - Exponential backoff on retries
- **Benefit**: Stable ingestion; prevents quota exhaustion

### 7. **Prompt Engineering**
- **Technique**: System prompt instructs LLM to:
  - Answer ONLY from context
  - Admit when information is missing
  - Use structured format (bullet points)
  - Cite sources
- **Benefit**: Consistent, safe, professional responses

### 8. **Dataclass for Result Encapsulation**
```python
@dataclass
class RAGResult:
    answer: str
    sources: List[str]
    retrieved_chunks: List[Document]
    confidence: float
    latency_seconds: float
    access_granted: bool
```
- **Why**: Type-safe result container with structured schema
- **Benefit**: Clear interface; easy debugging; IDE autocomplete

### 9. **Document Chunking with Overlap**
- **Chunk size**: 500 chars (fits LLM context windows)
- **Overlap**: 50 chars (preserve context at boundaries)
- **Splitter**: Recursive (tries paragraphs first, then sentences, then words)
- **Benefit**: Semantic coherence; prevents information loss at boundaries

### 10. **Confidence Scoring**
```python
base = min(len(docs) / 5, 1.0) * 0.7  # More docs = higher confidence
bonus = 0.2 if len(answer) > 100 else 0.1  # Longer answer = more thorough
confidence = min(base + bonus, 1.0)
```
- **Why**: Quantify result quality for user awareness
- **Benefit**: Transparency; helps users assess trustworthiness

### 11. **Expander UI Pattern**
- Chunks viewer: Hidden by default, expandable on demand
- Access decision: Technical details behind expander
- **Benefit**: Clean UI; advanced info available without clutter

### 12. **Latency Measurement**
```python
start = time.time()
# ... execute RAG pipeline ...
latency_seconds = round(time.time() - start, 2)
```
- **Why**: Track performance; identify bottlenecks
- **Benefit**: Observability; SLA monitoring

### 13. **Multi-Format Loader Pattern**
- Separate loaders for PDF, CSV, JSON, Metadata
- Each implements consistent interface: `load_* → List[Document]`
- **Benefit**: Extensibility; easy to add new formats (XML, HTML, etc.)

### 14. **Fail-Safe Security Model**
- Default: **Deny** (if role not found, access denied)
- Default: **Deny all** (if no role permissions configured)
- **Benefit**: Security by default; no accidental oversharing

---

## 📊 Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Embedding Model** | Gemini 001 | 768 dimensions, semantic search |
| **Chunk Size** | 500 characters | Optimal for context window |
| **Chunk Overlap** | 50 characters | Preserve boundary context |
| **Top-K Retrieval** | 8 chunks | Balance relevance vs. context size |
| **Similarity Score Threshold** | < 1.2 | Post-filtering cutoff |
| **LLM Model** | Gemini 2.5 Flash | Fast, cost-effective |
| **LLM Temperature** | 0.2 | Deterministic, factual responses |
| **Max Output Tokens** | 1024 | Sufficient for most queries |
| **Embedding Batch Size** | 10 | Rate-limit safe for Gemini API |
| **Batch Sleep Duration** | 65 seconds | Avoid 429 rate-limit errors |
| **RBAC Role Levels** | 4 roles | Admin, HR, Finance, Security |
| **Vector Store** | FAISS CPU | Lightweight, serverless |
| **Metadata Fields** | 5+ | source, department, role, classification, document_type |

---

## 🔐 Security Architecture

### Defense in Depth

1. **Authentication**: User lookup in role mapping
   - Unknown users → Access denied (fail-safe)

2. **Authorization**: RBAC filters by department
   - Admin role: No restrictions
   - Other roles: Department-based filtering

3. **Data Isolation**: Chunks tagged with department metadata
   - Finance chunks tagged `department: "finance"`
   - HR chunks tagged `department: "hr"`
   - Security chunks tagged `department: "security"`

4. **Pre-LLM Filtering**: Unauthorized data never reaches AI model
   - Filter applied at retrieval stage
   - Impossible to leak restricted data via prompt injection

5. **Audit Trail**: All queries can be logged
   - User: Who asked?
   - Role: What was their access level?
   - Query: What did they ask?
   - Result: What was retrieved?

6. **Fail-Safe Defaults**: 
   - Unknown users: **Denied**
   - Unconfigured roles: **Denied**
   - No retrieved docs: "No authorized information found"

### GDPR/Compliance-Friendly

✅ **User → Role → Department mapping** is explicit and auditable
✅ **Can query audit logs**: "What data did Finance role access?"
✅ **Easy access revocation**: Remove from `user_role_mapping.json`
✅ **No data exposure**: Filters prevent unauthorized retrieval
✅ **Logging-ready**: All queries logged with access decisions

---

## 📁 Project Structure

```
rag-pipeline/
├── app.py                          # Streamlit UI
├── rag_pipeline.py                 # Core RAG pipeline
├── security.py                     # RBAC engine
├── ingest.py                       # Ingestion pipeline
├── loaders.py                      # Multi-format document loaders
├── prompts.py                      # LLM prompt templates
├── utils.py                        # Shared utilities
├── dataset_generator.py            # Synthetic data generator
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── README.md                       # This file
├── data/
│   ├── pdfs/                      # PDF documents
│   ├── csv/                       # CSV data files
│   ├── json_logs/                 # JSON log files
│   ├── metadata/                  # Metadata catalogs
│   ├── user_roles/                # User-role mappings
│   └── access_policies/           # RBAC policies
├── faiss_db/                       # Vector store (created by ingest.py)
│   └── index.faiss
└── .env                            # Configuration (create after setup)
```

---

## 🚀 Workflow Summary

### Setup Workflow
1. **Install**: Dependencies via pip
2. **Configure**: Add Gemini API key to `.env`
3. **Generate**: Synthetic data (PDFs, CSVs, JSON logs)
4. **Ingest**: Embed documents into FAISS vector store
5. **Launch**: Start Streamlit app

### Query Workflow
1. **User selects role** (dropdown)
2. **System validates access** (RBAC check)
3. **Retrieves authorized documents** (semantic search + RBAC filter)
4. **Generates answer** (LLM with retrieved context)
5. **Shows results** (answer + citations + confidence + metrics)

### Result Output
- ✅ Secure, traceable, grounded AI responses
- ✅ No hallucinations (answer constrained to retrieved context)
- ✅ Multi-tenant safe (RBAC enforced before LLM)
- ✅ Explainable (sources, confidence, latency visible)

---

## 🎓 Key Features

### For Users
- 🔐 **Secure login** with role-based access
- 🎯 **Smart search** using semantic similarity
- 📋 **Demo queries** tailored to your role
- 💡 **Confidence scores** for result quality
- ⚡ **Fast responses** with latency tracking
- 📖 **Source citations** for verification
- 🔍 **Expandable chunks** for transparency

### For Administrators
- 👥 **User-role mapping** in JSON (easy to manage)
- 🛡️ **RBAC policies** per department
- 📊 **Audit-ready** (all queries logged)
- 🔓 **Easy revocation** (update JSON files)
- 📈 **Observable** (latency, confidence, chunk counts)

### For Developers
- 🏗️ **Modular architecture** (loaders, RAG, security decoupled)
- 📚 **Multi-format support** (PDF, CSV, JSON, custom formats)
- 🔌 **LangChain integration** (easy to swap LLMs/embeddings)
- ⚡ **Rate-limit handling** (batching, backoff, retry logic)
- 💾 **Singleton pattern** (efficient API usage)
- 📐 **Type-safe** (dataclasses, type hints)

---

## 🐛 Troubleshooting

### "FAISS index not found"
```bash
# Run ingestion first
python ingest.py
```

### "Missing GOOGLE_API_KEY"
```bash
# Create and configure .env file
cp .env.example .env
# Edit .env and add your API key from https://aistudio.google.com/app/apikey
```

### "User not found"
- Check `data/user_roles/user_role_mapping.json`
- Ensure username exists in the mapping

### "Access Denied"
- Verify user's role in `data/user_roles/user_role_mapping.json`
- Check role permissions in `data/access_policies/access_policies.json`

### Rate-limit errors (429)
- Ingestion script already handles this with batching + sleep
- If still occurring, increase `SLEEP_BETWEEN_BATCHES` in `ingest.py`

---

## 📚 Technologies Used

- **LangChain** — LLM orchestration & document processing
- **Google Generative AI (Gemini)** — Embeddings & LLM
- **FAISS** — Vector similarity search
- **Streamlit** — Web UI framework
- **Python 3.9+** — Core language
- **fpdf2** — PDF generation (for synthetic data)
- **Pandas** — CSV handling

---

## 📝 License

This project is provided as-is for educational and enterprise use.

---

## 🤝 Contributing

Suggestions for improvement:
- Add more document formats (HTML, XML, Markdown)
- Implement persistent query logging (database)
- Add multi-language support
- Integrate with SSO/LDAP for authentication
- Add document version control
- Implement feedback loop for answer quality

---

**Built with ❤️ using LangChain, Gemini, and FAISS**
