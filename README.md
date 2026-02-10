## Steps to Run the Project

This project runs an **ELK stack + Elastic MCP + Streamlit chat UI**, while **Ollama runs locally on the host**.

### 1️⃣ Prerequisites

Make sure you have the following installed:

- **Docker Desktop** (with Docker Compose v2)
- **Python 3.10+**  
  _(only needed if you run things outside Docker)_
- **Ollama**  
  _(installed on host, not in Docker)_

#### Verify installations

```bash
docker --version
```
```bash
docker compose version
```
```bash
ollama --version
```


## 2️⃣ Commands

**1. Ollama must be running before starting Docker.**

**2. Make sure the required model exists (change the model name if needed):**

```bash
ollama pull gpt-oss:120b-cloud
```

**3. Run following cmds:**

```bash
docker compose -f .\docker-compose.yml build
```
```bash
docker compose up -d elasticsearch
```

**4.Run these two cmds in base dir to get API key before running other containers**
```bash
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

```bash
$json | docker exec -i elk-elasticsearch-1 sh -c `
"curl -s -u elastic:changeme -H 'Content-Type: application/json' -X POST http://localhost:9200/_security/api_key --data-binary @-"
```
**5. Paste API key in docker compose file:**
```bash
eg: MDd2SlJwd0JNdk1HRHZJdXE3M0M6VFZ1ZkhQdFNSNnlWdnpOXzRXeXNfZw==
```

```bash
Paste this in the docker-compose file.
services:
  elastic_mcp:
    environment:
      - ES_URL=http://elasticsearch:9200
      - ES_AUTH_HEADER=MDd2SlJwd0JNdk1HRHZJdXE3M0M6VFZ1ZkhQdFNSNnlWdnpOXzRXeXNfZw==

```

**6. Finally run docker cmds:**
```bash
docker compose up -d --build
```

```bash
streamlit run chat\ui.py
```

Your chat UI is running at:

```bash
http://localhost:8501/
```
