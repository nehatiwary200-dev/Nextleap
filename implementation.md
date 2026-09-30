# Implementation Guide: HDFC Mutual Fund FAQ Assistant — RAG Chatbot

| Field | Value |
|-------|-------|
| **Document Type** | Phase-wise Implementation Guide |
| **Derived From** | `architecture.md` → `PRD.md` |
| **Date** | 28 Sep 2026 |
| **Status** | Ready for Cursor implementation |
| **Target** | Class demo prototype |

---

## How to Use This Document

Each phase below is a **self-contained unit of work** that can be handed to Cursor as a single prompt. For each phase:

1. **Read** the phase description and acceptance criteria
2. **Implement** the tasks in order
3. **Verify** against the acceptance criteria before moving to the next phase

**Cursor prompt template:**
```
Read implementation.md Phase N and implement it.
Follow architecture.md for design decisions.
Verify against the acceptance criteria at the end of the phase.
```

---

## Phase 0: Project Setup & Dependencies

**Goal:** Initialize the project structure and install all dependencies.

### Tasks

1. Create project directory structure:
   ```
   /Users/nehatiwary/Documents/Nextleap/
   ├── src/
   ├── data/
   ├── chroma_db/
   ├── requirements.txt
   ├── .env.example
   ├── .gitignore
   └── README.md
   ```

2. Create `requirements.txt` with:
   ```
   sentence-transformers>=5.0.0
   chromadb==0.4.22
   groq==0.4.1
   streamlit==1.29.0
   python-dotenv==1.0.0
   ```

