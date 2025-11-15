import streamlit as st
import streamlit.components.v1 as components
import json
from typing import List
import numpy as np
from io import BytesIO
try:
    import faiss  # type: ignore
    HAS_FAISS = True
except Exception:  # pragma: no cover
    faiss = None
    HAS_FAISS = False
try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except Exception:
    SentenceTransformer = None  # type: ignore
    HAS_ST = False
try:
    from pypdf import PdfReader
    HAS_PDF = True
except Exception:
    PdfReader = None  # type: ignore
    HAS_PDF = False

# ---- Basic config ----
PAGE_TITLE = "DocuBot Studio — Configuration Explorer"
st.set_page_config(page_title=PAGE_TITLE, layout="wide", initial_sidebar_state="expanded")

# ---- Steps metadata (same as your design) ----
STEPS = [
    {"id": 1, "title": "Upload PDF(s)"},
    {"id": 2, "title": "Chunk & Preview"},
    {"id": 3, "title": "Embeddings & Model Selection"},
    {"id": 4, "title": "Build Index & Retrieval"},
    {"id": 5, "title": "Prompt Template & LLM Selection"},
    {"id": 6, "title": "Run Fine-Tuning Experiments"},
    {"id": 7, "title": "Run Verifiability Checks"},
    {"id": 8, "title": "Launch Chatbot"},
]

# ---- Helpers: Chart.js small helper (client-side) ----
def render_chartjs(container_id: str, labels: List[str], datasets: List[dict], height: int = 360):
    """
    Render a Chart.js chart via components.html.
    datasets: list of dicts {label:..., data:[...], type?: 'bar'|'line', yAxisID?: 'A'|'B'}
    """
    payload = {"labels": labels, "datasets": datasets}
    html = f"""
    <div style="width:100%; height:{height}px;">
      <canvas id="{container_id}" style="width:100%; height:100%;"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
    <script>
      const payload = {json.dumps(payload)};
      const ctx = document.getElementById('{container_id}');
      const config = {{
        type: payload.datasets.length > 1 ? 'bar' : (payload.datasets[0].type || 'bar'),
        data: payload,
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'top' }},
            title: {{ display: true, text: 'Simulated Chart' }}
          }},
          scales: {{
            A: {{ type: 'linear', position: 'left' }},
            B: {{ type: 'linear', position: 'right', grid: {{ drawOnChartArea: false }} }}
          }}
        }}
      }};
      new Chart(ctx, config);
    </script>
    """
    components.html(html, height=height, scrolling=False)

# ---- RAG helpers: parsing, chunking, embedding, indexing, retrieval ----
def parse_pdfs(uploaded_files: List["UploadedFile"]) -> List[dict]:
    """Return list of page dicts: {source, page, text}."""
    out = []
    if not HAS_PDF:
        return out
    for f in uploaded_files:
        try:
            reader = PdfReader(BytesIO(f.read()))
            n_pages = len(reader.pages)
            for i in range(n_pages):
                try:
                    text = reader.pages[i].extract_text() or ""
                except Exception:
                    text = ""
                out.append({"source": f.name, "page": i + 1, "text": text})
        except Exception:
            continue
    return out

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    chunks = []
    if not text:
        return chunks
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(end - overlap, start + 1)
    return chunks

def build_chunks(pages: List[dict], chunk_size: int, overlap: int) -> List[dict]:
    chunks = []
    cid = 0
    for p in pages:
        segs = chunk_text(p.get("text", ""), chunk_size, overlap)
        for seg in segs:
            cid += 1
            chunks.append({
                "id": f"ch{cid}",
                "text": seg.strip(),
                "page": p.get("page", "-"),
                "source": p.get("source", "uploaded")
            })
    return chunks

def ensure_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    if not HAS_ST:
        return None
    if "embedding_model" in st.session_state and st.session_state.get("embedding_model_name") == model_name:
        return st.session_state.embedding_model
    model = SentenceTransformer(model_name)
    st.session_state.embedding_model = model
    st.session_state.embedding_model_name = model_name
    return model

