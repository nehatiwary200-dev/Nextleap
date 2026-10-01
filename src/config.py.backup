"""Application configuration and project paths."""

from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"
CHUNKS_TXT_PATH = DATA_DIR / "chunks.txt"
SOURCES_CSV_PATH = DATA_DIR / "sources.csv"

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
TOP_K = int(os.getenv("TOP_K", "5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