3. Create `.env.example`:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. Create `.gitignore`:
   ```
   .env
   chroma_db/
   __pycache__/
   *.pyc
   .venv/
   .DS_Store
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Acceptance Criteria
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `python -c "import sentence_transformers, chromadb, groq, streamlit"` succeeds
- [ ] `.env.example` and `.gitignore` exist with correct content

---

## Phase 1: Data Layer — Source URLs & Scheme Data

**Goal:** Define the 5 source URLs and the structured scheme data model.

### Tasks

1. Create `data/sources.csv` with 5 rows:
   ```csv
   scheme_name,category,source_url
   HDFC Large Cap Fund Direct Growth,Equity - Large Cap,https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
   HDFC Flexi Cap Direct Plan Growth,Equity - Flexi Cap,https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
   HDFC ELSS Tax Saver Fund Direct Plan Growth,Equity - ELSS,https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
   HDFC Small Cap Fund Direct Growth,Equity - Small Cap,https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth
   HDFC Balanced Advantage Fund Direct Growth,Hybrid - Dynamic Asset Allocation,https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth
   ```

2. Create `src/ingest.py` with the `SCHEMES` list containing 5 scheme dicts. Each dict must have these keys:
   ```python
   {
       "scheme_name": str,
       "category": str,
       "source_url": str,
       "risk_level": str,
       "nav": str,
       "aum": str,
       "expense_ratio": str,
       "rating": str,
       "min_sip": str,
       "min_lumpsum": str,
       "exit_load": str,
       "stamp_duty": str,
       "tax_implication": str,
       "benchmark": str,
       "investment_objective": str,
       "sid_link": str,
       "lock_in": str,  # optional, only for ELSS
       "fund_managers": [
           {"name": str, "tenure": str, "education": str}
       ],
   }
   ```

3. Populate all 5 schemes with data from the Groww pages (as of 25 Sep 2026):

   | Field | Large Cap | Flexi Cap | ELSS | Small Cap | Balanced Advantage |
   |-------|-----------|-----------|------|-----------|-------------------|
   | risk_level | Very High | Very High | Very High | Very High | Very High |
   | nav | ₹1,189.08 | ₹2,214.57 | ₹1,447.38 | ₹159.82 | ₹557.73 |
   | aum | ₹39,933.37 Cr | ₹1,13,606.47 Cr | ₹15,991.78 Cr | ₹41,890.86 Cr | ₹1,07,295.79 Cr |
   | expense_ratio | 1.03% | 0.77% | 1.21% | 0.78% | 0.78% |
   | rating | 4 | 5 | 5 | 3 | 5 |
   | min_sip | ₹100 | ₹100 | ₹500 | ₹100 | ₹100 |
   | min_lumpsum | ₹100 | ₹100 | ₹500 | ₹100 | ₹100 |
   | exit_load | 1% if redeemed within 1 year | 1% if redeemed within 1 year | Nil | 1% if redeemed within 1 year | 1% for units in excess of 15% of the investment if redeemed within 1 year |
   | benchmark | NIFTY 100 Total Return Index | NIFTY 500 Total Return Index | NIFTY 500 Total Return Index | BSE 250 SmallCap Total Return Index | NIFTY 500 Total Return Index |
   | lock_in | — | — | 3 years (ELSS mandatory lock-in) | — | — |

### Acceptance Criteria
- [ ] `data/sources.csv` has 5 rows with correct URLs
- [ ] `src/ingest.py` contains `SCHEMES` list with 5 dicts
- [ ] Each scheme dict has all required keys
- [ ] `python -c "from src.ingest import SCHEMES; print(len(SCHEMES))"` prints `5`

---

## Phase 2: Ingestion Pipeline — Section-aware Chunking

**Goal:** Split each scheme into 4 sections and chunk them for embedding.

### Tasks

1. In `src/ingest.py`, implement `scheme_to_sections(scheme)`:
   ```python
   def scheme_to_sections(scheme):
       """Split a scheme dict into 4 named sections.
       Returns: list of (section_name, section_text) tuples
       """
   ```
   - Section 1 "Overview": Combine scheme_name, category, risk_level, nav, aum, expense_ratio, rating, min_sip, min_lumpsum into one text
   - Section 2 "Exit Load & Tax": Combine exit_load, stamp_duty, tax_implication
   - Section 3 "Fund Management": Combine all fund_managers (name, tenure, education)
   - Section 4 "About": Combine investment_objective, benchmark, sid_link, lock_in (if present)

2. Implement `chunk_text(text, chunk_size=200, overlap=30)`:
   ```python
   def chunk_text(text, chunk_size=200, overlap=30):
       """Sliding window chunker (word-based).
       Returns: list of chunk strings
       """
   ```
   - Split text into words
   - Slide window of `chunk_size` words with `overlap` words overlap
   - Return list of chunk strings

3. Implement `build_chunks(schemes)`:
   ```python
   def build_chunks(schemes):
       """Generate all chunks with metadata.
       Returns: list of chunk dicts with keys:
           chunk_id, scheme_name, category, section, source_url, text
       """
   ```
   - For each scheme, call `scheme_to_sections()`
   - For each section, call `chunk_text()`
   - Assign sequential chunk_id: `chunk_0000`, `chunk_001`, etc.
   - Attach metadata: scheme_name, category, section, source_url

4. Implement `save_chunks_to_txt(chunks, filepath)`:
   ```python
   def save_chunks_to_txt(chunks, filepath):
       """Save chunks to human-readable text file."""
   ```
   - Write header with total chunks, chunk size, overlap
   - For each chunk: write chunk_id, scheme_name, section, source_url, text
   - Separate chunks with dashed lines

### Acceptance Criteria
- [ ] `scheme_to_sections()` returns 4 tuples per scheme
- [ ] `chunk_text("word " * 500)` returns multiple chunks
- [ ] `build_chunks(SCHEMES)` returns 20 chunks (5 schemes × 4 sections)
- [ ] `data/chunks.txt` is created and human-readable
- [ ] `python -c "from src.ingest import build_chunks, SCHEMES; print(len(build_chunks(SCHEMES)))"` prints `20`

---

## Phase 3: Ingestion Pipeline — Embedding & ChromaDB Storage

**Goal:** Embed chunks and persist to ChromaDB.

### Tasks

1. In `src/ingest.py`, implement `embed_and_store(chunks)`:
   ```python
   def embed_and_store(chunks):
       """Embed chunks and persist to ChromaDB. Skips if already populated.
       Returns: ChromaDB collection object
       """
   ```
   - Create `chromadb.PersistentClient(path="chroma_db")`
   - Create `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`
   - Get or create collection `"hdfc_mutual_funds"` with `metadata={"hnsw:space": "cosine"}`
   - If `collection.count() > 0`, skip ingestion (idempotent)
   - Otherwise, add all chunks with ids, documents, and metadatas
   - Metadata per chunk: `{"scheme_name", "category", "section", "source_url"}`

2. Implement `main()` CLI entry point:
   ```python
   def main():
       """CLI entry point for ingestion pipeline."""
   ```
   - Print progress: building chunks, saving to txt, embedding to ChromaDB
   - Call `build_chunks(SCHEMES)`, `save_chunks_to_txt()`, `embed_and_store()`
   - Print summary at end

3. Add constants at top of file:
   ```python
   CHUNK_SIZE = 200
   CHUNK_OVERLAP = 30
   CHROMA_PERSIST_DIR = "chroma_db"
   CHUNKS_TXT_PATH = "data/chunks.txt"
   ```

### Acceptance Criteria
- [ ] `python src/ingest.py` runs without errors
- [ ] `chroma_db/` directory is created with `chroma.sqlite3`
- [ ] Collection has 20 documents
- [ ] Running `python src/ingest.py` again skips ingestion (prints "already has 20 documents")
- [ ] `data/chunks.txt` contains 20 chunks with metadata

---

## Phase 4: Query Pipeline — Opinion Guard

**Goal:** Detect and refuse opinionated/advice-seeking questions.

### Tasks

1. Create `src/chatbot.py` with opinion guard:
   ```python
   OPINION_KEYWORDS = [
       "should i buy", "should i sell", "should i invest", "is it good to",
       "is it bad to", "best fund", "worst fund", "top fund", "which fund should",
       "recommend", "suggestion", "advice", "portfolio", "allocate my",
       "how much should i", "will i get", "can i earn", "guaranteed return",
       "is best for", "is better", "should i choose", "which is best",
       "which is better", "what should i do", "is it worth",
   ]

   REFUSAL_MESSAGE = (
       "I can only provide factual information from official public pages. "
       "I cannot give investment advice or recommendations. "
       "For educational resources on mutual funds, visit the [AMFI investor education page](https://www.amfiindia.com/investor-corner)."
   )
   ```

2. Implement `is_opinionated(question)`:
   ```python
   def is_opinionated(question):
       """Check if question is advice-seeking via keyword matching.
       Returns: True if opinionated, False if factual
       """
   ```
   - Lowercase the question
   - Check if any OPINION_KEYWORD is a substring
   - Return True/False

### Acceptance Criteria
- [ ] `is_opinionated("Should I buy HDFC Large Cap?")` returns `True`
- [ ] `is_opinionated("What is the expense ratio?")` returns `False`
- [ ] `is_opinionated("Which fund is best for me?")` returns `True`
- [ ] `is_opinionated("ELSS lock-in period?")` returns `False`

---

## Phase 5: Query Pipeline — Retrieval

**Goal:** Retrieve top-3 relevant chunks from ChromaDB for a given question.

### Tasks

1. In `src/chatbot.py`, implement `get_collection()`:
   ```python
   def get_collection():
       """Load ChromaDB collection with embedding function.
       Returns: ChromaDB collection object
       """
   ```
   - Create `chromadb.PersistentClient(path="chroma_db")`
   - Create `SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")`
   - Return collection `"hdfc_mutual_funds"` with cosine similarity

