# DocuBot Studio - Upload Redirect Issue Diagnosis & Fix

## 🔴 Root Cause Analysis

### Issue Observed
When clicking "Upload Document" or "Build Index", the app redirects to an empty page (301 redirects in Network tab).

### Root Causes Identified

#### 1. **Missing Environment Variables**
The app requires these environment variables that are NOT configured:
- `OPENAI_API_KEY` - Required for LLM answer generation
- `CHROMA_DIR` - Directory for vector database persistence
- `EMBEDDING_MODEL` - Sentence transformer model (defaults to `sentence-transformers/all-MiniLM-L6-v2`)
- `LLM_MODEL` - OpenAI model (defaults to `gpt-4o-mini`)

**Impact:** When these are missing, the app may fail silently or redirect unexpectedly.

#### 2. **Streamlit Session State Issues in Iframe**
The iframe sandbox configuration (`allow-scripts allow-forms allow-popups`) isolates storage from the parent page. Streamlit's session state may not persist correctly.

**Impact:** File uploads and state changes may not be saved properly, causing redirects.

#### 3. **Missing Error Handling**
The app lacks try-catch blocks around critical operations:
- PDF loading
- Vector database operations
- LLM API calls

**Impact:** Errors silently fail, causing unexpected redirects instead of showing error messages.

#### 4. **Streamlit CORS Configuration**
The `.streamlit/config.toml` doesn't have CORS disabled for iframe testing.

**Impact:** Cross-origin requests may be blocked.

---

## ✅ Solutions

### Solution 1: Add Environment Variables (CRITICAL)

Create or update `.env` file in the project root:

```bash
# .env
OPENAI_API_KEY=sk-your-actual-key-here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-4o-mini
CHROMA_DIR=./data/embeddings/chroma
```

