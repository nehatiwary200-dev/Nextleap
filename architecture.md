# Architecture: HDFC Mutual Fund FAQ Assistant — RAG Chatbot

| Field | Value |
|-------|-------|
| **Document Type** | Technical Architecture Document |
| **Derived From** | `PRD.md` |
| **Date** | 28 Sep 2026 |
| **Status** | Prototype — Class Demo |

---

## 1. System Overview

The system is a **Retrieval-Augmented Generation (RAG) chatbot** that answers factual questions about HDFC mutual fund schemes. It follows a two-phase architecture:

1. **Ingestion Pipeline** (one-time): Load → Chunk → Embed → Store in ChromaDB
2. **Query Pipeline** (per-question): Embed → Retrieve → LLM → Answer + Citation

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                           │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │  Load    │──▶│  Chunk   │──▶│  Embed   │──▶│  ChromaDB        │ │
│  │ 5 Pages  │   │ 4 Sect/  │   │ MiniLM   │   │ (persisted)      │ │
│  │ (Groww)  │   │ scheme   │   │ 384-dim  │   │ chroma_db/       │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────────┘ │
│        │              │              │                   │          │
│        ▼              ▼              ▼                   ▼          │
│   data/sources   data/chunks   sentence-transformers  chroma.sqlite3│
│   .csv           .txt          all-MiniLM-L6-v2                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         QUERY PIPELINE                              │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │ Question │──▶│  Embed   │──▶│ Retrieve │──▶│  Groq LLM        │ │
│  │ (user)   │   │ MiniLM   │   │ Top-3    │   │  llama-3.3-70b   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────────┘ │
│        │              │              │                   │          │
│        ▼              ▼              ▼                   ▼          │
│   Streamlit UI   384-dim vector   Cosine sim      Answer + Citation │
│   text_input     (same model)     top_k=3          ≤3 sentences     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          STREAMLIT UI                               │
│                                                                     │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────────────┐  │
│  │Welcome │ │ Examples │ │ Input  │ │ Answer │ │ Citation +     │  │
│  │ Line   │ │ (3 btns) │ │ Field  │ │ + Date │ │ Disclaimer     │  │
│  └────────┘ └──────────┘ └────────┘ └────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER                                      │
│                    (Retail investor / Support / Demo)                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP (localhost:8501)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP                                │
│                          src/app.py                                 │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  Session State  │  │  Example Btns   │  │  Disclaimer Banner  │ │
│  │  (question)     │  │  (3 presets)    │  │  (facts-only)       │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────┘ │
│           │                    │                                    │
│           └────────┬───────────┘                                    │
│                    ▼                                                │
│           ┌─────────────────┐                                       │
│           │  answer_question│                                       │
│           │  (chatbot.py)   │                                       │
│           └────────┬────────┘                                       │
└────────────────────┼────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ Opinion Guard│ │ Retrieve │ │  Groq LLM    │
│ (keywords)   │ │ Top-3    │ │  (llama-3.3) │
│              │ │ chunks   │ │              │
└──────┬───────┘ └────┬─────┘ └──────┬───────┘
       │              │              │
       │              ▼              │
       │       ┌──────────────┐      │
       │       │  ChromaDB    │      │
       │       │  (persisted) │      │
       │       │  20 chunks   │      │
       │       └──────────────┘      │
       │                             │
       ▼                             ▼
┌──────────────┐            ┌──────────────┐
│ AMFI Refusal │            │ Answer +     │
│ Link         │            │ Citation     │
└──────────────┘            └──────────────┘
```

---

## 3. Data Flow

### 3.1 Ingestion Flow (One-Time)

```
Step 1: LOAD
─────────────────────────────────────────────────────────
Input:  5 Groww URLs (data/sources.csv)
Method: webfetch / requests + BeautifulSoup
Output: Raw HTML → structured fields per scheme

Extracted fields per scheme:
  - scheme_name, category, risk_level
  - nav, aum, expense_ratio, rating
  - min_sip, min_lumpsum
  - exit_load, stamp_duty, tax_implication
  - benchmark, investment_objective
  - fund_managers (name, tenure, education)
  - sid_link, lock_in (if ELSS)

Step 2: CHUNK
─────────────────────────────────────────────────────────
Input:  5 scheme objects
Method: Section-aware splitting
Output: 20 chunks (5 schemes × 4 sections)

