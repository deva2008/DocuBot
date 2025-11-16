# DocuBot Studio
Turn your PDFs into a grounded, domain‑agnostic chatbot in minutes.

## What it is
- Upload PDFs → app auto‑parses, chunks, embeds, indexes, and launches chat.
- Answers are grounded in retrieved snippets with citations.
- CPU‑friendly; FAISS for fast search; lexical fallback available.

## Quick start
1. pip install -r requirements.txt
2. streamlit run app_steps_patch.py
3. Upload PDFs → Process PDFs → chat in Step 8.

## Architecture
```mermaid
flowchart LR
  U[End User (Browser)] -->|HTTPS| ST[Streamlit App]

  subgraph ST_RUNTIME[Streamlit Runtime]
    ST --> SS[(Session State)]
    ST --> PARSE[pypdf: Parse PDFs]
    ST --> CHUNK[Chunker: char-size + overlap]
    ST --> EMB[Sentence-Transformers: Embeddings]
    ST --> INDEX[FAISS IndexFlatIP or NumPy]
    ST --> RET[Retriever: Vector or Lexical]
    ST --> GEN[Answer Composer: Grounded Markdown]
    ST --> UI[UI: Steps, Metrics, Chat]
  end

  PARSE --> CHUNK --> EMB --> INDEX
  UI --> RET
  INDEX --> RET
  RET --> GEN
  GEN --> UI
  SS --- UI
```

## Data flow
```mermaid
sequenceDiagram
  participant U as User
  participant UI as Streamlit UI
  participant P as pypdf
  participant C as Chunker
  participant E as Embeddings (S-Transformers)
  participant I as Index (FAISS/NumPy)
  participant R as Retriever
  participant G as Grounded Answer

  U->>UI: Upload PDFs + Process
  UI->>P: Extract text pages
  P-->>UI: Pages
  UI->>C: Split (size, overlap)
  C-->>UI: Chunks
  UI->>E: Encode chunks
  E-->>UI: Vectors
  UI->>I: Build index (add vectors)
  UI-->>U: Steps 1–7 complete → open Chat

  U->>UI: Ask a question
  UI->>R: search_topk(query)
  R->>I: Vector search (or Lexical)
  I-->>R: Top‑K (score, chunk)
  R-->>UI: Top‑K results
  UI->>G: Build structured answer + sources
  G-->>U: Answer + Key points + Sources
```

## User journey
```mermaid
flowchart TD
  A[Open App] --> B[Step 1: Upload PDFs]
  B --> C[Set Chunk Size & Overlap]
  C --> D[Click 'Process PDFs']
  D --> E[Auto: Parse → Chunk → Embed → Index]
  E --> F[Mark Steps 1–7 Complete]
  F --> G[Open Step 8: Chat]
  G --> H[Ask a Question]
  H --> I[Retrieve Top‑K]
  I --> J[Structured Answer + Sources]
  J --> K{Satisfied?}
  K -- No --> H
  K -- Yes --> L[Finish / New Question]
```

## Tech stack
- Streamlit, Python 3
- pypdf, sentence-transformers, faiss-cpu, numpy
- Character-based chunking with overlap
- Vector retrieval (cosine) + lexical fallback

## Deployment (Streamlit Cloud)
- Repo: deva2008/DocuBot (main)
- App file: app_steps_patch.py
- Requirements: requirements.txt

## Exporting diagrams
- Paste any ```mermaid block into https://mermaid.live → Download as SVG/PNG.

## Roadmap
- OCR fallback for scanned PDFs (pytesseract)
- Clickable citations/side panel
- Hybrid retrieval (BM25 + vector)
- Persisted indexes, evaluation suite