def compute_embeddings(texts: List[str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> np.ndarray:
    """Compute embeddings with retry + fallback to a smaller model if the first load fails."""
    try:
        model = ensure_embedding_model(model_name)
        if model is None:
            return np.zeros((len(texts), 384), dtype=np.float32)
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        return embs.astype(np.float32)
    except Exception:
        # Fallback to a smaller model
        fallback = "sentence-transformers/paraphrase-MiniLM-L3-v2"
        model = ensure_embedding_model(fallback)
        if model is None:
            raise
        st.session_state.embedding_model_name = fallback
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        return embs.astype(np.float32)

def build_index(embs: np.ndarray):
    if embs is None or len(embs) == 0:
        return None
    if HAS_FAISS:
        index = faiss.IndexFlatIP(embs.shape[1])
        index.add(embs)
        return index
    # fallback: store matrix for numpy cosine search
    return {"matrix": embs}

def search_topk(query: str, k: int = 5):
    """Return list of (score, chunk_dict). Uses FAISS if available, else token overlap."""
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        return []
    # Force lexical if user selected it
    if st.session_state.get("retrieval_backend") == "lexical":
        return retrieve_in_memory_with_scores(query, top_k=k)
    # Prefer vector search if we have embeddings and index
    if st.session_state.get("embeddings") is not None and st.session_state.get("index") is not None and HAS_ST:
        model = ensure_embedding_model(st.session_state.get("embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2"))
        q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
        idx = st.session_state["index"]
        if HAS_FAISS and isinstance(idx, faiss.Index):
            D, I = idx.search(q, k)
            pairs = []
            for score, idx_i in zip(D[0].tolist(), I[0].tolist()):
                if idx_i == -1:
                    continue
                ch = chunks[idx_i]
                pairs.append((float(score), ch))
            return pairs
        else:
            M = st.session_state["index"].get("matrix")
            sims = (q @ M.T)[0]
            order = np.argsort(-sims)[:k]
            return [(float(sims[i]), chunks[i]) for i in order]
    # fallback: lexical overlap scoring
    return retrieve_in_memory_with_scores(query, top_k=k)
STOPWORDS = set("""
the a an and or but if while is are was were be been being to of in on for with as by from at this that these those into over under within without about up down out off then than so such it its their your our my we you he she they them i me his her theirs ours yours my
""".split())

def _tokenize(text: str) -> List[str]:
    return [t for t in ''.join([c.lower() if c.isalnum() else ' ' for c in text]).split() if t and t not in STOPWORDS]

# Minimum score to consider a hit relevant (tune as needed)
MIN_SCORE = 3

def retrieve_in_memory(query: str, top_k: int = 3):
    """Naive in-memory retrieval over st.session_state['chunks'].
    Expects st.session_state.chunks = List[dict(text=..., id=...)]
    """
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        return []
    q_tokens = _tokenize(query)
    q_phrase = ' '.join(q_tokens)
    scored = []
    for c in chunks:
        text = c.get("text") or ""
        t_tokens = _tokenize(text)
        token_overlap = len(set(q_tokens) & set(t_tokens))
        phrase_bonus = 6 if q_phrase and q_phrase in text.lower() else 0
        score = token_overlap + phrase_bonus
        scored.append((score, c))
    # filter low scores
    scored = [pair for pair in scored if pair[0] >= MIN_SCORE]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _s, c in scored[:top_k]]

# Variant that returns (score, chunk) for debugging/UI
def retrieve_in_memory_with_scores(query: str, top_k: int = 3):
    chunks = st.session_state.get("chunks", [])
    if not chunks:
        return []
    q_tokens = _tokenize(query)
    q_phrase = ' '.join(q_tokens)
    scored = []
    for c in chunks:
        text = c.get("text") or ""
        t_tokens = _tokenize(text)
        token_overlap = len(set(q_tokens) & set(t_tokens))
        phrase_bonus = 6 if q_phrase and q_phrase in text.lower() else 0
        score = token_overlap + phrase_bonus
        scored.append((score, c))
    # filter low scores
    scored = [pair for pair in scored if pair[0] >= MIN_SCORE]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

# ---- Initialize session state keys safely ----
if "completed_steps" not in st.session_state:
    st.session_state.completed_steps = set()
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "active_step" not in st.session_state:
    st.session_state.active_step = 1
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of tuples ("user"|"bot", message)
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "config"
if "openai_api_key" not in st.session_state:
    st.session_state.openai_api_key = ""
if "selected_sample_q" not in st.session_state:
    st.session_state.selected_sample_q = None
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "text": "Welcome to DocuBot Studio! Ask me anything about your uploaded documents."}
    ]
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "last_topk" not in st.session_state:
    st.session_state.last_topk = []