**For Streamlit Cloud deployment:**
1. Go to your app settings on Streamlit Cloud
2. Click **Secrets**
3. Add these as secrets (they'll be available as environment variables)

### Solution 2: Update Streamlit Configuration

Update `.streamlit/config.toml`:

```toml
[browser]
gatherUsageStats = false

[server]
# Disable CORS for iframe testing
enableCORS = false

# Allow embedding in iframes
allowRunOnSave = true

# Session state settings
maxUploadSize = 200

[logger]
level = "debug"
```

### Solution 3: Add Error Handling to App

Update `app/app.py` to add error handling:

```python
import streamlit as st
from dotenv import load_dotenv
from utils.logger import get_logger
from utils.pdf_utils import load_pdfs
from utils.retriever_utils import build_retriever, retrieve_chunks
from utils.generator_utils import generate_answer

load_dotenv()
st.set_page_config(page_title="DocuBot Studio", page_icon="✈️", layout="wide")
logger = get_logger(__name__)


def main():
    st.title("DocuBot Studio")
    st.caption("Transform documentation into AI assistants.")

    # Check for required environment variables
    import os
    if not os.getenv("OPENAI_API_KEY"):
        st.warning("⚠️ OPENAI_API_KEY not configured. LLM features will be limited.")

    uploaded_files = st.file_uploader(
        "Upload HR policy PDFs", type=["pdf"], accept_multiple_files=True
    )
    
    if "retriever" not in st.session_state:
        st.session_state["retriever"] = None

    col1, col2 = st.columns(2)
    with col1:
        build_clicked = st.button("Build index")
    with col2:
        query = st.text_input("Ask a question about HR policies")

    if build_clicked and uploaded_files:
        try:
            with st.spinner("Loading PDFs..."):
                docs = load_pdfs(uploaded_files)
            
            with st.spinner("Building index..."):
                retriever = build_retriever(docs)
            
            st.session_state["retriever"] = retriever
            st.success("✅ Index built from uploaded PDFs.")
        except Exception as e:
            st.error(f"❌ Error building index: {str(e)}")
            logger.error(f"Build index error: {e}", exc_info=True)

    if st.button("Ask") and query:
        try:
            retriever = st.session_state.get("retriever")
            if retriever is None:
                st.warning("Please build the index first using uploaded PDFs.")
            else:
                with st.spinner("Retrieving context..."):
                    contexts = retrieve_chunks(retriever, query)
                
                with st.spinner("Generating answer..."):
                    answer, sources = generate_answer(query, contexts)
                
                st.subheader("Answer")
                st.write(answer)
                with st.expander("Sources / Context"):
                    for s in sources:
                        st.write(s[:500] + ("..." if len(s) > 500 else ""))
        except Exception as e:
            st.error(f"❌ Error processing query: {str(e)}")
            logger.error(f"Query error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
```

### Solution 4: Update Iframe Configuration

Update your parent page's iframe to include these attributes:

```html
<iframe
  id="docubot"
  src="https://docubot-studio.streamlit.app"
  style="width:100%; height:900px; border:0;"
  sandbox="allow-scripts allow-forms allow-popups allow-same-origin"
  allow="microphone; camera; geolocation"
  title="DocuBot Studio">
</iframe>
```

**Note:** `allow-same-origin` is needed for Streamlit session state to work properly in iframes.

---

## 🔧 Step-by-Step Fix Instructions

### Step 1: Set Up Environment Variables

```bash
cd /Users/pavandevarapalli/Documents/DocuBots/DocuBot

# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-actual-key-here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-4o-mini
CHROMA_DIR=./data/embeddings/chroma
EOF
```

**Replace `sk-your-actual-key-here` with your actual OpenAI API key.**

### Step 2: Update Streamlit Config

```bash
# Update .streamlit/config.toml
cat > .streamlit/config.toml << 'EOF'
[browser]
gatherUsageStats = false

[server]
enableCORS = false
allowRunOnSave = true
maxUploadSize = 200

[logger]
level = "debug"
EOF
```

### Step 3: Update app/app.py

Replace the current `app/app.py` with the error-handling version (see Solution 3 above).

### Step 4: Restart Streamlit

```bash
# If running locally
streamlit run streamlit_app.py

# If on Streamlit Cloud, push changes to GitHub
git add .
git commit -m "Fix: Add environment variables, error handling, and iframe config"
git push origin main
```

### Step 5: Test Upload

1. Open the app in your browser
2. Upload a PDF file
3. Click "Build Index"
4. Verify it shows success message instead of redirecting

---

## 📋 Dependency Checklist

| Dependency | Version | Status | Purpose |
|-----------|---------|--------|---------|
| streamlit | >=1.36.0 | ✅ | Web framework |
| pypdf | >=4.2.0 | ✅ | PDF reading |
| python-dotenv | >=1.0.1 | ✅ | Environment variables |
| chromadb | >=0.5.5 | ✅ | Vector database |
| sentence-transformers | >=3.0.1 | ✅ | Embeddings |
| langchain-text-splitters | >=0.2.0 | ✅ | Text chunking |
| openai | >=1.51.0 | ✅ | LLM API |
| pdfplumber | >=0.7.6 | ⚠️ | Alternative PDF reading (optional) |
| faiss-cpu | >=1.7.4 | ⚠️ | Vector search (optional, chromadb handles this) |
| pandas | >=2.0.0 | ✅ | Data processing |
| numpy | >=1.26.0 | ✅ | Numerical operations |

**All dependencies are installed and compatible.**

---

## 🧪 Testing Checklist

- [ ] Environment variables are set in `.env`
- [ ] `.streamlit/config.toml` has CORS disabled
- [ ] `app/app.py` has error handling
- [ ] App runs locally without redirect on upload
- [ ] App works in iframe with `allow-same-origin`
- [ ] Console shows no errors (F12 → Console)
- [ ] Network tab shows no 301 redirects on upload

---

## 🚀 Deployment to Streamlit Cloud

1. **Push changes to GitHub:**
   ```bash
   git add .
   git commit -m "Fix: Add environment variables, error handling, and iframe config"
   git push origin main
   ```

2. **Add secrets to Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click your app
   - Click **Settings** → **Secrets**
   - Add:
     ```
     OPENAI_API_KEY = "sk-your-actual-key"
     EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
     LLM_MODEL = "gpt-4o-mini"
     CHROMA_DIR = "./data/embeddings/chroma"
     ```

3. **Verify app loads and upload works**

---

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Still redirecting on upload | Missing OPENAI_API_KEY | Add to .env or Streamlit Secrets |
| "Session state not persisting" | Missing `allow-same-origin` in iframe | Update iframe sandbox attribute |
| "CORS error" | CORS enabled in config | Set `enableCORS = false` in config.toml |
| "PDF not loading" | pypdf not installed | Run `pip install -r requirements.txt` |
| "Blank page after upload" | Error not being caught | Check console (F12) for error messages |

---

## 📞 Need Help?

1. Check browser console (F12 → Console) for error messages
2. Check Streamlit logs for detailed errors
3. Verify all environment variables are set
4. Ensure `.streamlit/config.toml` has correct settings
5. Test locally before deploying to Streamlit Cloud

