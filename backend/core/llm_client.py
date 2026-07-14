import requests
import logging

logger = logging.getLogger("LLMClient")

class LLMClient:
    def __init__(self, config: dict):
        llm_cfg = config.get("llm", {})
        self.provider = llm_cfg.get("provider", "openrouter")
        self.api_url = llm_cfg.get("api_url", "https://openrouter.ai/api/v1/chat/completions")
        self.model_name = llm_cfg.get("model_name", "google/gemini-2.5-flash")
        self.api_key = llm_cfg.get("api_key", "")

    def query(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