if "last_question" not in st.session_state:
    st.session_state.last_question = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""
if "demo_domain" not in st.session_state:
    st.session_state.demo_domain = ""
if "retrieval_backend" not in st.session_state:
    st.session_state.retrieval_backend = "vector"  # 'vector' or 'lexical'
if "embedding_model_name" not in st.session_state:
    st.session_state.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []  # list of {name, pages}

# ---- UI: Header ----
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.markdown(f"<h1 style='margin:0'>{PAGE_TITLE}</h1>", unsafe_allow_html=True)
with header_col2:
    st.write("")  # keep layout similar to your header (can add logos / status)

st.markdown("---")

# ---- Layout: left navigation + main content ----
nav_col, main_col = st.columns([1, 3])

# ---- Sidebar: info only (API key is handled in Step 1) ----
with st.sidebar:
    st.markdown("## DocuBot Studio — Info")
    st.info("API key is entered in Step 1 → 'LLM API Key (session only)'.")

with nav_col:
    st.markdown("### Configuration Steps (8)")
    # Show clickable step list
    for step in STEPS:
        step_id = step["id"]
        is_complete = step_id in st.session_state.completed_steps
        label = f"{'✅' if is_complete else '◌'}  {step_id}. {step['title']}"
        # Render a button per step to switch
        if st.button(label, key=f"nav_step_{step_id}"):
            st.session_state.active_step = step_id
            # keep page stable on click
            st.rerun()