Sections per scheme:
  ┌─────────────────────────────────────────────────────┐
  │ 1. Overview        → NAV, AUM, expense ratio, etc.  │
  │ 2. Exit Load & Tax → exit load, stamp duty, tax     │
  │ 3. Fund Management → managers, tenure, education    │
  │ 4. About           → objective, benchmark, SID      │
  └─────────────────────────────────────────────────────┘

Chunking parameters:
  - chunk_size: 200 tokens
  - overlap: 30 tokens
  - splitter: word-based sliding window

Step 3: EMBED
─────────────────────────────────────────────────────────
Input:  20 text chunks
Model:  sentence-transformers/all-MiniLM-L6-v2
Output: 20 vectors (384 dimensions each)

Properties:
  - Local execution (no API key)
  - ~110 MB model download (first run)
  - CPU-friendly

Step 4: STORE
─────────────────────────────────────────────────────────
Input:  20 chunks + 20 vectors + metadata
Store:  ChromaDB (chroma_db/)
Table:  collection "hdfc_mutual_funds"

Schema:
  ┌─────────────┬──────────────────────────────────────┐
  │ Column      │ Type                                 │
  ├─────────────┼──────────────────────────────────────┤
  │ id          │ TEXT (chunk_0000 ... chunk_0019)    │
  │ embedding   │ FLOAT[384]                           │
  │ document    │ TEXT (chunk content)                 │
  │ metadata    │ JSON {scheme_name, category,         │
  │             │   section, source_url}               │
  └─────────────┴──────────────────────────────────────┘

Also saved: data/chunks.txt (human-readable)
```

### 3.2 Query Flow (Per Question)

```
Step 1: OPINION GUARD
─────────────────────────────────────────────────────────
Input:  User question (string)
Method: Keyword matching against OPINION_KEYWORDS list
Output: Boolean (is_opinionated)

If True → Return refusal message + AMFI link
If False → Continue to Step 2

Step 2: EMBED QUESTION
─────────────────────────────────────────────────────────
Input:  User question (string)
Model:  sentence-transformers/all-MiniLM-L6-v2
Output: 1 vector (384 dimensions)

Note: Same model as ingestion → same vector space

Step 3: RETRIEVE
─────────────────────────────────────────────────────────
Input:  Question vector (384-dim)
Method: Cosine similarity search in ChromaDB
Output: Top-3 chunks (n_results=3)

Retrieved chunk structure:
  {
    "text": "chunk content...",
    "metadata": {
      "scheme_name": "HDFC Large Cap Fund Direct Growth",
      "category": "Equity - Large Cap",
      "section": "Overview",
      "source_url": "https://groww.in/mutual-funds/..."
    },
    "distance": 0.234  // cosine distance (lower = more similar)
  }

Step 4: BUILD PROMPT
─────────────────────────────────────────────────────────
Input:  Question + Top-3 chunks
Method: Template-based prompt construction
Output: Formatted prompt string

Prompt structure:
  ┌─────────────────────────────────────────────────────┐
  │ SYSTEM: You are a factual FAQ assistant...         │
  │ RULES: ≤3 sentences, one citation, no advice       │
  │ CONTEXT:                                            │
  │   [Source 1] Scheme: ... | Section: ... | URL: ...  │
  │   [Source 2] Scheme: ... | Section: ... | URL: ...  │
  │   [Source 3] Scheme: ... | Section: ... | URL: ...  │
  │ USER QUESTION: {question}                           │
  │ ANSWER:                                             │
  └─────────────────────────────────────────────────────┘

Step 5: LLM GENERATION
─────────────────────────────────────────────────────────
Input:  Formatted prompt
Model:  Groq API — llama-3.3-70b-versatile
Params: temperature=0.1, max_tokens=300
Output: Generated answer text

Step 6: POST-PROCESS
─────────────────────────────────────────────────────────
Input:  Generated answer
Method: Append "Last updated from sources: {date}"
Output: Final answer + citation URL

Return:
  {
    "answer": "The expense ratio is 1.03%...\n\n*Last updated from sources: 2026-09-28*",
    "citation": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "is_refusal": false,
    "retrieved_chunks": [...]  // for debugging
  }
