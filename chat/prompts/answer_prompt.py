def build_answer_prompt(question: str, context: str) -> str:
    return f"""
You are an observability assistant.

User question:
{question}

Elasticsearch log data (from ES|QL):
{context}

Answer clearly in plain English.
Highlight insights, trends, or anomalies.
""".strip()
