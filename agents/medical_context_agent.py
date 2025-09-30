from data_analyze import client, GROQ_MODEL

def medical_context_icd(data: str) -> str:
    try:
        prompt = f"""
        You are a clinical assistant. Based on the extracted findings below, list likely ICD-10 codes with short explanations.
        Provide concise bullet points for context.

        Findings:
        {data}
        """
        resp = client.chat.completions.create(model=GROQ_MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.2)
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Medical Context Agent failed: {str(e)}"
