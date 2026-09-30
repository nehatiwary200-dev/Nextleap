# PRD: HDFC Mutual Fund FAQ Assistant — RAG Chatbot

| Field | Value |
|-------|-------|
| **Document Type** | Product Requirements Document (PRD) |
| **Project** | HDFC Mutual Fund FAQ Assistant |
| **Architecture** | RAG (Retrieval-Augmented Generation) Chatbot |
| **Date** | 28 Sep 2026 |
| **Status** | Prototype — Class Demo |
| **Stakeholders** | Retail investors, support/content teams, demo audience |

---

## 1. Problem Statement

Retail investors and support teams repeatedly ask factual questions about mutual fund schemes — expense ratios, exit loads, minimum SIP amounts, lock-in periods, riskometers, benchmarks, and how to download statements. Today, these answers are scattered across AMC websites, AMFI portals, and distributor pages, requiring manual lookup.

**Goal:** Build a small FAQ assistant that answers facts about mutual fund schemes using **only official public pages**, with every answer carrying a source citation. No advice, no opinions.

---

## 2. Scope

### 2.1 In Scope

| Dimension | Detail |
|-----------|--------|
| **AMC** | HDFC Mutual Fund |
| **Schemes** | 5 schemes (see below) |
| **Data source** | 5 public Groww pages (one per scheme) |
| **Query types** | Factual Q&A: expense ratio, exit load, minimum SIP/lumpsum, ELSS lock-in, riskometer, benchmark, fund manager, AUM, tax, stamp duty, SID link |
| **UI** | Streamlit — welcome line, 3 example questions, text input, citation display |
| **Pipeline** | Ingestion (Load → Chunk → Embed → ChromaDB) + Query (Embed → Retrieve → LLM → Answer) |

### 2.2 Out of Scope

- Real-time NAV / AUM / price data
- Investment advice or portfolio recommendations
- Comparison of returns across schemes
- Non-HDFC AMCs or schemes
- User accounts, PII storage, or transaction capabilities
- Mobile app or API endpoints

### 2.3 Scheme Corpus

| # | Scheme | Category | Source URL |
|---|--------|----------|------------|
| 1 | HDFC Large Cap Fund Direct Growth | Equity — Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 2 | HDFC Flexi Cap Direct Plan Growth | Equity — Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 3 | HDFC ELSS Tax Saver Fund Direct Plan Growth | Equity — ELSS | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 4 | HDFC Small Cap Fund Direct Growth | Equity — Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 5 | HDFC Balanced Advantage Fund Direct Growth | Hybrid — Dynamic Asset Allocation | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

---

## 3. User Personas

| Persona | Description | Primary Need |
|---------|-------------|--------------|
| **Retail investor** | Comparing HDFC schemes before investing | Quick facts: fees, lock-in, risk, minimums |
| **Support / content team** | Answering repetitive MF questions | Verified answers with source links |
| **Demo audience** | Evaluating the RAG pipeline in a class setting | See ingestion → retrieval → generation working end-to-end |

---

## 4. Functional Requirements

### FR-1: Ingestion Pipeline

| Step | Description |
|------|-------------|
| **Load** | Fetch 5 Groww scheme pages; extract structured fields (NAV, AUM, expense ratio, exit load, min SIP, benchmark, fund managers, etc.) |
| **Chunk** | Section-aware splitting: each scheme → 4 sections (Overview, Exit Load & Tax, Fund Management, About). Chunk size: 200 tokens, overlap: 30 tokens |
| **Embed** | `sentence-transformers/all-MiniLM-L6-v2` (384-dim, local, no API key) |
| **Store** | ChromaDB persisted to `chroma_db/` — ingestion runs once, not on every restart |
| **Inspect** | All chunks saved to `data/chunks.txt` for human review |

### FR-2: Query Pipeline

| Step | Description |
|------|-------------|
| **Embed question** | Same `all-MiniLM-L6-v2` model |
| **Retrieve** | Top-3 chunks from ChromaDB (cosine similarity) |
| **LLM** | Groq API (`llama-3.3-70b-versatile`), temperature 0.1, max 300 tokens |
| **Answer** | ≤3 sentences, one citation link, "Last updated from sources: {date}" |

### FR-3: Opinion Guard

- Detect opinionated/advice-seeking queries via keyword matching
- Refuse with: *"I can only provide factual information from official public pages. I cannot give investment advice or recommendations."*
- Link to AMFI investor education page

### FR-4: UI (Streamlit)

- Welcome line + 3 example question buttons
- Text input for custom questions
- "Facts-only. No investment advice." disclaimer banner
- Citation box with clickable source link
- Footer with scope and tech stack info

---

## 5. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | **Public sources only** — no screenshots of app back-end, no third-party blogs |
| NFR-2 | **No PII** — never accept/store PAN, Aadhaar, account numbers, OTPs, emails, phone numbers |
| NFR-3 | **No performance claims** — don't compute or compare returns; link to official factsheet if asked |
| NFR-4 | **Clarity** — answers ≤3 sentences; "Last updated from sources: {date}" on every answer |
| NFR-5 | **Transparency** — every answer includes one source citation link |
| NFR-6 | **API key security** — Groq key stored in `.env`, never committed to Git |
| NFR-7 | **Persistence** — ChromaDB persisted to disk; ingestion runs once |
| NFR-8 | **Portability** — Python 3.10+, `pip install -r requirements.txt`, no GPU required |

---