```

---

## 4. Module Architecture

### 4.1 Project Structure

```
/Users/nehatiwary/Documents/Nextleap/
│
├── src/
│   ├── ingest.py              # Ingestion pipeline (Load → Chunk → Embed → Store)
│   │   ├── SCHEMES[]          #   Structured data for 5 HDFC schemes
│   │   ├── scheme_to_sections()  # Split scheme into 4 sections
│   │   ├── chunk_text()       #   Sliding window chunker (200 tok, 30 overlap)
│   │   ├── build_chunks()     #   Generate all chunks with metadata
│   │   ├── save_chunks_to_txt()  # Human-readable output
│   │   ├── embed_and_store()  #   Embed + persist to ChromaDB
│   │   └── main()             #   CLI entry point
│   │
│   ├── chatbot.py             # Query pipeline (Embed → Retrieve → LLM → Answer)
│   │   ├── OPINION_KEYWORDS   #   Advice-seeking keyword list
│   │   ├── is_opinionated()   #   Opinion guard
│   │   ├── get_collection()   #   Load ChromaDB collection
│   │   ├── retrieve_chunks()  #   Top-3 cosine similarity search
│   │   ├── build_prompt()     #   Prompt template
│   │   └── answer_question()  #   End-to-end query handler
│   │
│   └── app.py                 # Streamlit UI
│       ├── Page config        #   Title, icon, layout
│       ├── CSS styles         #   Custom styling
│       ├── Example buttons    #   3 preset questions
│       ├── Text input         #   User question field
│       └── Answer display     #   Answer + citation + disclaimer
│
├── data/
│   ├── sources.csv            # 5 source URLs
│   ├── chunks.txt             # 20 human-readable chunks
│   └── sample_qa.md           # 10 sample Q&A pairs
│
├── chroma_db/                 # ChromaDB persistent storage
│   ├── chroma.sqlite3         #   SQLite backend
│   └── {uuid}/                #   Collection data
│
├── requirements.txt           # Python dependencies
├── .env                       # Groq API key (git-ignored)
├── .env.example               # Template for .env
├── .gitignore                 # Excludes .env, chroma_db/, __pycache__
├── PRD.md                     # Product Requirements Document
├── architecture.md            # This document
└── README.md                  # Setup and usage instructions
```

### 4.2 Data Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SCHEME (per mutual fund)                     │
├─────────────────────────────────────────────────────────────────────┤
│ scheme_name:        TEXT                                            │
│ category:           TEXT (e.g., "Equity - Large Cap")               │
│ source_url:         TEXT (Groww page URL)                           │
│ risk_level:         TEXT (e.g., "Very High")                        │
│ nav:                TEXT (e.g., "₹1,189.08 (25 Sep 2026)")          │
│ aum:                TEXT (e.g., "₹39,933.37 Cr")                    │
│ expense_ratio:      TEXT (e.g., "1.03%")                            │
│ rating:             TEXT (e.g., "4")                                │
│ min_sip:            TEXT (e.g., "₹100")                             │
│ min_lumpsum:        TEXT (e.g., "₹100")                             │
│ exit_load:          TEXT (e.g., "1% if redeemed within 1 year")     │
│ stamp_duty:        TEXT (e.g., "0.005% (from July 1, 2020)")      │
│ tax_implication:    TEXT                                            │
│ benchmark:          TEXT (e.g., "NIFTY 100 Total Return Index")     │
│ investment_objective: TEXT                                          │
│ sid_link:           TEXT (e.g., "https://www.hdfcfund.com")         │
│ lock_in:            TEXT (optional, e.g., "3 years")                │
│ fund_managers:      LIST[OBJECT]                                    │
│   └─ {name, tenure, education}                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ scheme_to_sections()
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SECTION (4 per scheme)                       │
├─────────────────────────────────────────────────────────────────────┤
│ section_name:       TEXT (Overview | Exit Load & Tax |              │
│                     Fund Management | About)                        │
│ text:               TEXT (combined factual sentences)              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ chunk_text()
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CHUNK (20 total)                             │
├─────────────────────────────────────────────────────────────────────┤
│ chunk_id:           TEXT (chunk_0000 ... chunk_0019)               │
│ scheme_name:        TEXT                                            │
│ category:           TEXT                                            │
│ section:            TEXT                                            │
│ source_url:         TEXT                                            │
│ text:               TEXT (≤200 tokens)                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ embed_and_store()
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CHROMADB RECORD                               │
├─────────────────────────────────────────────────────────────────────┤
│ id:                 TEXT (chunk_id)                                 │
│ embedding:          FLOAT[384]                                      │
│ document:           TEXT (chunk text)                               │
│ metadata:           JSON {scheme_name, category, section,          │
│                              source_url}                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. API Design

### 5.1 Internal Python API

#### `src/ingest.py`

```python
def scheme_to_sections(scheme: dict) -> list[tuple[str, str]]:
    """Split a scheme dict into 4 named sections."""
    # Returns: [("Overview", "..."), ("Exit Load & Tax", "..."), ...]

