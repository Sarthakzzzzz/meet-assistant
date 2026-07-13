import logging
import asyncio
import requests
import base64
import os

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
        
        self.current_slide_path = None
        self.active_captions = []
        
        logger.info(f"IntelligenceWorker initialized using {self.provider} model: {self.model_name}")

    async def handle_chat_received(self, text: str):
        logger.info(f"Processing chat message: '{text}'")
        await self._evaluate_text(text, source="Chat")

    async def handle_transcript_updated(self, payload: dict):
        text = payload.get("text", "")
        logger.info(f"Processing transcript text: '{text}'")
        await self._evaluate_text(text, source="Transcript")

    async def handle_platform_caption(self, payload: dict):
        text = payload.get("text", "")
        speaker = payload.get("speaker", "Platform CC")
        logger.info(f"Processing platform caption: '{text}'")
        
        caption_line = f"{speaker}: {text}"
        # Append to active slide caption log
        self.active_captions.append(caption_line)
        
        # Save to file simultaneously
        try:
            if self.current_slide_path:
                txt_path = self.current_slide_path.rsplit(".", 1)[0] + ".txt"
            else:
                txt_path = "data/presentation_slides/pre_slide_captions.txt"
                
            os.makedirs(os.path.dirname(os.path.abspath(txt_path)), exist_ok=True)
            with open(txt_path, "a", encoding="utf-8") as f:
                f.write(caption_line + "\n")
        except Exception as e:
            logger.error(f"Failed to save caption to text file: {e}")
        
        # Still evaluate for panic keywords
        await self._evaluate_text(text, source="PlatformCC")

    async def handle_slide_captured(self, filepath: str):
        logger.info(f"New slide captured: {filepath}")
        
        # Summarize the finished slide before switching active slide
        if self.current_slide_path and self.active_captions:
            captions_to_summarize = list(self.active_captions)
            slide_to_summarize = self.current_slide_path
            
            logger.info(f"Triggering background summary for finished slide: {slide_to_summarize}")
            asyncio.create_task(self._summarize_slide(slide_to_summarize, captions_to_summarize))
            
        self.current_slide_path = filepath
        self.active_captions = []

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
            logger.error(f"Failed to query {self.provider} API: {e}")

    async def _summarize_slide(self, slide_path: str, captions: list):
        """Asynchronously requests AI to summarize what was spoken for a slide, with vision fallback."""
        def prepare_data():
            if not os.path.exists(slide_path):
                return ""
            with open(slide_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
                
        base64_image = await asyncio.to_thread(prepare_data)
        transcript_str = "\n".join(captions)
        
        system_prompt = (
            "You are a precise meeting assistant. Analyze the slide image and/or the transcript of "
            "what was spoken during this slide, and write a summary of what the presenter discussed. "
            "Format the output as a concise bulleted list (max 3 points). Output only the bullet points."
        )
        
        prompt = f"Transcript of spoken captions for this slide:\n{transcript_str}"

        # 1. Try Multimodal API Call (Vision + Text)
        if base64_image and self.provider == "openrouter":
            logger.info("Attempting multimodal slide summarization (Image + Text)...")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/google/meet-assistant",
                "X-Title": "Meet Assistant"
            }
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            }
            
            try:
                def query_vision():
                    resp = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
                    if resp.status_code == 200:
                        choices = resp.json().get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
                    logger.warning(f"Multimodal query failed with status {resp.status_code}. Retrying text-only...")
                    return None
                    
                summary = await asyncio.to_thread(query_vision)
                if summary:
                    logger.info("Multimodal slide summary generated successfully.")
                    self.bus.publish("SlideSummaryGenerated", {"slide": slide_path, "summary": summary})
                    return
            except Exception as e:
                logger.warning(f"Multimodal query raised exception: {e}. Retrying text-only...")

        # 2. Text-Only Fallback
        logger.info("Running text-only slide summarization...")
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
            
        try:
            def query_text():
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=120)
                if resp.status_code == 200:
                    resp_json = resp.json()
                    if self.provider == "openrouter":
                        choices = resp_json.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
                        return ""
                    else:
                        return resp_json.get("response", "").strip()
                return None
                
            summary = await asyncio.to_thread(query_text)
            if summary:
                logger.info("Text-only slide summary generated successfully.")
                self.bus.publish("SlideSummaryGenerated", {"slide": slide_path, "summary": summary})
            else:
                logger.error("Failed to generate slide summary.")
        except Exception as e:
            logger.error(f"Text-only summarization raised exception: {e}")
