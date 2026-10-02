# Groww - HDFC Mutual Fund FAQ Assistant

A facts-only RAG chatbot for the five HDFC Mutual Fund schemes defined in the project data. The frontend follows the attached dark FAQ/chat UI reference, while the backend exposes one clean `/api/ask` path for retrieval + generation.

## What was fixed

- Removed the disconnected Streamlit input pattern. The visible composer now sends the real request.
- Replaced the Streamlit-only UI with a lightweight FastAPI + vanilla HTML/CSS/JS app so the supplied UI can be implemented directly.
- Added persistent chat history in browser `localStorage`, new-chat, delete-chat, mobile sidebar, keyboard submit, loading state, and source links.
- Made paths independent of the working directory.
- Added configuration through `.env` without shipping the real secret.
- Added input validation and clearer server-side errors.
- Made Chroma ingestion idempotent and added safe chunking validation.

## Architecture

```text
Browser UI (static/index.html)
        |
        | POST /api/ask
        v
FastAPI (src/server.py)
        |
        v
RAG query pipeline (src/chatbot.py)
   |               |
   v               v
ChromaDB        Groq LLM
   ^
   |
Ingestion pipeline (src/ingest.py)
   ^
   |
data sources / SCHEMES
```

## Scope

The project data defines five covered schemes:

1. HDFC Large Cap Fund Direct Growth
2. HDFC Flexi Cap Direct Plan Growth
3. HDFC ELSS Tax Saver Fund Direct Plan Growth
4. HDFC Small Cap Fund Direct Growth
5. HDFC Balanced Advantage Fund Direct Growth

The source list is retained in `data/sources.csv`.

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Groq

```bash
cp .env.example .env
```

Add your real `GROQ_API_KEY` to `.env`. Do **not** commit `.env`.

### 4. Build the vector database

```bash
python src/ingest.py
```

This creates `chroma_db/` and refreshes `data/chunks.txt`.

### 5. Start the app

```bash
python run.py
```

Open `http://127.0.0.1:8000`.

API documentation is available at `http://127.0.0.1:8000/docs`.

## Important data note

The project documentation says the scheme data were extracted from public Groww pages as of 25 Sep 2026. These values are static project data, not live NAV/AUM data. The assistant therefore should not be treated as a real-time market-data system.

## Validation

From the project root:

```bash
python -m compileall src run.py
python -c "from src.ingest import SCHEMES, build_chunks; print('schemes:', len(SCHEMES)); print('chunks:', len(build_chunks(SCHEMES)))"
```

For the current dataset, the expected counts are 5 schemes and 20 chunks.

## Project structure

```text
Nextleap/
├── static/
│   └── index.html
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── chatbot.py
│   ├── ingest.py
│   └── server.py
├── data/
│   ├── sources.csv
│   ├── chunks.txt
│   └── sample_qa.md
├── PRD.md
├── architecture.md
├── implementation.md
├── requirements.txt
├── .env.example
├── .gitignore
└── run.py
```

# Nextleap


## Source List

The assistant uses the following public Groww pages as its source data:

1. **HDFC Large Cap Fund Direct Growth**  
   https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth

2. **HDFC Flexi Cap Direct Plan Growth**  
   https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth

3. **HDFC ELSS Tax Saver Fund Direct Plan Growth**  
   https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth

4. **HDFC Small Cap Fund Direct Growth**  
   https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth

5. **HDFC Balanced Advantage Fund Direct Growth**  
   https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth


## Disclaimer

This project is a demonstration FAQ assistant and provides facts from the project's stored source data. The information is static project data extracted from public Groww pages as of **25 September 2026** and is not live market or NAV/AUM data.

The assistant is intended for informational purposes only and does **not** provide personalized investment advice, recommendations, or guarantees of returns. Users should verify current information from official fund documents and consult a qualified financial professional before making investment decisions.


