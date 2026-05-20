"""
prompts.py
----------
LangChain prompt templates for RAG system (LangChain 0.2+ compatible)
"""

# ✅ FIX: modern LangChain import
from langchain_core.prompts import PromptTemplate


# ─────────────────────────────────────────────
# Main RAG Prompt
# ─────────────────────────────────────────────

RAG_PROMPT_TEMPLATE = """
You are an enterprise AI assistant.

You MUST answer ONLY using the provided context.

RULES:
- Do NOT hallucinate
- Do NOT invent departments
- If information is missing, say:
  "The retrieved documents do not contain that information."
- Summarize clearly
- Use bullet points when possible
- Mention sources when relevant

User Role:
{role}

Retrieved Context:
{context}

Question:
{question}

Answer:
"""

RAG_PROMPT = PromptTemplate(
    input_variables=["role", "context", "question"],
    template=RAG_PROMPT_TEMPLATE,
)


# ─────────────────────────────────────────────
# Access Denied Prompt
# ─────────────────────────────────────────────

ACCESS_DENIED_TEMPLATE = """You are a secure enterprise AI assistant.

The user is NOT authorized to access this information.

RULES:
- Do NOT answer the question.
- Do NOT reveal hidden or partial information.
- Politely deny access.

User Role: {role}
User Question: {question}

Response:
"""

ACCESS_DENIED_PROMPT = PromptTemplate(
    input_variables=["role", "question"],
    template=ACCESS_DENIED_TEMPLATE,
)


# ─────────────────────────────────────────────
# Summary Prompt
# ─────────────────────────────────────────────

SUMMARY_PROMPT_TEMPLATE = """You are an enterprise reporting assistant.

Summarize the documents below in a clear executive format.
Focus on insights, risks, and key metrics.

TEXT:
{context}

SUMMARY:
"""

SUMMARY_PROMPT = PromptTemplate(
    input_variables=["context"],
    template=SUMMARY_PROMPT_TEMPLATE,
)