## 6. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                    │
│                                                          │
│  Groww Pages → Extract → Section-aware Chunks → Embed    │
│  (5 URLs)      (fields)   (20 chunks, 200 tok)    (384d)│
│                                          ↓               │
│                                    ChromaDB (persisted)  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                     QUERY PIPELINE                       │
│                                                          │
│  Question → Embed (384d) → Retrieve top-3 → Groq LLM   │
│                                    ↓                     │
│                              Answer + Citation           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                         │
│  Welcome | Examples | Input | Answer | Citation | Disclaimer│
└─────────────────────────────────────────────────────────┘
```

---

## 7. Tech Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` | Local, no API key, 384-dim, good semantic similarity |
| Vector DB | ChromaDB 0.4.22 | Lightweight, persistent, cosine similarity, easy setup |
| LLM | Groq API (`llama-3.3-70b-versatile`) | Fast, free tier available, good instruction following |
| UI | Streamlit 1.29.0 | Quick prototype, Python-native, minimal frontend code |
| Language | Python 3.10+ | Ecosystem support for all above |
| Env management | `python-dotenv` | Secure API key handling |

---

## 8. Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Strategy | Section-aware splitting | Each scheme page has 4 natural sections; keeps related facts together |
| Chunk size | 200 tokens | Large enough for context, small enough for precise retrieval |
| Overlap | 30 tokens | Prevents facts being cut at chunk boundaries |
| Sections per scheme | 4 (Overview, Exit Load & Tax, Fund Management, About) | Matches the natural structure of Groww scheme pages |
| Metadata per chunk | `scheme_name`, `category`, `section`, `source_url`, `chunk_id` | Enables filtering and citation |
| Total chunks | 20 (5 schemes × 4 sections) | Small corpus, fast retrieval |

---

## 9. API & Environment

| Variable | Purpose | Required |
|----------|---------|----------|
| `GROQ_API_KEY` | Groq API authentication | Yes (for query pipeline) |

**Setup:**
```bash
cp .env.example .env
# Add your key: GROQ_API_KEY=gsk_...
```

Get a free key at: https://console.groq.com/

---

## 10. Deliverables Checklist

| # | Deliverable | Location | Status |
|---|-------------|----------|--------|
| 1 | Working prototype (Streamlit app) | `src/app.py` | Done |
| 2 | Ingestion pipeline | `src/ingest.py` | Done |
| 3 | Query pipeline (RAG) | `src/chatbot.py` | Done |
| 4 | Source list (CSV) | `data/sources.csv` | Done |
| 5 | Readable chunks (TXT) | `data/chunks.txt` | Done |
| 6 | Sample Q&A (MD) | `data/sample_qa.md` | Done |
| 7 | README with setup steps | `README.md` | Done |
| 8 | Disclaimer snippet (in UI) | `src/app.py` | Done |
| 9 | `.env.example` | `.env.example` | Done |
| 10 | `.gitignore` (excludes `.env`, `chroma_db/`) | `.gitignore` | Done |
| 11 | PRD (this document) | `PRD.md` | Done |

---

## 11. Known Limitations

| ID | Limitation | Mitigation |
|----|-----------|------------|
| L-1 | **Static data** — data is from 25 Sep 2026; NAV/AUM/expense ratios change | Note in UI; re-run `ingest.py` to refresh |
| L-2 | **No real-time data** — does not fetch live prices | Link to Groww/AMC pages for live data |
| L-3 | **Limited scope** — only 5 HDFC schemes | Out-of-scope questions get "I don't have that information" |
| L-4 | **No advice** — refuses opinionated questions | Keyword-based guard + AMFI educational link |
| L-5 | **Groq rate limits** — free tier has limits | Paid plan for heavy usage |
| L-6 | **Embedding model** — general-purpose, not finance-specific | Domain fine-tuning could improve accuracy |
| L-7 | **Single source per scheme** — only Groww pages | Could add AMC/SEBI/AMFI pages for richer corpus |

---

## 12. Demo Script (for class)

1. **Show the corpus** — `data/sources.csv` (5 URLs)
2. **Show the chunks** — `data/chunks.txt` (20 chunks, section-aware)
3. **Run ingestion** — `python src/ingest.py` (creates ChromaDB)
4. **Launch UI** — `streamlit run src/app.py`
5. **Ask factual questions:**
   - "Expense ratio of HDFC Large Cap Fund?"
   - "ELSS lock-in period?"
   - "Minimum SIP for HDFC Small Cap?"
   - "Who manages HDFC Flexi Cap?"
   - "Benchmark for HDFC Balanced Advantage?"
6. **Ask an opinionated question:**
   - "Should I buy HDFC Large Cap?" → Shows refusal + AMFI link
7. **Show the citation** — every answer has a clickable source link
8. **Show the architecture** — Ingestion → ChromaDB → Retrieval → Groq → Answer

---

## 13. Success Criteria

| Criterion | Target |
|-----------|--------|
| Ingestion completes without errors | 20 chunks, 5 schemes |
| Retrieval returns relevant chunks | Top-3 chunks match query intent |
| Answers are factual | ≤3 sentences, grounded in retrieved context |
| Every answer has a citation | 100% of factual answers include source link |
| Opinionated questions refused | 100% detection rate for advice-seeking queries |
| UI loads and responds | Streamlit app starts in <10s |
| No PII collected | Zero PII fields in codebase |
| API key not committed | `.env` in `.gitignore` |