2. Implement `retrieve_chunks(question, top_k=3)`:
   ```python
   def retrieve_chunks(question, top_k=3):
       """Retrieve top-k most similar chunks from ChromaDB.
       Returns: list of {text, metadata, distance} dicts
       """
   ```
   - Call `collection.query(query_texts=[question], n_results=top_k)`
   - Parse results into list of dicts with text, metadata, distance
   - Return empty list if no results

3. Add constants:
   ```python
   CHROMA_PERSIST_DIR = "chroma_db"
   TOP_K = 3
   ```

### Acceptance Criteria
- [ ] `retrieve_chunks("expense ratio of HDFC Large Cap")` returns 3 chunks
- [ ] Top chunk's scheme_name contains "Large Cap"
- [ ] `retrieve_chunks("ELSS lock-in")` returns chunks with scheme_name containing "ELSS"
- [ ] Each chunk has `text`, `metadata`, `distance` keys

---

## Phase 6: Query Pipeline — LLM Answer Generation

**Goal:** Build prompt, call Groq LLM, and format the answer with citation.

### Tasks

1. In `src/chatbot.py`, implement `build_prompt(question, chunks)`:
   ```python
   def build_prompt(question, chunks):
       """Build LLM prompt with context and rules.
       Returns: formatted prompt string
       """
   ```
   - Include system instruction: "You are a factual FAQ assistant for HDFC Mutual Fund schemes."
   - Include rules: ≤3 sentences, one citation, no advice, no performance claims
   - Include context: for each chunk, show [Source N] with scheme_name, section, URL, content
   - Include user question at the end

