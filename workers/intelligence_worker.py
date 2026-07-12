import logging
import asyncio
import requests

logger = logging.getLogger("IntelligenceWorker")

class IntelligenceWorker:
    def __init__(self, bus, state_manager, config):
        self.bus = bus
        self.state = state_manager
        self.config = config
        
        llm_cfg = config.get("llm", {})
        self.provider = llm_cfg.get("provider", "ollama")
        self.api_url = llm_cfg.get("api_url", "http://localhost:11434/api/generate")
        self.model_name = llm_cfg.get("model_name", "llama3")
        self.api_key = llm_cfg.get("api_key", "")
        self.panic_keywords = [kw.lower() for kw in llm_cfg.get("panic_keywords", [])]
        
        logger.info(f"IntelligenceWorker initialized using {self.provider} model: {self.model_name}")

    async def handle_chat_received(self, text: str):
        logger.info(f"Processing chat message: '{text}'")
        await self._evaluate_text(text, source="Chat")

    async def handle_transcript_updated(self, payload: dict):
        text = payload.get("text", "")
        logger.info(f"Processing transcript text: '{text}'")
        await self._evaluate_text(text, source="Transcript")

    async def _evaluate_text(self, text: str, source: str):
        text_lower = text.lower()
        matched_keyword = None
        
        for kw in self.panic_keywords:
            if kw in text_lower:
                matched_keyword = kw
                break
                
        if matched_keyword:
            logger.info(f"Panic keyword '{matched_keyword}' triggered via {source}!")
            
            self.bus.publish("TriggerAlert", {
                "title": f"Panic Keyword Detected ({source})",
                "message": f"Keyword matched: '{matched_keyword}'. Content: '{text}'",
                "priority": "high"
            })
            
            asyncio.create_task(self._generate_reply_and_publish(matched_keyword, text))

    async def _generate_reply_and_publish(self, keyword: str, trigger_text: str):
        recent_entries = self.state.get_recent_transcript(limit=30)
        context_transcript = "\n".join(f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}" for entry in recent_entries)
        
        system_prompt = (
            "You are a helpful meeting assistant for Sarthak. "
            "Sarthak is in a virtual meeting. Someone just spoke or typed a question mentioning them or asking a question. "
            "Write a short, natural, professional response (max 15 words) for Sarthak's assistant to send in the meeting chat box. "
            "For example: 'I am looking into that right now.' or 'Yes, I am here. Let me address that.' "
            "IMPORTANT: Output ONLY the raw response string to type. No intro, no quotes, no explanations."
        )
        
        prompt = (
            f"Meeting context transcript:\n{context_transcript}\n\n"
            f"Triggering statement: '{trigger_text}'\n"
            f"Triggered keyword: '{keyword}'\n\n"
            f"Response:"
        )
        
        headers = {"Content-Type": "application/json"}
        if self.provider == "openrouter":
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["HTTP-Referer"] = "https://github.com/google/meet-assistant"
            headers["X-Title"] = "Meet Assistant"
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            }
        else:
            payload = {
                "model": self.model_name,
                "prompt": f"{system_prompt}\n\n{prompt}",
                "stream": False
            }
            
        logger.info(f"Contacting {self.provider} API ({self.api_url})...")
        
        try:
            def query_llm():
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
                if response.status_code == 200:
                    resp_json = response.json()
                    if self.provider == "openrouter":
                        choices = resp_json.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
                        return ""
                    else:
                        return resp_json.get("response", "").strip()
                else:
                    logger.error(f"{self.provider} returned HTTP error {response.status_code}: {response.text}")
                    return None
            
            reply = await asyncio.to_thread(query_llm)
            
            if reply:
                cleaned_reply = reply.strip().replace('"', '').replace("'", "")
                logger.info(f"{self.provider} generated reply: '{cleaned_reply}'")
                self.bus.publish("SendChat", cleaned_reply)
            
        except Exception as e:
            logger.error(f"Failed to query Ollama API: {e}")
