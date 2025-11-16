# Environment Setup Guide

## Local Development

### Step 1: Create .env file

Create a `.env` file in the project root with the following variables:

```bash
# OpenAI API Key (required for LLM features)
# Get your key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-actual-key-here

# Embedding Model (optional, defaults to sentence-transformers/all-MiniLM-L6-v2)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# LLM Model (optional, defaults to gpt-4o-mini)
LLM_MODEL=gpt-4o-mini

# Chroma Vector DB Directory (optional, defaults to ./Airlines_QA_Bot/data/embeddings/chroma)
CHROMA_DIR=./data/embeddings/chroma
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run Locally

```bash
streamlit run streamlit_app.py
```

---

## Streamlit Cloud Deployment

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Add environment variables and error handling"
git push origin main
```

**Note:** Do NOT commit `.env` file (it's in `.gitignore`)

### Step 2: Add Secrets to Streamlit Cloud

1. Go to https://share.streamlit.io
2. Click your **DocuBot Studio** app
3. Click **Settings** (gear icon)
4. Click **Secrets**
5. Add the following:

```
OPENAI_API_KEY = "sk-your-actual-key"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "gpt-4o-mini"
CHROMA_DIR = "./data/embeddings/chroma"
```

6. Click **Save**
7. The app will automatically redeploy

---

## Getting OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click **Create new secret key**
4. Copy the key (you won't be able to see it again)
5. Paste it into `.env` (local) or Streamlit Secrets (cloud)

---

## Verifying Setup

After setting up environment variables:

1. Run the app: `streamlit run streamlit_app.py`
2. Upload a PDF file
3. Click "Build Index"
4. You should see: ✅ Index built from uploaded PDFs.
5. If you see an error, check the console for details

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "OPENAI_API_KEY not configured" warning | Add OPENAI_API_KEY to .env or Streamlit Secrets |
| Upload redirects to blank page | Check browser console (F12) for error messages |
| "Module not found" error | Run `pip install -r requirements.txt` |
| Streamlit app won't start | Check that Python 3.8+ is installed |