2. Implement `answer_question(question)`:
   ```python
   def answer_question(question):
       """End-to-end query handler.
       Returns: {answer, citation, is_refusal, retrieved_chunks}
       """
   ```
   - Call `is_opinionated(question)` → if True, return refusal dict
   - Call `retrieve_chunks(question)` → if empty, return "don't have info" dict
   - Call `build_prompt(question, chunks)`
   - Call Groq API:
     ```python
     client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
     response = client.chat.completions.create(
         model="llama-3.3-70b-versatile",
         messages=[{"role": "user", "content": prompt}],
         temperature=0.1,
         max_tokens=300,
     )
     ```
   - Append `\n\n*Last updated from sources: {today}*` to answer
   - Return dict with answer, citation (top chunk's source_url), is_refusal=False, retrieved_chunks

3. Add imports and constants:
   ```python
   import os
   from datetime import datetime
   import chromadb
   from chromadb.utils import embedding_functions
   from groq import Groq

   GROQ_MODEL = "llama-3.3-70b-versatile"
   ```

### Acceptance Criteria
- [ ] `build_prompt("test", chunks)` returns string with context and rules
- [ ] `answer_question("What is the expense ratio of HDFC Large Cap?")` returns dict with answer containing "1.03%"
- [ ] Answer includes citation URL
- [ ] Answer includes "Last updated from sources:" date
- [ ] `answer_question("Should I buy HDFC?")` returns `is_refusal=True`

---

## Phase 7: Streamlit UI

**Goal:** Build the user interface with welcome, examples, input, answer, and citation.

### Tasks

1. Create `src/app.py`:
   ```python
   import streamlit as st
   from chatbot import answer_question
   ```

2. Configure page:
   ```python
   st.set_page_config(page_title="HDFC MF FAQ Assistant", page_icon="📊", layout="centered")
   ```

3. Add custom CSS:
   - `.main-header` — large bold title
   - `.sub-header` — smaller gray subtitle
   - `.disclaimer` — yellow warning box
   - `.citation-box` — blue left-border box
   - Button styling

4. Render UI sections:
   - **Header:** "HDFC Mutual Fund FAQ Assistant"
   - **Sub-header:** "Ask factual questions about HDFC mutual fund schemes..."
   - **Disclaimer:** "Facts-only. No investment advice."
   - **Example buttons:** 3 columns with preset questions
   - **Text input:** `st.text_input` for custom questions
   - **Get Answer button:** primary button
   - **Answer display:** `st.markdown(result["answer"])`
   - **Citation box:** clickable link
   - **Footer:** scope and tech stack info

5. Handle session state:
   ```python
   if "question" not in st.session_state:
       st.session_state["question"] = ""
   ```

### Acceptance Criteria
- [ ] `streamlit run src/app.py` starts without errors
- [ ] Page shows welcome line, 3 example buttons, text input, disclaimer
- [ ] Clicking example button populates the input
- [ ] Clicking "Get Answer" shows answer with citation
- [ ] Opinionated question shows refusal message
- [ ] Citation is a clickable link

---

## Phase 8: Sample Q&A & Documentation

**Goal:** Create sample Q&A file and update README.

### Tasks

1. Create `data/sample_qa.md` with 10 Q&A pairs covering:
   - Expense ratio (Large Cap)
   - ELSS lock-in period
   - Minimum SIP (Small Cap)
   - Exit load (Flexi Cap)
   - Benchmark (Balanced Advantage)
   - Fund managers (Large Cap)
   - AUM (Flexi Cap)
   - Tax implication (ELSS)
   - Risk level (Small Cap)
   - Minimum investment (ELSS)

2. Update `README.md` with:
   - Project description
   - Architecture diagram (from architecture.md)
   - Tech stack table
   - Setup instructions (install, .env, ingest, run)
   - Known limitations
   - Project structure
   - Deliverables checklist

### Acceptance Criteria
- [ ] `data/sample_qa.md` has 10 Q&A pairs with sources
- [ ] `README.md` has setup steps that work
- [ ] All deliverables checklist items are checked

---

## Phase 9: End-to-End Testing & Demo Prep

**Goal:** Verify the full pipeline works and prepare for class demo.

### Tasks

1. Run full ingestion:
   ```bash
   python src/ingest.py
   ```
   Verify: 20 chunks created, ChromaDB populated, chunks.txt saved

2. Test retrieval:
   ```python
   from src.chatbot import retrieve_chunks
   chunks = retrieve_chunks("expense ratio of HDFC Large Cap")
   assert len(chunks) == 3
   assert "Large Cap" in chunks[0]["metadata"]["scheme_name"]
   ```

3. Test opinion guard:
   ```python
   from src.chatbot import is_opinionated
   assert is_opinionated("Should I buy?") == True
   assert is_opinionated("What is the expense ratio?") == False
   ```

4. Test end-to-end (requires GROQ_API_KEY):
   ```python
   from src.chatbot import answer_question
   result = answer_question("What is the expense ratio of HDFC Large Cap?")
   assert "1.03%" in result["answer"]
   assert result["citation"] is not None
   ```

5. Launch UI:
   ```bash
   streamlit run src/app.py
   ```
   Verify: all sections render, questions work, citations show

6. Prepare demo script (see PRD section 12)

### Acceptance Criteria
- [ ] All ingestion tests pass
- [ ] All retrieval tests pass
- [ ] All opinion guard tests pass
- [ ] End-to-end test returns correct answer with citation
- [ ] Streamlit UI loads at localhost:8501
- [ ] Demo script runs without issues

---

## Phase Summary

| Phase | Name | Key Output | Depends On |
|-------|------|------------|------------|
| 0 | Project Setup | requirements.txt, .env.example, .gitignore | — |
| 1 | Data Layer | sources.csv, SCHEMES list | Phase 0 |
| 2 | Chunking | scheme_to_sections(), chunk_text(), build_chunks() | Phase 1 |
| 3 | Embedding & Storage | embed_and_store(), chroma_db/ | Phase 2 |
| 4 | Opinion Guard | is_opinionated(), OPINION_KEYWORDS | Phase 0 |
| 5 | Retrieval | retrieve_chunks(), get_collection() | Phase 3 |
| 6 | LLM Generation | build_prompt(), answer_question() | Phase 4, 5 |
| 7 | Streamlit UI | src/app.py | Phase 6 |
| 8 | Documentation | sample_qa.md, README.md | Phase 1-7 |
| 9 | Testing & Demo | All tests pass, demo ready | Phase 0-8 |

---

## File → Phase Mapping

| File | Phases | Description |
|------|--------|-------------|
| `requirements.txt` | 0 | Python dependencies |
| `.env.example` | 0 | API key template |
| `.gitignore` | 0 | Git exclusions |
| `data/sources.csv` | 1 | 5 source URLs |
| `src/ingest.py` | 1, 2, 3 | SCHEMES data + chunking + embedding |
| `src/chatbot.py` | 4, 5, 6 | Opinion guard + retrieval + LLM |
| `src/app.py` | 7 | Streamlit UI |
| `data/chunks.txt` | 2, 3 | Human-readable chunks |
| `data/sample_qa.md` | 8 | Sample Q&A pairs |
| `README.md` | 8 | Setup and usage docs |
| `chroma_db/` | 3 | ChromaDB persistent storage |

---

## Quick Start (After All Phases)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key
cp .env.example .env
# Edit .env and add: GROQ_API_KEY=gsk_your_key_here

# 3. Run ingestion (one-time)
python src/ingest.py

# 4. Launch app
streamlit run src/app.py

# 5. Open browser at http://localhost:8501
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'chatbot'` | Running from wrong directory | `cd /Users/nehatiwary/Documents/Nextleap` first |
| `GROQ_API_KEY not found` | .env not created | `cp .env.example .env` and add key |
| `Collection is empty` | Ingestion not run | `python src/ingest.py` |
| `Rate limit exceeded` | Groq free tier limit | Wait 60s or upgrade plan |
| `Model download slow` | First-time download | Wait for ~110 MB download |
| `Streamlit port busy` | Another app on 8501 | `streamlit run src/app.py --server.port 8502` |
