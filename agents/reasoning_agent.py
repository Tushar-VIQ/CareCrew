from data_analyze import client, GROQ_MODEL

def reasoning_agent(data: str) -> str:
    try:
        prompt = f"""
        Analyze the medical findings and ICD codes below.
        Provide a concise clinical reasoning summary in bullet points.

        {data}
        """
        resp = client.chat.completions.create(model=GROQ_MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.2)
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Reasoning Agent failed: {str(e)}"
