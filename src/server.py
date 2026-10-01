"""FastAPI server for the HDFC Mutual Fund FAQ Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from .chatbot import answer_question
except ImportError:
    from chatbot import answer_question

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"

app = FastAPI(
    title="HDFC Mutual Fund FAQ Assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


class AskResponse(BaseModel):
    answer: str
    citation: Optional[str] = None
    citation_label: Optional[str] = None
    is_refusal: bool = False


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        result = answer_question(request.question)
        return AskResponse(
            answer=result["answer"],
            citation=result.get("citation"),
            citation_label=result.get("citation_label"),
            is_refusal=result.get("is_refusal", False),
        )
    except Exception as exc:
        import traceback
        print("API ERROR:", repr(exc), flush=True)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Assistant error: {type(exc).__name__}: {exc}",
        ) from exc
