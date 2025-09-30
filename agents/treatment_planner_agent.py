import re
from data_analyze import client, GROQ_MODEL, get_openfda_warnings

def _extract_drug_candidates(text: str):
    common_drugs = ["metformin", "insulin", "ibuprofen", "aspirin", "atorvastatin",
                    "amlodipine", "lisinopril", "paracetamol", "amoxicillin",
                    "ciprofloxacin", "warfarin"]
    found = set()
    text_lower = text.lower()
    for d in common_drugs:
        if d in text_lower:
            found.add(d)
    candidates = re.findall(r"\b([A-Za-z]{3,20}(?:in|ol|ide|ene|ine|cillin))\b", text_lower)
    for c in candidates:
        found.add(c)
    return list(found)

def treatment_planner_agent(data: str, kb_snippets: str = None) -> str:
    try:
        prompt = f"""
        Based on findings, ICD codes, clinical reasoning, and guideline snippets, create a concise treatment plan.
        Use bullet points and short explanations. Mention FDA drug warnings if relevant.

        INPUT:
        {data}

        KB SNIPPETS:
        {kb_snippets if kb_snippets else 'No KB snippets provided.'}
        """
        resp = client.chat.completions.create(model=GROQ_MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.3)
        plan = resp.choices[0].message.content

        candidates = _extract_drug_candidates(plan + "\n" + data + ("\n" + (kb_snippets or "")))
        enriched_notes = []
        for drug in candidates:
            warnings = get_openfda_warnings(drug)
            enriched_notes.append({
                "drug": drug,
                "fda_warnings": warnings
            })

        safety_sections = []
        for e in enriched_notes:
            s = f"🔹 {e['drug'].title()}\n"
            warnings = e["fda_warnings"]
            if isinstance(warnings, dict):
                s += f"- FDA Warnings (brand/generic): {warnings.get('brand')}/{warnings.get('generic')}\n"
                s += f"  * Summary: {warnings.get('warnings')}\n"
            else:
                s += f"- FDA Warnings: {warnings}\n"
            safety_sections.append(s)

        safety_text = "\n\n".join(safety_sections) if safety_sections else "No drug candidates found for FDA safety checks."
        return plan + "\n\n---\n\nSafety Notes (FDA-augmented):\n" + safety_text

    except Exception as e:
        return f"❌ Treatment Planner Agent failed: {str(e)}"
