from data_analyze import client, GROQ_MODEL, rag_lookup_kb

def kb_agent(query_text, top_k=4):
    hits = rag_lookup_kb(query_text, top_k=top_k)
    if not hits:
        return "No guideline passages found in KB."

    raw_passages = []
    for h in hits:
        passage = h.get("passage", "").strip()
        if len(passage) > 1000:
            passage = passage[:950].rsplit(" ", 1)[0] + "..."
        raw_passages.append(passage)

    combined_text = "\n\n".join(raw_passages)

    prompt = f"""
Reformat the following medical guideline passages into clear, easy-to-read bullet points.
Each bullet point should be concise and include a short explanation for better understanding.

Passages:
{combined_text}
"""
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Error formatting KB output: {str(e)}"
