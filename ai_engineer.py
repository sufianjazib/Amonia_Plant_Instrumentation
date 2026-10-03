import os
import json
import streamlit as st

GROQ_MODEL = "llama-3.3-70b-versatile"

def get_groq_client():
    api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key or api_key.startswith("gsk_YourActual"):
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception:
        return None


def run_ai_diagnostics(instruments: dict, controllers: dict, alarms: list, active_faults: dict, process_state: dict) -> str:
    client = get_groq_client()
    if not client:
        return """### ⚠️ AI Service Unavailable
**Groq API Key is missing or invalid.**

Please configure your Groq API Key in Streamlit secrets:
1. Open `.streamlit/secrets.toml` locally, OR
2. Go to **Streamlit Cloud -> App Settings -> Secrets** and add:
```toml
GROQ_API_KEY = "gsk_your_groq_api_key_here"