def chunk_text(text: str, chunk_size: int = 200, overlap: int = 30) -> list[str]:
    """Sliding window chunker (word-based)."""
    # Returns: ["chunk text 1", "chunk text 2", ...]

def build_chunks(schemes: list[dict]) -> list[dict]:
    """Generate all chunks with metadata."""
    # Returns: [{chunk_id, scheme_name, category, section, source_url, text}, ...]

def save_chunks_to_txt(chunks: list[dict], filepath: str) -> None:
    """Save chunks to human-readable text file."""

def embed_and_store(chunks: list[dict]) -> chromadb.Collection:
    """Embed chunks and persist to ChromaDB. Skips if already populated."""
    # Returns: ChromaDB collection object
```

#### `src/chatbot.py`

```python
def is_opinionated(question: str) -> bool:
    """Check if question is advice-seeking via keyword matching."""
    # Returns: True if opinionated, False if factual

def get_collection() -> chromadb.Collection:
    """Load ChromaDB collection with embedding function."""
    # Returns: ChromaDB collection object

def retrieve_chunks(question: str, top_k: int = 3) -> list[dict]:
    """Retrieve top-k most similar chunks from ChromaDB."""
    # Returns: [{text, metadata, distance}, ...]

def build_prompt(question: str, chunks: list[dict]) -> str:
    """Build LLM prompt with context and rules."""
    # Returns: Formatted prompt string

def answer_question(question: str) -> dict:
    """End-to-end query handler."""
    # Returns: {answer, citation, is_refusal, retrieved_chunks}
```

### 5.2 External API: Groq

| Field | Value |
|-------|-------|
| **Endpoint** | `https://api.groq.com/openai/v1/chat/completions` |
| **Model** | `llama-3.3-70b-versatile` |
| **Auth** | Bearer token (`GROQ_API_KEY` from `.env`) |
| **Temperature** | 0.1 (low randomness for factual answers) |
| **Max tokens** | 300 |
| **Rate limit** | Free tier: 30 requests/min, 7000 tokens/min |

**Request:**
```json
{
  "model": "llama-3.3-70b-versatile",
  "messages": [{"role": "user", "content": "<prompt>"}],
  "temperature": 0.1,
  "max_tokens": 300
}
```

**Response:**
```json
{
  "choices": [{
    "message": {
      "content": "The expense ratio of HDFC Large Cap Fund is 1.03%..."
    }
  }]
}
```

---

## 6. Deployment Architecture

### 6.1 Local Development (Current)

```
┌─────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE                        │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Python 3.10│  │  ChromaDB   │  │  Groq API   │    │
│  │  + venv     │  │  (local)    │  │  (remote)   │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │            │
│         └────────────────┼────────────────┘            │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │  Streamlit  │                       │
│                   │  :8501      │                       │
│                   └─────────────┘                       │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │   Browser   │                       │
│                   │  (user)     │                       │
│                   └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Production (Future)

```
┌─────────────────────────────────────────────────────────┐
│                      CLOUD                              │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Docker     │  │  ChromaDB   │  │  Groq API   │    │
│  │  Container  │  │  Server or  │  │  (remote)   │    │
│  │  (Streamlit)│  │  Pinecone   │  │             │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │            │
│         └────────────────┼────────────────┘            │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │  Cloud LB   │                       │
│                   │  (HTTPS)    │                       │
│                   └─────────────┘                       │
│                          │                              │
│                   ┌──────┴──────┐                       │
│                   │   Users     │                       │
│                   │  (global)   │                       │
│                   └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                       │
│                                                         │
│  Layer 1: API KEY PROTECTION                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • GROQ_API_KEY stored in .env (never committed) │   │
│  │ • .env in .gitignore                            │   │
│  │ • .env.example has placeholder only             │   │
│  │ • python-dotenv loads at runtime                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Layer 2: NO PII                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • No user accounts or authentication            │   │
│  │ • No PII fields in data model                   │   │
│  │ • No logging of user inputs                     │   │
│  │ • Session state only stores current question    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Layer 3: SOURCE INTEGRITY                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Only public Groww pages as sources            │   │
│  │ • No third-party blogs or scraped content       │   │
│  │ • Every answer has verifiable citation          │   │
│  │ • "Last updated" date on every answer           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Layer 4: OPINION GUARD                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • Keyword-based advice detection                │   │
│  │ • Refusal message with AMFI educational link    │   │
│  │ • LLM prompt enforces facts-only rule           │   │
│  │ • Temperature 0.1 minimizes hallucination       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Error Handling

