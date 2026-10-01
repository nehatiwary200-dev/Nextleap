
"""RAG query pipeline for the HDFC Mutual Fund FAQ Assistant."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

import chromadb
from groq import Groq

try:
    from .config import CHROMA_PERSIST_DIR, GROQ_MODEL, TOP_K
except ImportError:
    from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, GROQ_MODEL, TOP_K


OPINION_KEYWORDS = [
    "should i buy",
    "should i sell",
    "should i invest",
    "is it good to",
    "is it bad to",
    "best fund",
    "worst fund",
    "top fund",
    "which fund should",
    "recommend",
    "suggestion",
    "advice",
    "portfolio",
    "allocate my",
    "how much should i",
    "will i get",
    "can i earn",
    "guaranteed return",
    "is best for",
    "is better",
    "should i choose",
    "which is best",
    "which is better",
    "what should i do",
    "is it worth",
    "better than",
    "better or",
    "worth buying",
    "worth investing",
    "good to buy",
    "good to invest",
    "bad to buy",
    "bad to invest",
]

REFUSAL_MESSAGE = (
    "I can provide factual information from the project's source pages, "
    "but I cannot give investment advice or recommendations."
)


def _normalise_url(url: str) -> str:
    """Convert markdown-style URLs into plain URLs."""
    if not url:
        return ""

    url = url.strip()

    match = re.fullmatch(r"\[(https://[^\]]+)\]\((https://[^)]+)\)", url)
    if match:
        return match.group(2)

    return url


@lru_cache(maxsize=1)
def get_collection():
    """Open the persisted Chroma collection without loading a local ML model."""

    if not CHROMA_PERSIST_DIR.exists():
        raise RuntimeError(
            "ChromaDB is not initialized. Run `python src/ingest.py` "
            "before starting the server."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))

    return client.get_collection(
        name="hdfc_mutual_funds"
    )

def is_opinionated(question: str) -> bool:
    """Return True when a question is explicitly advice-seeking."""

    normalized = " ".join(question.lower().split())

    return any(
        keyword in normalized
        for keyword in OPINION_KEYWORDS
    )


def _keyword_score(question: str, document: str) -> int:
    """Give a simple lexical relevance score to improve exact fact retrieval."""

    question_words = set(
        re.findall(r"[a-z0-9]+", question.lower())
    )

    document_words = set(
        re.findall(r"[a-z0-9]+", document.lower())
    )

    important_words = {
        word
        for word in question_words
        if len(word) >= 3
    }

    return len(important_words.intersection(document_words))


def retrieve_chunks(
    question: str,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """Retrieve stored FAQ chunks using lightweight keyword matching."""

    collection = get_collection()

    data = collection.get(
        include=["documents", "metadatas"]
    )

    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []

    if not documents:
        return []

    chunks: list[dict[str, Any]] = []

    for index, document in enumerate(documents):
        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        chunks.append(
            {
                "text": document,
                "metadata": metadata or {},
                "distance": None,
                "keyword_score": _keyword_score(
                    question,
                    document,
                ),
            }
        )

    chunks.sort(
        key=lambda chunk: chunk["keyword_score"],
        reverse=True,
    )

    return chunks[:max(1, min(top_k, len(chunks)))]

def build_prompt(
    question: str,
    chunks: list[dict[str, Any]],
) -> str:
    """Build a constrained prompt from retrieved context."""

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk["metadata"]

        source_url = _normalise_url(
            metadata.get("source_url", "")
        )

        context_parts.append(
            f"[Source {index}]\n"
            f"Scheme: {metadata.get('scheme_name', 'Unknown')}\n"
            f"Section: {metadata.get('section', 'Unknown')}\n"
            f"URL: {source_url}\n"
            f"Content: {chunk['text']}"
        )

    context = "\n\n".join(context_parts)

    return f"""You are a factual FAQ assistant for HDFC Mutual Fund schemes.

Answer the user's question ONLY using the supplied context.

Rules:
- Keep the answer to 3 sentences or fewer.
- Give factual information only.
- Do not give investment advice.
- Do not give recommendations.
- Do not give opinions.
- Do not invent missing facts.
- Do not use information from your general knowledge.
- Do not include URLs in the answer body.
- Do not include unnecessary dates.
- If the exact answer is present in the context, answer it directly.
- If the context does not contain the answer, say exactly:
I don't have that information in my sources.
- Do not compare funds unless the user is explicitly asking for factual attributes.

Important:
Use the source content even when the user's wording is different from the wording in the source.

Context:
{context}

User question:
{question}

Answer:"""


def _groq_client() -> Groq:
    """Create the Groq client."""

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. "
            "Copy `.env.example` to `.env` and add your key."
        )

    return Groq(api_key=api_key)


def answer_question(question: str) -> dict[str, Any]:
    """Answer a user question using RAG."""

    clean_question = question.strip()

    if not clean_question:
        return {
            "answer": (
                "Please enter a question about the "
                "HDFC mutual fund schemes."
            ),
            "citation": None,
            "citation_label": None,
            "is_refusal": False,
            "retrieved_chunks": [],
        }

    if is_opinionated(clean_question):
        return {
            "answer": REFUSAL_MESSAGE,
            "citation": None,
            "citation_label": None,
            "is_refusal": True,
            "retrieved_chunks": [],
        }

    chunks = retrieve_chunks(clean_question)

    if not chunks:
        return {
            "answer": (
                "I don't have that information in my sources."
            ),
            "citation": None,
            "citation_label": None,
            "is_refusal": False,
            "retrieved_chunks": [],
        }

    prompt = build_prompt(
        clean_question,
        chunks,
    )

    client = _groq_client()

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.1,
        max_tokens=240,
    )

    answer_text = (
        response.choices[0].message.content or ""
    ).strip()

    if not answer_text:
        answer_text = (
            "I don't have that information in my sources."
        )

    source_metadata = chunks[0]["metadata"]

    source_url = _normalise_url(
        source_metadata.get("source_url", "")
    )

    source_name = source_metadata.get(
        "scheme_name"
    )

    return {
        "answer": answer_text,
        "citation": source_url,
        "citation_label": source_name or "Source",
        "is_refusal": False,
        "retrieved_chunks": chunks,
    }


