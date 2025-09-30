from data_analyze import client, GROQ_MODEL

def advisory_agent(data: str) -> str:
    try:
        prompt = f"Rewrite the clinical reasoning and treatment plan below into simple, patient-friendly advice:\n{data}"
        resp = client.chat.completions.create(model=GROQ_MODEL,
                                              messages=[{"role": "user", "content": prompt}],
                                              temperature=0.4)
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Advisory Agent failed: {str(e)}"