```
┌─────────────────────────────────────────────────────────┐
│                   ERROR SCENARIOS                        │
│                                                         │
│  1. Missing GROQ_API_KEY                                │
│     → Groq client raises authentication error            │
│     → User sees: "API key not configured"                │
│     → Fix: Add key to .env                              │
│                                                         │
│  2. ChromaDB not ingested                               │
│     → Collection is empty                               │
│     → retrieve_chunks returns []                        │
│     → User sees: "I don't have that information..."      │
│     → Fix: Run python src/ingest.py                     │
│                                                         │
│  3. Groq API rate limit                                 │
│     → HTTP 429 from Groq                                │
│     → User sees: error message                          │
│     → Fix: Wait and retry, or upgrade plan              │
│                                                         │
│  4. Groq API timeout                                    │
│     → Request exceeds timeout                           │
│     → User sees: error message                          │
│     → Fix: Retry query                                  │
│                                                         │
│  5. Out-of-scope question                               │
│     → No relevant chunks retrieved                      │
│     → User sees: "I don't have that information..."      │
│     → Fix: Rephrase or ask about covered schemes        │
│                                                         │
│  6. Opinionated question                                │
│     → Detected by keyword guard                         │
│     → User sees: Refusal message + AMFI link             │
│     → Fix: N/A (by design)                              │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Performance Characteristics

| Metric | Target | Notes |
|--------|--------|-------|
| Ingestion time | ~30s | One-time; includes model download (~110 MB) on first run |
| Query latency | 2-5s | Embed (~0.5s) + Retrieve (~0.1s) + Groq (~1.5-4s) |
| Concurrent users | 1-5 | Streamlit single-process; not production-scaled |
| ChromaDB size | ~300 KB | 20 chunks × 384-dim vectors |
| Memory usage | ~500 MB | Embedding model + ChromaDB + Streamlit |
| Cold start | ~10s | Streamlit app boot + model load |

---

## 10. Technology Decisions

| Decision | Alternatives Considered | Rationale |
|----------|------------------------|-----------|
| **all-MiniLM-L6-v2** | OpenAI embeddings, BGE, E5 | Free, local, no API key, good semantic similarity, 384-dim |
| **ChromaDB** | Pinecone, Weaviate, FAISS, Milvus | Lightweight, persistent, zero-config, cosine similarity, Python-native |
| **Groq** | OpenAI, Anthropic, local LLM | Free tier, fast inference, llama-3.3-70b quality, simple API |
| **Streamlit** | Flask, FastAPI, Gradio, React | Python-native, minimal code, fast prototype, built-in widgets |
| **Section-aware chunking** | Fixed-size, sentence, recursive | Matches page structure, keeps related facts together, 200 tok is ideal for FAQ |
| **Keyword opinion guard** | LLM-based classifier, regex | Simple, fast, zero-cost, transparent, sufficient for demo scope |

---

## 11. Testing Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    TEST LAYERS                           │
│                                                         │
│  Unit Tests (manual verification)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • chunk_text() produces correct number of chunks │   │
│  │ • is_opinionated() detects advice keywords       │   │
│  │ • retrieve_chunks() returns relevant results     │   │
│  │ • build_prompt() includes context and rules      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Integration Tests                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • ingest.py → ChromaDB populated correctly       │   │
│  │ • chatbot.py → End-to-end answer with citation   │   │
│  │ • app.py → UI renders and responds               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Acceptance Tests (demo script)                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ • 5 factual questions → correct answers + links  │   │
│  │ • 3 opinionated questions → refusal + AMFI link  │   │
│  │ • 2 out-of-scope questions → "I don't have..."   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 12. Future Enhancements

| ID | Enhancement | Priority | Effort |
|----|-------------|----------|--------|
| E-1 | Add AMC/SEBI/AMFI pages to corpus | Medium | Low |
| E-2 | Hybrid search (BM25 + vector) for better retrieval | Medium | Medium |
| E-3 | Reranker (Cohere Rerank or cross-encoder) | Low | Medium |
| E-4 | Multi-turn conversation memory | Medium | Medium |
| E-5 | Feedback thumbs up/down on answers | Low | Low |
| E-6 | Docker containerization | Medium | Low |
| E-7 | CI/CD with GitHub Actions | Low | Medium |
| E-8 | Monitoring (LangSmith / Phoenix) | Low | Medium |
| E-9 | Expand to 20+ schemes | High | Low |
| E-10 | User authentication + chat history | Low | High |
