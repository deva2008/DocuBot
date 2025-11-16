# Entry point for Streamlit Cloud
# Delegates to the main app implementation, with a minimal debug mode.

import streamlit as st

# Minimal mode to isolate file uploader behavior on Streamlit Cloud.
# Visit: https://<app>/?minimal=1
def _run_minimal():
    st.set_page_config(page_title="DocuBot Minimal Uploader Test", layout="centered")
    st.title("Minimal Uploader Test")
    st.caption("Use this page to test the file dialog on Streamlit Cloud.")
    files = st.file_uploader("Upload PDF(s)", type=["pdf"], accept_multiple_files=True)
    if files:
        st.success(f"Selected {len(files)} file(s): {[f.name for f in files]}")

params = {}
try:
    # Streamlit >=1.30
    params = {k: v for k, v in st.query_params.items()}
except Exception:
    try:
        # Older API
        params = st.experimental_get_query_params()
    except Exception:
        params = {}

min_flag = str(params.get("minimal", ["0"][0] if isinstance(params.get("minimal"), list) else params.get("minimal", "0"))).lower()
if min_flag in ("1", "true", "yes"):  # Minimal test mode
    _run_minimal()
else:
    # Load the full application
    import app_steps_patch  # noqa: F401
