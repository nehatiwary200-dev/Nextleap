"""RAG ingestion pipeline for the HDFC Mutual Fund FAQ Assistant."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import chromadb
from chromadb.utils import embedding_functions

try:
    from .config import CHROMA_PERSIST_DIR, CHUNKS_TXT_PATH, EMBEDDING_MODEL
except ImportError:
    from config import CHROMA_PERSIST_DIR, CHUNKS_TXT_PATH, EMBEDDING_MODEL

CHUNK_SIZE = 200
CHUNK_OVERLAP = 30
COLLECTION_NAME = "hdfc_mutual_funds"

SCHEMES = [
    {
        "scheme_name": "HDFC Large Cap Fund Direct Growth",
        "category": "Equity - Large Cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "risk_level": "Very High",
        "nav": "₹1,189.08 (25 Sep 2026)",
        "aum": "₹39,933.37 Cr",
        "expense_ratio": "1.03%",
        "rating": "4",
        "min_sip": "₹100",
        "min_lumpsum": "₹100",
        "exit_load": "1% if redeemed within 1 year",
        "stamp_duty": "0.005% (from July 1, 2020)",
        "tax_implication": "If redeemed within one year, returns are taxed at 20%. If redeemed after one year, returns exceeding ₹1.25 lakh in a financial year are taxed at 12.5%.",
        "benchmark": "NIFTY 100 Total Return Index",
        "investment_objective": "The scheme seeks to provide long-term capital appreciation/income by investing predominantly in Large-Cap companies.",
        "sid_link": "https://www.hdfcfund.com",
        "fund_managers": [
            {"name": "Rahul Baijal", "tenure": "Jul 2022 - Present", "education": "PGDM(MBA) from IIM Calcutta, Engineering graduate from Delhi College of Engineering"},
            {"name": "Dhruv Muchhal", "tenure": "Jun 2023 - Present", "education": "B.Com, CA, CFA"},
        ],
    },
    {
        "scheme_name": "HDFC Flexi Cap Direct Plan Growth",
        "category": "Equity - Flexi Cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "risk_level": "Very High",
        "nav": "₹2,214.57 (25 Sep 2026)",
        "aum": "₹1,13,606.47 Cr",
        "expense_ratio": "0.77%",
        "rating": "5",
        "min_sip": "₹100",
        "min_lumpsum": "₹100",
        "exit_load": "1% if redeemed within 1 year",
        "stamp_duty": "0.005% (from July 1, 2020)",
        "tax_implication": "If redeemed within one year, returns are taxed at 20%. If redeemed after one year, returns exceeding ₹1.25 lakh in a financial year are taxed at 12.5%.",
        "benchmark": "NIFTY 500 Total Return Index",
        "investment_objective": "The scheme seeks to generate capital appreciation / income from a portfolio, predominantly invested in equity & equity related instruments.",
        "sid_link": "https://www.hdfcfund.com",
        "fund_managers": [
            {"name": "Dhruv Muchhal", "tenure": "Jun 2023 - Present", "education": "B.Com, CA, CFA"},
            {"name": "Amit Ganatra", "tenure": "Feb 2026 - Present", "education": "Commerce degree, Chartered Accountant, CFA from AIMR"},
        ],
    },
    {
        "scheme_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        "category": "Equity - ELSS",
        "source_url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "risk_level": "Very High",
        "nav": "₹1,447.38 (25 Sep 2026)",
        "aum": "₹15,991.78 Cr",
        "expense_ratio": "1.21%",
        "rating": "5",
        "min_sip": "₹500",
        "min_lumpsum": "₹500",
        "exit_load": "Nil",
        "stamp_duty": "0.005% (from July 1, 2020)",
        "tax_implication": "If redeemed within one year, returns are taxed at 20%. If redeemed after one year, returns exceeding ₹1.25 lakh in a financial year are taxed at 12.5%.",
        "benchmark": "NIFTY 500 Total Return Index",
        "investment_objective": "The scheme seeks to generate capital appreciation / income from a portfolio, comprising predominantly of equity & equity related instruments.",
        "sid_link": "https://www.hdfcfund.com",
        "lock_in": "3 years (ELSS mandatory lock-in)",
        "fund_managers": [
            {"name": "Amar Kalkundrikar", "tenure": "Dec 2025 - Present", "education": "B.Com, CA, CFA, MBA from Columbia Business School"},
            {"name": "Dhruv Muchhal", "tenure": "Jun 2023 - Present", "education": "B.Com, CA, CFA"},
        ],
    },
    {
        "scheme_name": "HDFC Small Cap Fund Direct Growth",
        "category": "Equity - Small Cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "risk_level": "Very High",
        "nav": "₹159.82 (25 Sep 2026)",
        "aum": "₹41,890.86 Cr",
        "expense_ratio": "0.78%",
        "rating": "3",
        "min_sip": "₹100",
        "min_lumpsum": "₹100",
        "exit_load": "1% if redeemed within 1 year",
        "stamp_duty": "0.005% (from July 1, 2020)",
        "tax_implication": "If redeemed within one year, returns are taxed at 20%. If redeemed after one year, returns exceeding ₹1.25 lakh in a financial year are taxed at 12.5%.",
        "benchmark": "BSE 250 SmallCap Total Return Index",
        "investment_objective": "The scheme seeks to provide long-term capital appreciation / income by investing predominantly in Small-Cap companies.",
        "sid_link": "https://www.hdfcfund.com",
        "fund_managers": [
            {"name": "Dhruv Muchhal", "tenure": "Jun 2023 - Present", "education": "B.Com, CA, CFA"},
            {"name": "Chirag Setalvad", "tenure": "Jun 2014 - Present", "education": "B.Sc, MBA from University of North Carolina"},
        ],
    },
    {
        "scheme_name": "HDFC Balanced Advantage Fund Direct Growth",
        "category": "Hybrid - Dynamic Asset Allocation",
        "source_url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
        "risk_level": "Very High",
        "nav": "₹557.73 (25 Sep 2026)",
        "aum": "₹1,07,295.79 Cr",
        "expense_ratio": "0.78%",
        "rating": "5",
        "min_sip": "₹100",
        "min_lumpsum": "₹100",
        "exit_load": "1% for units in excess of 15% of the investment if redeemed within 1 year",
        "stamp_duty": "0.005% (from July 1, 2020)",
        "tax_implication": "If redeemed within one year, returns are taxed at 20%. If redeemed after one year, returns exceeding ₹1.25 lakh in a financial year are taxed at 12.5%.",
        "benchmark": "NIFTY 500 Total Return Index",
        "investment_objective": "The scheme seeks to generate capital appreciation / income from a portfolio, comprising predominantly of equity & equity related instruments with dynamic asset allocation between equity and debt.",
        "sid_link": "https://www.hdfcfund.com",
        "fund_managers": [
            {"name": "Anil Bamboli", "tenure": "Jul 2022 - Present", "education": "CFA from AIMR, Masters in Management Studies (Finance), Graduate in Cost and Works Accountant from ICWAI"},
            {"name": "Arun Agarwal", "tenure": "Oct 2022 - Present", "education": "B.Com, Chartered Accountant"},
            {"name": "Dhruv Muchhal", "tenure": "Jun 2023 - Present", "education": "B.Com, CA, CFA"},
        ],
    },
]


def scheme_to_sections(scheme: dict) -> list[tuple[str, str]]:
    """Split a scheme into four named sections."""
    overview = (
        f"{scheme['scheme_name']} is a {scheme['category']} mutual fund scheme. "
        f"Risk level: {scheme['risk_level']}. NAV: {scheme['nav']}. "
        f"Fund size (AUM): {scheme['aum']}. Expense ratio: {scheme['expense_ratio']}. "
        f"Rating: {scheme['rating']}. Minimum SIP: {scheme['min_sip']}. "
        f"Minimum Lumpsum: {scheme['min_lumpsum']}."
    )
    exit_tax = (
        f"Exit load for {scheme['scheme_name']}: {scheme['exit_load']}. "
        f"Stamp duty on investment: {scheme['stamp_duty']}. "
        f"Tax implication: {scheme['tax_implication']}"
    )
    fund_management = " ".join(
        f"{manager['name']} ({manager['tenure']}). Education: {manager['education']}."
        for manager in scheme["fund_managers"]
    )
    fund_management = f"Fund managers of {scheme['scheme_name']}: {fund_management}"
    about = (
        f"About {scheme['scheme_name']}: {scheme['investment_objective']} "
        f"Benchmark: {scheme['benchmark']}. Scheme Information Document (SID): {scheme['sid_link']}."
    )
    if scheme.get("lock_in"):
        about += f" Lock-in period: {scheme['lock_in']}."

    return [
        ("Overview", overview),
        ("Exit Load & Tax", exit_tax),
        ("Fund Management", fund_management),
        ("About", about),
    ]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chunk text using a word-based sliding window."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks


def build_chunks(schemes: list[dict]) -> list[dict]:
    """Generate chunks with stable sequential IDs and source metadata."""
    all_chunks: list[dict] = []
    chunk_id = 0
    for scheme in schemes:
        for section_name, section_text in scheme_to_sections(scheme):
            for text_chunk in chunk_text(section_text):
                all_chunks.append({
                    "chunk_id": f"chunk_{chunk_id:04d}",
                    "scheme_name": scheme["scheme_name"],
                    "category": scheme["category"],
                    "section": section_name,
                    "source_url": scheme["source_url"],
                    "text": text_chunk,
                })
                chunk_id += 1
    return all_chunks


def save_chunks_to_txt(chunks: list[dict], filepath: Union[Path, str]) -> None:
    """Save chunks in a human-readable format."""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with output_path.open("w", encoding="utf-8") as file:
        file.write("=" * 80 + "\n")
        file.write("HDFC MUTUAL FUND FAQ - CHUNKED DATA\n")
        file.write(f"Generated: {timestamp}\n")
        file.write(f"Total chunks: {len(chunks)}\n")
        file.write(f"Chunk size: {CHUNK_SIZE} words, Overlap: {CHUNK_OVERLAP} words\n")
        file.write("=" * 80 + "\n\n")
        for chunk in chunks:
            file.write(f"[{chunk['chunk_id']}] {chunk['scheme_name']} | {chunk['section']}\n")
            file.write(f"Source: {chunk['source_url']}\n")
            file.write(f"Text: {chunk['text']}\n")
            file.write("-" * 80 + "\n\n")


def embed_and_store(chunks: list[dict], reset: bool = False):
    """Create/update the Chroma collection. Rebuild only when requested."""
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    existing_ids = set(collection.get(include=[]).get("ids", []))
    new_chunks = [chunk for chunk in chunks if chunk["chunk_id"] not in existing_ids]

    if new_chunks:
        collection.add(
            ids=[chunk["chunk_id"] for chunk in new_chunks],
            documents=[chunk["text"] for chunk in new_chunks],
            metadatas=[
                {
                    "scheme_name": chunk["scheme_name"],
                    "category": chunk["category"],
                    "section": chunk["section"],
                    "source_url": chunk["source_url"],
                }
                for chunk in new_chunks
            ],
        )
        print(f"Added {len(new_chunks)} new chunks to ChromaDB.")
    else:
        print(f"Collection already has {collection.count()} current chunks. Nothing to add.")

    return collection


def main() -> None:
    print("=" * 60)
    print("HDFC Mutual Fund FAQ - RAG Ingestion Pipeline")
    print("=" * 60)

    chunks = build_chunks(SCHEMES)
    print(f"[1/3] Built {len(chunks)} chunks from {len(SCHEMES)} schemes")

    save_chunks_to_txt(chunks, CHUNKS_TXT_PATH)
    print(f"[2/3] Saved chunks to {CHUNKS_TXT_PATH}")

    collection = embed_and_store(chunks)
    print(f"[3/3] Collection contains {collection.count()} documents")

    print("\nIngestion complete. Start the app with: python run.py")


if __name__ == "__main__":
    main()
