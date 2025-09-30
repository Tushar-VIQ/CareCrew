# mcp_server_kb.py - Exposes RAG Knowledge Base lookup as an MCP Tool on port 8002

import uvicorn
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Dict

# --- Import core logic from data_analyze.py ---
from data_analyze import rag_lookup_kb
# -----------------------------------------------

# Define the output structure for the LLM
class KBLookupOutput(BaseModel):
    """Structured data returned after searching the internal Knowledge Base (STG)."""
    guideline_snippets: List[str] = Field(description="A list of up to 4 highly relevant text passages from the medical guidelines.")
    query_used: str = Field(description="The clinical query used for retrieval.")

# Initialize the MCP Server
mcp = FastMCP("STG_Knowledge_Base", port=8002)

@mcp.tool()
def search_medical_guidelines(query: str = Field(description="The key clinical finding or diagnostic question to search the Standard Treatment Guidelines (STG) for.")) -> KBLookupOutput:
    """
    Performs a deep semantic search against the internal Standard Treatment Guidelines (STG)
    to retrieve evidence-based passages relevant to the diagnosis or treatment plan.
    """
    # Call the underlying RAG logic function from data_analyze.py
    hits = rag_lookup_kb(query, top_k=4)
    
    # Extract just the passage text for the final output
    snippets = [h['passage'] for h in hits]
    
    return KBLookupOutput(
        guideline_snippets=snippets,
        query_used=query
    )

if __name__ == "__main__":
    print("--- Starting KB RAG MCP Server on port 8002 ---")
    # --- CRITICAL FIX: Use the FastMCP built-in .run() method ---
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8002)
    # -----------------------------------------------------------
