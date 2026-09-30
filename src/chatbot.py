"""RAG query pipeline for the HDFC Mutual Fund FAQ Assistant."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.utils import embedding_functions
from groq import Groq

try:
    from .config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, GROQ_MODEL, TOP_K
except ImportError:  # Allows `python src/chatbot.py` style imports.
    from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, GROQ_MODEL, TOP_K


OPINION_KEYWORDS = [
    "should i buy", "should i sell", "should i invest", "is it good to",
    "is it bad to", "best fund", "worst fund", "top fund", "which fund should",
    "recommend", "suggestion", "advice", "portfolio", "allocate my",
    "how much should i", "will i get", "can i earn", "guaranteed return",
    "is best for", "is better", "should i choose", "which is best",
    "which is better", "what should i do", "is it worth", "better than",
    "better or", "worth buying", "worth investing", "good to buy",
    "good to invest", "bad to buy", "bad to invest",
]

REFUSAL_MESSAGE = (
    "I can provide factual information from the project's source pages, "
    "but I cannot give investment advice or recommendations."
)


@lru_cache(maxsize=1)
def get_collection():
    """Open the persisted Chroma collection lazily, once per process."""
    if not CHROMA_PERSIST_DIR.exists():
        raise RuntimeError(
            "ChromaDB is not initialized. Run `python src/ingest.py` before starting the server."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client.get_or_create_collection(
        name="hdfc_mutual_funds",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def is_opinionated(question: str) -> bool:
    """Return True when a question is explicitly advice-seeking."""
    normalized = " ".join(question.lower().split())
    return any(keyword in normalized for keyword in OPINION_KEYWORDS)


def retrieve_chunks(question: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    """Retrieve the most relevant chunks from ChromaDB."""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    requested_k = max(1, min(top_k, count))
    results = collection.query(query_texts=[question], n_results=requested_k)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: list[dict[str, Any]] = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        chunks.append({
            "text": document,
            "metadata": metadata,
            "distance": distance,
        })
    return chunks


def build_prompt(question: str, chunks: list[dict[str, Any]]) -> str:
    """Build a constrained prompt from retrieved context."""
    context_parts = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]
        context_parts.append(
            f"[Source {index}]\n"
            f"Scheme: {metadata.get('scheme_name', 'Unknown')}\n"
            f"Section: {metadata.get('section', 'Unknown')}\n"
            f"URL: {metadata.get('source_url', '')}\n"
            f"Content: {chunk['text']}"
        )

    context = "\n\n".join(context_parts)
    return f"""You are a factual FAQ assistant for HDFC Mutual Fund schemes.
Answer only from the supplied context.

Rules:
- Keep the answer to 3 sentences or fewer.
- Do not give investment advice, recommendations, or opinions.
- Do not invent missing facts.
- Do not include URLs in the answer body; the application adds the source link separately.
- Do not include dates unless they are needed to answer the user's question.
- If the context does not contain the answer, say exactly: I don't have that information in my sources.
- Do not compare funds unless the question is purely asking for factual attributes.

Context:
{context}

User question: {question}

Answer:"""


def _groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Copy `.env.example` to `.env` and add your key."
        )
    return Groq(api_key=api_key)


def answer_question(question: str) -> dict[str, Any]:
    """Answer a user question with RAG and return the selected source URL."""
    clean_question = question.strip()
    if not clean_question:
        return {
            "answer": "Please enter a question about the HDFC mutual fund schemes.",
            "citation": None,
            "is_refusal": False,
        }

    if is_opinionated(clean_question):
        return {
            "answer": REFUSAL_MESSAGE,
            "citation": None,
            "is_refusal": True,
        }

    chunks = retrieve_chunks(clean_question)
    if not chunks:
        return {
            "answer": "I don't have that information in my sources. Please try rephrasing your question about the covered HDFC schemes.",
            "citation": None,
            "is_refusal": False,
            "retrieved_chunks": [],
        }

    prompt = build_prompt(clean_question, chunks)
    client = _groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=240,
    )

    answer_text = (response.choices[0].message.content or "").strip()
    if not answer_text:
        answer_text = "I don't have that information in my sources."

    source_url = chunks[0]["metadata"].get("source_url")
    source_name = chunks[0]["metadata"].get("scheme_name")

    return {
        "answer": answer_text,
        "citation": source_url,
        "citation_label": source_name or "Source",
        "is_refusal": False,
        "retrieved_chunks": chunks,
    }
