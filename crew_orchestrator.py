from crewai import Crew, Process, Task, Agent
from crewai_tools import MCPServerAdapter
from data_analyze import client, ensure_kb_index
from agents.document_analyzer import document_analyzer as doc_analyzer_logic
from agents.medical_context_agent import medical_context_icd as icd_logic
from agents.reasoning_agent import reasoning_agent as reasoning_logic 
from agents.kb_agent import kb_agent as kb_logic
from agents.treatment_planner_agent import treatment_planner_agent as planner_logic
from agents.advisory_agent import advisory_agent as advisory_logic
from agents.agent_definitions import ( 
    get_document_analyzer_agent, get_medical_context_agent, get_reasoning_agent, 
    get_kb_agent, get_treatment_planner_agent, get_advisory_agent
)
import groq
from yarl import URL

# --- MCP Client Setup ---
MCP_SERVER_PARAMS = [
    {"url": "http://127.0.0.1:8001/mcp", "transport": "streamable-http"},
    {"url": "http://127.0.0.1:8002/mcp", "transport": "streamable-http"},
]

def get_mcp_tools():
    try:
        adapter = MCPServerAdapter(MCP_SERVER_PARAMS)
        return adapter.tools
    except Exception as e:
        raise RuntimeError(
            f"MCP Connection Failure: Ensure servers on 8001 & 8002 are running. Error: {e}"
        )

def fix_groq_url(tool):
    """Ensure Groq models inside tools use string URLs, not URL objects."""
    if hasattr(tool, 'model') and isinstance(tool.model, groq.Groq):
        tool.model = groq.Groq(url=str(tool.model.url))
    return tool

def safe_task(callback, task_name):
    """Execute a task safely and log success/failure in terminal."""
    try:
        output = callback(None)
        print(f"✅ {task_name} succeeded.")
        return output
    except Exception as e:
        print(f"❌ {task_name} failed: {e}")
        return f"❌ Task failed: {task_name} | Error: {e}"

def run_medical_crew(file_paths: list, user_note: str = None) -> str:
    # --- MCP tools ---
    try:
        all_mcp_tools = get_mcp_tools()
    except Exception as e:
        return f"❌ Failed to initialize MCP tools: {e}"

    try:
        kb_search_tool = next((t for t in all_mcp_tools if t.name == 'search_medical_guidelines'), None)
        fda_checker_tool = next((t for t in all_mcp_tools if t.name == 'check_drug_safety'), None)
        if not kb_search_tool or not fda_checker_tool:
            return "❌ Required MCP tools not found."

        kb_search_tool = fix_groq_url(kb_search_tool)
        fda_checker_tool = fix_groq_url(fda_checker_tool)
    except Exception as e:
        return f"❌ Error fetching or fixing MCP tools: {e}"

    # --- Agents ---
    try:
        document_analyzer_a = get_document_analyzer_agent()
        medical_context_agent = get_medical_context_agent()
        reasoning_agent_a = get_reasoning_agent() 
        kb_agent = get_kb_agent(tools=[kb_search_tool]) 
        treatment_planner_agent = get_treatment_planner_agent(tools=[fda_checker_tool]) 
        advisory_agent = get_advisory_agent()
    except Exception as e:
        return f"❌ Failed to initialize agents: {e}"

    # --- Execute tasks safely ---
    doc_analysis_output = safe_task(
        lambda _: doc_analyzer_logic(file_paths, user_note),
        "Document Analysis"
    )

    icd_mapping_output = safe_task(
        lambda _: icd_logic(doc_analysis_output),
        "ICD Mapping"
    )

    reasoning_output = safe_task(
        lambda _: reasoning_logic(icd_mapping_output),
        "Clinical Reasoning"
    )

    kb_lookup_output = safe_task(
        lambda _: kb_logic(reasoning_output),  # Use logic function, not Agent.call()
        "KB Lookup"
    )

    treatment_output = safe_task(
        lambda _: planner_logic(
            doc_analysis_output + icd_mapping_output + reasoning_output,
            kb_snippets=kb_lookup_output
        ),
        "Treatment Planning"
    )

    advisory_output = safe_task(
        lambda _: advisory_logic(treatment_output),
        "Patient Advisory"
    )

    # --- Final report ---
    final_report_parts = [
        f"### 📄 Document Analysis\n{doc_analysis_output}",
        f"### 🏷️ Medical Context (ICD)\n{icd_mapping_output}",
        f"### 🧠 Clinical Reasoning\n{reasoning_output}",
        f"### 🗂️ KB Guidelines\n{kb_lookup_output}",
        f"### 🩺 Treatment Plan\n{treatment_output}",
        f"### 💡 Patient Advisory\n{advisory_output}",
    ]

    return "\n\n---\n\n".join(final_report_parts)


if __name__ == '__main__':
    try:
        ensure_kb_index()
    except Exception as e:
        print(f"❌ Failed KB setup: {e}")
