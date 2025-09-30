# data_analyze.py: The central utility file (Updated fallback for MCP compatibility)

import os
import re
import pickle
import base64
import fitz
import requests
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import faiss
from groq import Groq

# -------------------------
# Groq credentials
# -------------------------

import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
client = Groq(api_key=GROQ_API_KEY) 

# -------------------------
# KB settings
# -------------------------
STG_PDF = "standard-treatment-guidelines.pdf"
KB_INDEX_PICKLE = "kb_index.pkl"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
KB_EMBEDDER = SentenceTransformer(EMBED_MODEL_NAME)
RAG_EMBEDDER = SentenceTransformer(EMBED_MODEL_NAME)
kb_index_data = None

# -------------------------
# OpenFDA
# -------------------------
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# -------------------------
# Utilities
# -------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Helper to safely extract text from a PDF file."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"{pdf_path} not found")
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc])

def file_to_base64(file_path: str):
    """Helper to convert a file to a Base64 string for multimodal input."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Helper to split long text into manageable chunks for RAG indexing."""
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks

def get_openfda_warnings(drug_name: str):
    """
    Searches the OpenFDA database for safety warnings. Returns a structured dictionary.
    FIXED to return ALL Pydantic fields on failure.
    """
    try:
        for key in ["brand_name", "generic_name"]:
            params = {"search": f"openfda.{key}:{drug_name}", "limit": 1}
            resp = requests.get(OPENFDA_BASE, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("results", [])
                if data:
                    entry = data[0]
                    return {
                        "drug_name": drug_name,
                        "brand": entry.get("openfda", {}).get("brand_name", ["N/A"])[0],
                        "generic": entry.get("openfda", {}).get("generic_name", ["N/A"])[0],
                        "warnings": entry.get("warnings", ["No warnings available"])[0],
                        "found": True # Indicate success
                    }
    except Exception:
        pass
    
    # --- FIX: Ensure ALL required Pydantic fields are returned on failure ---
    return {
        "drug_name": drug_name, 
        "brand": "N/A",
        "generic": "N/A",
        "warnings": "No data found due to search or network error.", 
        "found": False # Indicate failure
    }
    # -----------------------------------------------------------------------

# -------------------------
# KB RAG
# -------------------------
def build_kb_index(pdf_path: str = STG_PDF, out_pickle: str = KB_INDEX_PICKLE):
    # ... (RAG/FAISS logic remains the same)
    print(f"Building KB (STG) index from PDF: {pdf_path}...")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Cannot build KB index. PDF file not found at: {pdf_path}")
        
    text = extract_text_from_pdf(pdf_path)
    text = re.sub(r"\n{2,}", "\n", text)
    passages = chunk_text(text, chunk_size=300, overlap=50)
    embeddings = KB_EMBEDDER.encode(passages, convert_to_numpy=True, show_progress_bar=True)
    if embeddings.dtype != np.float32:
        embeddings = embeddings.astype(np.float32)
        
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    with open(out_pickle, "wb") as f:
        pickle.dump({"index": index, "passages": passages}, f)
    print(f"✅ Built KB index with {len(passages)} passages and saved to {out_pickle}")
    return {"index": index, "passages": passages}

def load_kb_index(pickle_path: str = KB_INDEX_PICKLE):
    if not os.path.exists(pickle_path):
        return None
    with open(pickle_path, "rb") as f:
        return pickle.load(f)

def ensure_kb_index():
    global kb_index_data
    if kb_index_data is None:
        data = load_kb_index(KB_INDEX_PICKLE)
        if data is None:
            if os.path.exists(STG_PDF):
                data = build_kb_index(STG_PDF, KB_INDEX_PICKLE)
            else:
                print(f"WARNING: Standard Treatment Guidelines PDF ({STG_PDF}) not found. RAG will not work.")
                return None
        kb_index_data = data
    return kb_index_data

def rag_lookup_kb(query: str, top_k: int = 4) -> List[Dict[str,str]]:
    """Performs semantic search against the FAISS index."""
    kb_data = ensure_kb_index()
    if kb_data is None:
        return []
        
    emb = RAG_EMBEDDER.encode([query], convert_to_numpy=True)
    if emb.dtype != np.float32:
        emb = emb.astype(np.float32)
    
    D, I = kb_data["index"].search(emb, top_k)
    results = []
    for idx in I[0]:
        if idx >= 0 and idx < len(kb_index_data["passages"]):
            results.append({"passage": kb_index_data["passages"][idx], "score": float(D[0][list(I[0]).index(idx)])})
    return results

ensure_kb_index()

# -------------------------
# OLD ORCHESTRATOR REMOVED
# -------------------------
