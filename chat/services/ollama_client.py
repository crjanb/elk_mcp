import requests

from chat.config import OLLAMA_URL, MODEL


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_URL, model: str = MODEL):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt: str, stream: bool = False, timeout: int = 60) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
        }
        resp = requests.post(self.base_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return (resp.json().get("response") or "").strip()