with main_col:
    active = st.session_state.active_step
    step_meta = STEPS[active - 1]
    st.header(f"Step {active} — {step_meta['title']}")
    # Tabs for Overview / Metrics / Configuration
    tabs = st.tabs(["Overview", "Metrics", "Configuration"])
    # ---- Overview tab content ----
    with tabs[0]:
        overviews = {
            1: "The foundational step of any RAG system. Upload your PDFs to begin.",
            2: "Chunking splits documents into pieces; preview ensures semantic boundaries.",
            3: "Embeddings map chunks into vectors. Choose a model balancing accuracy/latency.",
            4: "Build a vector index (FAISS/HNSW) and choose retrieval params (k, threshold).",
            5: "Design prompt templates and pick the LLM used for generation.",
            6: "Optional fine-tuning experiments to improve domain accuracy.",
            7: "Run verifiability checks (hallucination rate, groundedness).",
            8: "Deploy/launch chatbot UI for interactive queries."
        }
        st.info(overviews.get(active, "Overview not found."))

    # ---- Metrics tab content (simulated charts) ----
    with tabs[1]:
        if active == 1:
            st.subheader("Upload — Simulated Intake Metrics")
            chunk_count = len(st.session_state.get("chunks", []))
            pages_est = max(1, chunk_count // 5) if chunk_count else 0
            labels = ["Uploads", "Pages (est)", "Chunks"]
            datasets = [
                {"label": "Counts", "data": [1 if chunk_count else 0, pages_est, chunk_count], "type": "bar"},
            ]
            render_chartjs("upload_metrics", labels, datasets, height=300)
        elif active == 2:
            st.subheader("Chunking — Simulated Impact")
            chunk_size = st.slider("Simulated Chunk Size (tokens)", 100, 1000, 400, step=50, key="chunk_size_slider")
            total_chunks = max(1, 1500000 // chunk_size)
            context_score = max(1, 15000 // chunk_size)
            labels = ["Total Chunks", "Retrieval Context (proxy)"]
            datasets = [
                {"label": "Values", "data": [total_chunks, context_score], "type": "bar"},
            ]
            render_chartjs("chunking_chart", labels, datasets, height=300)
        elif active == 3:
            st.subheader("Embeddings — Accuracy vs Latency (simulated)")
            labels = ["MiniLM-L6-v2", "BGE-Base-v1.5", "e5-Large-v2"]
            datasets = [
                {"label": "Accuracy (%)", "data": [75, 82, 82.5], "type": "line", "yAxisID": "A"},
                {"label": "Latency (ms)", "data": [50, 150, 250], "type": "line", "yAxisID": "B"},
            ]
            render_chartjs("model_chart", labels, datasets, height=300)
        elif active == 4:
            st.subheader("Retrieval — Top‑K and Threshold (simulated)")
            labels = ["k=1", "k=3", "k=5", "k=10"]
            datasets = [
                {"label": "Recall proxy (%)", "data": [55, 72, 80, 88], "type": "bar"},
            ]
            render_chartjs("retrieval_chart", labels, datasets, height=300)
        elif active == 5:
            st.subheader("Prompt/LLM — Cost per 1K tokens (simulated)")
            labels = ["Gemini 2.5 Flash", "Gemini 2.5 Pro"]
            datasets = [
                {"label": "USD ($)", "data": [0.0005, 0.0035], "type": "bar"},
            ]
            render_chartjs("llm_cost_chart", labels, datasets, height=300)
        elif active == 6:
            st.subheader("Fine‑Tuning — Eval vs Epochs (simulated)")
            labels = ["1", "2", "3", "4"]
            datasets = [
                {"label": "Eval F1 (%)", "data": [68, 74, 78, 79], "type": "line"},
            ]
            render_chartjs("ft_chart", labels, datasets, height=300)
        elif active == 7:
            st.subheader("Verifiability — Groundedness vs Hallucination (simulated)")
            labels = ["Groundedness", "Hallucination"]
            datasets = [
                {"label": "Rate (%)", "data": [90, 10], "type": "bar"},
            ]
            render_chartjs("verify_chart", labels, datasets, height=300)
        elif active == 8:
            st.subheader("Chat — Usage & Latency (simulated)")
            labels = ["Avg Turns/Session", "Avg Response (ms)"]
            datasets = [
                {"label": "Values", "data": [7, 320], "type": "bar"},
            ]
            render_chartjs("chat_metrics", labels, datasets, height=300)

    # ---- Configuration tab content ----
    with tabs[2]:
        st.subheader("Configuration")
        if active == 1:
            st.write("Enter your LLM API key below (session-only). If provided, Step 8 can call your LLM; otherwise answers are extractive.")
            api_key_input = st.text_input("LLM API Key (session only)", type="password", value=st.session_state.api_key, key="api_key_widget")
            if api_key_input:
                st.session_state.api_key = api_key_input.strip()
            st.markdown("---")
            # Advanced: retrieval backend and model selection
            with st.expander("Advanced settings", expanded=False):
                backend_choice = st.selectbox(
                    "Retrieval backend",
                    ["Vector (embeddings + FAISS)", "Lexical (no embeddings)"],
                    index=0 if st.session_state.retrieval_backend == "vector" else 1,
                )
                st.session_state.retrieval_backend = "vector" if backend_choice.startswith("Vector") else "lexical"
                if st.session_state.retrieval_backend == "vector":
                    model_choice = st.selectbox(
                        "Embedding model",
                        [
                            "sentence-transformers/all-MiniLM-L6-v2",
                            "sentence-transformers/paraphrase-MiniLM-L3-v2",
                        ],
                        index=0 if st.session_state.embedding_model_name == "sentence-transformers/all-MiniLM-L6-v2" else 1,
                    )
                    st.session_state.embedding_model_name = model_choice
            st.subheader("Upload & Parse PDFs")
            colu1, colu2 = st.columns(2)
            with colu1:
                chunk_size = st.number_input("Chunk size (chars)", min_value=300, max_value=2000, value=800, step=50, key="chunk_size_input")
            with colu2:
                overlap = st.number_input("Overlap (chars)", min_value=0, max_value=400, value=120, step=10, key="chunk_overlap_input")
            uploaded = st.file_uploader("Upload PDF(s)", accept_multiple_files=True, type=["pdf"])
            # Show previously processed files, if any
            if st.session_state.get("processed_files"):
                files = st.session_state.processed_files
                total_pages = sum(f.get("pages", 0) for f in files)
                total_chunks = len(st.session_state.get("chunks", []))
                with st.expander("Previously processed files", expanded=True):
                    st.markdown(f"**Files:** {len(files)} | **Pages:** {total_pages} | **Chunks:** {total_chunks}")
                    for f in files:
                        st.markdown(f"- {f.get('name','unknown')} — {f.get('pages',0)} page(s)")
                    def _clear_processed():
                        st.session_state.processed_files = []
                    st.button("Clear list (keep data)", on_click=_clear_processed, key="clear_processed_files")
            if uploaded and HAS_PDF:
                if st.button("Process PDFs", key="process_pdfs"):
                    # 1) Parse & chunk
                    with st.spinner("Parsing and chunking PDFs..."):
                        pages = parse_pdfs(uploaded)
                        chunks = build_chunks(pages, int(chunk_size), int(overlap))
                        # drop empty/very short chunks
                        filtered = [c for c in chunks if c.get("text") and len(c.get("text")) > 20]
                        st.session_state.chunks = filtered
                        st.session_state.embeddings = None
                        st.session_state.index = None
                    # Build and persist processed file summary
                    file_pages = {}
                    for p in pages:
                        src = p.get("source", "uploaded")
                        file_pages[src] = file_pages.get(src, 0) + 1
                    st.session_state.processed_files = [
                        {"name": name, "pages": count} for name, count in sorted(file_pages.items())
                    ]
                    st.success(f"Processed {sum(file_pages.values())} pages → {len(filtered)} chunks (removed {len(chunks)-len(filtered)} empty/short).")
                    with st.expander("Preview first 5 chunks", expanded=False):
                        for i, ch in enumerate(st.session_state.chunks[:5], start=1):
                            meta = f"{ch.get('source','uploaded')} p.{ch.get('page','-')}"
                            st.markdown(f"{i}. {meta}")
                            st.write(ch.get("text", "")[:400])
                    with st.expander("Preview first 5 chunks", expanded=False):
                        for i, ch in enumerate(st.session_state.chunks[:5], start=1):
                            meta = f"{ch.get('source','uploaded')} p.{ch.get('page','-')}"
                            st.markdown(f"{i}. {meta}")
                            st.write(ch.get("text", "")[:400])

                    # 2) Compute embeddings
                    if st.session_state.chunks:
                        with st.spinner("Computing embeddings..."):
                            texts = [c["text"] for c in st.session_state.chunks]
                            try:
                                embs = compute_embeddings(texts)
                            except Exception as e:
                                st.error(f"Embedding computation failed: {e}. Falling back to lexical retrieval only.")
                                embs = None
                            st.session_state.embeddings = embs
                    # 3) Build index
                    if st.session_state.get("embeddings") is not None:
                        with st.spinner("Building index..."):
                            st.session_state.index = build_index(st.session_state.embeddings)
                    # 4) Mark steps 1–7 complete and launch chat
                    for s_id in range(1, 8):
                        st.session_state.completed_steps.add(s_id)
                    st.session_state.active_step = 8
                    st.session_state.app_mode = "chat"
                    st.success("Auto-configuration complete. Launching chat…")
                    st.rerun()
            elif uploaded and not HAS_PDF:
                st.error("PDF parsing dependency not available. Please install pypdf.")
        elif active == 2:
            st.write("Chunking strategy: Recursive character splitting.")
            chs = st.session_state.get("chunks", [])
            st.info(f"Chunks available: {len(chs)}")
            if chs:
                cols = st.columns([2,2,1])
                with cols[0]:
                    page_size = st.selectbox("Preview page size", [5, 10, 20, 50], index=0, key="chunk_preview_ps")
                with cols[1]:
                    start = st.number_input("Start index (1-based)", min_value=1, max_value=max(1, len(chs)), value=1, step=int(page_size), key="chunk_preview_start")
                with cols[2]:
                    st.write("")
                start_idx = int(start) - 1
                end_idx = min(len(chs), start_idx + int(page_size))
                with st.expander(f"Showing chunks {start_idx+1}–{end_idx} of {len(chs)}", expanded=True):
                    for i in range(start_idx, end_idx):
                        ch = chs[i]
                        meta = f"{ch.get('source','uploaded')} p.{ch.get('page','-')}"
                        st.markdown(f"**#{i+1}** — {meta}")
                        st.write((ch.get('text','') or '')[:800])
                        st.markdown("---")
            if st.button("Mark Step 2 Complete", key="complete2"):
                st.session_state.completed_steps.add(2)
                st.success("Step 2 marked complete.")
        elif active == 3:
            st.write("Compute embeddings for your chunks (CPU, local). Model: all-MiniLM-L6-v2.")
            if not st.session_state.get("chunks"):
                st.warning("No chunks found. Upload and process PDFs in Step 1 first, or load a demo dataset.")
            else:
                if st.button("Compute embeddings", key="compute_embs"):
                    with st.spinner("Computing embeddings..."):
                        texts = [c["text"] for c in st.session_state.chunks]
                        embs = compute_embeddings(texts)
                        st.session_state.embeddings = embs
                        st.session_state.embedding_model_name = st.session_state.get("embedding_model_name", "sentence-transformers/all-MiniLM-L6-v2")
                        st.session_state.index = None
                    st.success(f"Computed embeddings: shape {embs.shape}")
            if st.button("Mark Step 3 Complete", key="complete3"):
                st.session_state.completed_steps.add(3)
                st.success("Step 3 marked complete.")
        elif active == 4:
            st.write("Build a vector index and test retrieval.")
            if st.session_state.get("embeddings") is not None and st.session_state.get("index") is None:
                if st.button("Build index", key="build_index_btn"):
                    with st.spinner("Building index..."):
                        st.session_state.index = build_index(st.session_state.embeddings)
                    st.success("Index built.")
            elif st.session_state.get("index") is not None:
                st.info("Index already built.")
            else:
                st.warning("Compute embeddings in Step 3 first.")

            st.markdown("**Try a retrieval test**: pick a sample question or type your own, then run.")
            SAMPLE_QUERIES = [
                "What are the main airline baggage size rules in the uploaded documents?",
                "Summarize the cancellation & refund policy.",
                "List the safety protocols described for COVID response.",
                "What steps are required to issue a full refund?",
                "Explain how to change a flight within 24 hours of booking.",
                "Extract the penalty fees for missed connections.",
                "Which section covers passenger liabilities?",
                "Give a step-by-step on how to claim lost baggage.",
                "Describe the loyalty program rules for upgrades.",
                "What are the contact channels for customer support?",
            ]
            choice = st.selectbox(
                "Pick a sample test query (or choose 'Other')",
                options=["-- choose sample question --"] + SAMPLE_QUERIES + ["Other (type custom question below)"]
            )
            custom_q = ""
            if choice == "Other (type custom question below)":
                custom_q = st.text_input("Type your test question here", key="custom_test_q")
            elif choice and choice != "-- choose sample question --":
                custom_q = choice
            if st.button("Run retrieval test (Step 4)", key="run_retrieval_test"):
                if not custom_q:
                    st.warning("Pick or type a question first.")
                else:
                    retrieved_scored = search_topk(custom_q, k=5)
                    if not retrieved_scored:
                        st.info("No results. Ensure chunks/embeddings/index are prepared or lower the threshold.")
                    else:
                        with st.expander("Retrieved chunks (top-5)", expanded=True):
                            for i, (sc, ch) in enumerate(retrieved_scored, start=1):
                                meta = f"{ch.get('source','uploaded')} p.{ch.get('page','-')}"
                                st.markdown(f"{i}. **Score:** {sc:.4f} | {meta}")
                                st.write(ch.get("text", ""))
            if st.button("Mark Step 4 Complete", key="complete4"):
                st.session_state.completed_steps.add(4)
                st.success("Step 4 marked complete.")
        elif active == 5:
            st.write("Prompt template: Grounded Answer Template V3 (simulated). LLM: Gemini 2.5 Flash.")
            if st.button("Mark Step 5 Complete", key="complete5"):
                st.session_state.completed_steps.add(5)
                st.success("Step 5 marked complete.")
        elif active == 6:
            st.write("Fine-tuning experiments: completed (simulated).")
            if st.button("Mark Step 6 Complete", key="complete6"):
                st.session_state.completed_steps.add(6)
                st.success("Step 6 marked complete.")
        elif active == 7:
            st.write("Verifiability checks: Groundedness score = 90% (simulated).")
            if st.button("Mark Step 7 Complete", key="complete7"):
                st.session_state.completed_steps.add(7)
                st.success("Step 7 marked complete.")
        elif active == 8:
            if st.session_state.app_mode != "chat":
                st.write("All config steps are ready for launch.")
                col1, col2 = st.columns([3, 1])
                with col1:
                    app_name = st.text_input("Application name", value="DocuBot Studio", key="app_name_widget")
                    tagline = st.text_input("Tagline", value="Your intelligent workspace for turning documents into chatbots.", key="tagline_widget")
                    st.session_state.app_title = app_name
                    st.session_state.app_tagline = tagline
                with col2:
                    if st.button("Launch Chatbot UI", key="launch_chat_button"):
                        for s in range(1, 8):
                            st.session_state.completed_steps.add(s)
                        st.session_state.completed_steps.add(8)
                        st.session_state.app_mode = "chat"
                        st.success("Launching chat view…")
                        st.rerun()
            else:
                # Single-window Chat UI using messages store and callbacks
                st.header(st.session_state.get("app_title", "DocuBot Studio"))
                st.caption(st.session_state.get("app_tagline", ""))
                # Banners about retrieval mode/availability
                if st.session_state.get("retrieval_backend") == "lexical":
                    st.info("Retrieval backend: Lexical (embeddings disabled).")
                elif not (st.session_state.get("embeddings") is not None and st.session_state.get("index") is not None):
                    st.warning("Vector search unavailable — using lexical fallback.")

                # Dataset status quick view
                chs = st.session_state.get("chunks", [])
                emb_ok = st.session_state.get("embeddings") is not None
                idx_ok = st.session_state.get("index") is not None
                with st.expander("Dataset status", expanded=False):
                    st.write({
                        "chunks": len(chs),
                        "embeddings": bool(emb_ok),
                        "index": bool(idx_ok),
                        "model": st.session_state.get("embedding_model_name")
                    })
                    # Show processed files summary if available
                    files = st.session_state.get("processed_files", [])
                    if files:
                        st.markdown("**Processed files**")
                        total_pages = sum(f.get("pages", 0) for f in files)
                        st.markdown(f"Files: {len(files)} | Pages: {total_pages}")
                        for f in files:
                            st.markdown(f"- {f.get('name','unknown')} — {f.get('pages',0)} page(s)")
                    if chs:
                        st.markdown("Preview first 3 chunks:")
                        for i, ch in enumerate(chs[:3], start=1):
                            meta = f"{ch.get('source','uploaded')} p.{ch.get('page','-')}"
                            st.markdown(f"**#{i}** — {meta}")
                            st.write((ch.get('text','') or '')[:400])

                # helper: simulated response using retrieval context (replace with real backend)
                PROMPT_HEADER = (
                    "You are a helpful assistant that must answer the user's question using ONLY the provided document snippets. "
                    "If the answer cannot be found, say 'I couldn't find a clear answer in the provided documents.'\n\n"
                )

                def build_prompt_with_snippets(question: str, top_chunks):
                    ctx_blocks = []
                    for i, (score, ch) in enumerate(top_chunks, 1):
                        idx = ch.get("id", i)
                        page = ch.get("page", "-")
                        raw = ch.get("text", "")
                        snippet = _clean(raw)[:700]
                        ctx_blocks.append(f"Snippet {i} (idx={idx}, score={score:.4f}, page={page}):\n{snippet}\n")
                    ctx_text = "\n---\n".join(ctx_blocks) if ctx_blocks else "(no snippets)"
                    prompt = (
                        PROMPT_HEADER +
                        "CONTEXT (top retrieved snippets):\n" + ctx_text + "\n\n" +
                        "QUESTION:\n" + question + "\n\n" +
                        "INSTRUCTION: Provide a concise answer grounded ONLY in the CONTEXT. Then, list sources as 'Sources: idx=X (page Y)'.\n"
                    )
                    return prompt

                def _clean(txt: str) -> str:
                    # Collapse excessive newlines and spaces for neat rendering
                    return "\n".join([" ".join(line.split()) for line in txt.splitlines() if line.strip()])

                def generate_response_simulated(question: str, top_chunks):
                    if not top_chunks:
                        return "I couldn't find a clear answer in the provided documents."
                    # Use up to 3 snippets
                    raw_snips = [ch.get("text", "") for _s, ch in top_chunks[:3]]
                    snips = [_clean(s) for s in raw_snips if s]
                    # Heuristic: pick first 2-3 sentences as the concise answer
                    joined = " ".join(snips)
                    sentences = [s.strip() for s in joined.replace("•", " ").split('.') if s.strip()]
                    answer = ". ".join(sentences[:3])
                    # Extract concise key points
                    key_points = []
                    for s in snips:
                        # prefer semicolon/dot separated phrases of reasonable length
                        for cand in [p.strip() for p in s.replace("\n", " ").split('.')]:
                            if 6 <= len(cand) <= 140:
                                key_points.append(cand)
                            if len(key_points) >= 5:
                                break
                        if len(key_points) >= 5:
                            break
                    key_points = key_points[:5]
                    # Sources
                    sources = ", ".join([f"idx={ch.get('id', i+1)} (p={ch.get('page','-')})" for i, (_s, ch) in enumerate(top_chunks[:3])])
                    # Structured Markdown
                    out = [
                        "**Answer**",
                        answer or snips[0][:300],
                    ]
                    if key_points:
                        out.append("\n**Key points**")
                        out.extend([f"- {kp}" for kp in key_points])
                    out.append(f"\n**Sources**: {sources}")
                    return "\n".join(out)

                # callback for Send button
                def submit_chat():
                    if st.session_state.get("is_generating", False):
                        return
                    user_q = st.session_state["chat_input"].strip()
                    if not user_q:
                        return
                    st.session_state.is_generating = True
                    st.session_state["messages"].append({"role": "user", "text": user_q})
                    st.session_state["chat_input"] = ""  # allowed inside callback
                    # Retrieve and build prompt
                    topk_scored = search_topk(user_q, k=5)
                    st.session_state.last_topk = topk_scored
                    st.session_state.last_question = user_q
                    _prompt = build_prompt_with_snippets(user_q, topk_scored)
                    # Simulated generation
                    resp = generate_response_simulated(user_q, topk_scored)
                    st.session_state.last_answer = resp
                    st.session_state["messages"].append({"role": "assistant", "text": resp})
                    st.session_state.is_generating = False

                # render messages
                use_chat_api = hasattr(st, "chat_message")
                for m in st.session_state["messages"]:
                    if use_chat_api:
                        with st.chat_message(m["role"]):
                            st.write(m["text"])
                    else:
                        if m["role"] == "user":
                            st.markdown(f"**You:** {m['text']}")
                        elif m["role"] == "assistant":
                            st.markdown(f"**Bot:** {m['text']}")
                        else:
                            st.info(m["text"])

                # Show diagnostics if no hits
                if not st.session_state.last_topk and st.session_state.last_question:
                    ch_n = len(st.session_state.get("chunks", []))
                    has_emb = st.session_state.get("embeddings") is not None
                    has_idx = st.session_state.get("index") is not None
                    st.warning(f"No relevant snippets retrieved. Diagnostics — chunks: {ch_n}, embeddings: {has_emb}, index: {has_idx}. Try re-processing PDFs in Step 1 or re-running Steps 3–4.")

                # Show latest top-K under a collapsible panel
                if st.session_state.last_topk:
                    with st.expander("Top retrieved chunks (last question)", expanded=True):
                        for i, (sc, ch) in enumerate(st.session_state.last_topk, start=1):
                            idx = ch.get("id", i)
                            page = ch.get("page", "-")
                            st.markdown(f"{i}. **idx={idx}** | **score={sc:.4f}** | page={page}")
                            snip = _clean(ch.get("text", ""))[:1000]
                            st.write(snip)

                cols = st.columns([8, 1, 1])
                with cols[0]:
                    st.text_input("Type your question", key="chat_input", placeholder="Ask me anything about the uploaded docs…")
                with cols[1]:
                    st.button("Send", on_click=submit_chat, key="chat_send_inline")
                with cols[2]:
                    def reset_chat():
                        st.session_state["messages"] = [{"role": "system", "text": "Welcome to DocuBot Studio! Ask me anything about your uploaded documents."}]
                        st.session_state["chat_input"] = ""
                    st.button("Reset chat", on_click=reset_chat, key="chat_reset_inline")


# ---- Footer: quick status ----
st.markdown("---")
completed = sorted(list(st.session_state.completed_steps))
st.write(f"Completed steps: {completed if completed else 'none'}")
st.write("Note: This is a demo-native Streamlit implementation that simulates the full flow. Replace simulation blocks with your actual backend (embedding, FAISS, LLM calls).")
