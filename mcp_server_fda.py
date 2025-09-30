# mcp_server_fda.py - Exposes OpenFDA API as an MCP Tool on port 8001

import uvicorn
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# --- Import core logic from data_analyze.py ---
from data_analyze import get_openfda_warnings 
# -----------------------------------------------

# Define the output structure for the LLM
class FdaWarningOutput(BaseModel):
    """Structured data returned after checking a drug against the FDA database."""
    drug_name: str = Field(description="The name of the drug checked.")
    brand: str = Field(description="The brand name found, if available.")
    generic: str = Field(description="The generic name found, if available.")
    warnings: str = Field(description="The primary safety warnings or adverse effects found in the FDA label.")
    found: bool = Field(description="True if successful data was retrieved, False otherwise.")

# Initialize the MCP Server
# NOTE: The Deprecation Warning about providing 'port' here is unavoidable for now, 
# but it doesn't stop the server.
mcp = FastMCP("FDA_Safety_Checker", port=8001)

# We rely on the Python type hint '-> FdaWarningOutput' to handle the schema definition.
@mcp.tool() 
def check_drug_safety(drug_name: str = Field(description="The exact brand or generic name of the drug to check.")) -> FdaWarningOutput:
    """
    Checks the OpenFDA database for critical warnings and safety information 
    related to the specified drug. Use this tool to verify the safety of any 
    medication proposed in the treatment plan.
    """
    # Call the underlying logic function from data_analyze.py
    result = get_openfda_warnings(drug_name)
    return FdaWarningOutput(**result)

if __name__ == "__main__":
    print("--- Starting FDA MCP Server on port 8001 ---")
    # --- FIX: Use the FastMCP built-in .run() method with correct arguments ---
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
    # -------------------------------------------------------------------------
