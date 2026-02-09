import sys
import json
import requests

MCP_URL = "http://localhost:8080/mcp"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gpt-oss:120b-cloud"


def call_mcp_esql(query: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "esql",
            "arguments": {
                "query": query
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    resp = requests.post(MCP_URL, headers=headers, json=payload, stream=True)
    resp.raise_for_status()

    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if text.startswith("data:"):
            data = json.loads(text.replace("data:", "").strip())
            if "result" in data:
                return data["result"]["content"][-1]["text"]

    return None


def ask_ollama(question: str, context: str):
    prompt = f"""
You are an observability assistant.

User question:
{question}

Elasticsearch log data (from ES|QL):
{context}

Answer clearly in plain English.
Highlight insights, trends, or anomalies.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    resp = requests.post(OLLAMA_URL, json=payload)
    resp.raise_for_status()
    return resp.json()["response"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_logs.py \"your question\"")
        sys.exit(1)

    question = sys.argv[1].lower()

    # Simple intent → ES|QL mapping (v1)
    if "log level" in question or "level" in question:
        esql = "FROM logs-dummy-backend* | STATS count() BY `log.level`"
    elif "error" in question:
        esql = (
            "FROM logs-dummy-backend* "
            "| WHERE `log.level` == \"ERROR\" OR status >= 400 "
            "| STATS count() BY route, status"
        )
    else:
        esql = "FROM logs-dummy-backend* | LIMIT 20"

    print("\n🔍 Running ES|QL via MCP:")
    print(esql)

    context = call_mcp_esql(esql)

    print("\n📊 Raw MCP Result:")
    print(context)

    print("\n🤖 Ollama Answer:\n")
    answer = ask_ollama(question, context)
    print(answer)


if __name__ == "__main__":
    main()
