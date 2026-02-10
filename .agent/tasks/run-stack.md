---
title: Run the full ELK + Elastic MCP + Chat stack
description: Step‑by‑step guide for starting all services and the UI locally.
---

## Prerequisites

- Docker Desktop with Docker Compose v2.
- Python 3.10+ (for running the chat UI/CLI outside Docker).
- Ollama installed and running on the host, with the configured model pulled (see `chat/config.py`).

## 1. Start Ollama and pull the model

- Ensure the Ollama daemon is running.
- Pull (or adjust) the model referenced in `chat/config.py`:

```bash
ollama pull gpt-oss:120b-cloud
```

If you change the model name, update `MODEL` in `chat/config.py`.

## 2. Build and start Elasticsearch first

From the repo root:

```bash
docker compose -f ./docker-compose.yml build
docker compose up -d elasticsearch
```

Wait until Elasticsearch is healthy on `http://localhost:9200`.

## 3. Create an API key for Elastic MCP

Elastic MCP uses an Elasticsearch API key for authentication. From PowerShell in the repo root (as documented in `README.md`):

```powershell
$json = @'
{
  "name": "mcp-key",
  "role_descriptors": {
    "mcp_role": {
      "cluster": ["monitor"],
      "index": [
        {
          "names": ["logs-dummy-backend*", ".ds-logs-dummy-backend*"],
          "privileges": ["read", "view_index_metadata"],
          "allow_restricted_indices": true
        }
      ]
    }
  }
}
'@
```

Then:

```powershell
$json | docker exec -i elk-elasticsearch-1 sh -c `
"curl -s -u elastic:changeme -H 'Content-Type: application/json' -X POST http://localhost:9200/_security/api_key --data-binary @-"
```

Copy the resulting base64 API key string.

## 4. Configure Elastic MCP API key

Edit `docker-compose.yml`:

- In the `elastic_mcp` service, set:
  - `ES_API_KEY=<your_base64_api_key_here>`

Example:

```yaml
  elastic_mcp:
    image: docker.elastic.co/mcp/elasticsearch:0.4.0
    environment:
      - ES_URL=http://elasticsearch:9200
      - ES_API_KEY=MDd2SlJw...snipped...
```

Do **not** commit real keys to version control; prefer environment overrides or `.env` in real deployments.

## 5. Start the remaining services

From the repo root:

```bash
docker compose up -d --build
```

This starts:
- `backend` (log generator),
- `filebeat` (log shipper),
- `kibana`,
- `elastic_mcp`.

Confirm services:

```bash
docker compose ps
```

You should see all containers `running` or `healthy`.

## 6. Run the chat UI

From the repo root, with your Python environment active:

```bash
streamlit run chat/ui.py
```

Open the UI at:

```bash
http://localhost:8501/
```

You can now ask questions like:
- “How many errors per route in the last 2 hours?”
- “Which users see the most login failures?”

## 7. Optional: Use the CLI instead of UI

You can also interact via the CLI:

```bash
python -m chat.cli "how many errors per route?"
```

This prints:
- the chosen MCP tools and arguments,
- raw ES|QL / search results,
- the final natural‑language answer.

