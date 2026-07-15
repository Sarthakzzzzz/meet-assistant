import logging
import asyncio
import os
from core.vector_store import MeetingVectorStore
from core.llm_client import LLMClient

logger = logging.getLogger("IntelligenceWorker")

class IntelligenceWorker:
    def __init__(self, bus, state_manager, config):
        self.bus = bus
        self.state = state_manager
        self.config = config
        
        self.current_slide_path = None
        
        # decoupled services
        self.vector_store = MeetingVectorStore()
        self.llm_client = LLMClient(config)
        
        logger.info("IntelligenceWorker initialized using decoupled core services.")

    async def handle_chat_received(self, text: str):
        # Reserved for RAG queries
        pass

    async def handle_user_chat_query(self, query: str):
        logger.info(f"Received RAG query: {query}")
        
        try:
            # 1. Retrieve Context from ChromaDB using Vector Store service
            docs = self.vector_store.similarity_search(query, k=5)
            context = "\n".join([f"[Slide: {d.metadata.get('slide', 'None')}] {d.page_content}" for d in docs])
            
            # 2. Construct Prompt
            prompt = f"""You are a helpful AI Meeting Assistant. Answer the user's question based on the meeting context below. 
If you don't know the answer based on the context, just say you don't know.

Meeting Context:
{context}

Question: {query}
Answer:"""

            # 3. Query LLM via client
            answer = await asyncio.to_thread(self.llm_client.query, prompt)
            
            # Publish response back to Web UI
            self.bus.publish("SendChat", answer)
        except Exception as e:
            logger.error(f"Error handling RAG query: {e}")
            self.bus.publish("SendChat", f"Sorry, I encountered an error: {e}")

    async def handle_transcript_updated(self, payload: dict):
        pass # Replaced by RAG

    async def handle_platform_caption(self, payload: dict):
        text = payload.get("text", "")
        speaker = payload.get("speaker", "Platform CC")
        
        if not text.strip():
            return
            
        # Ingest into ChromaDB using decoupled vector store
        self.vector_store.add_caption(
            speaker=speaker,
            text=text,
            slide_path=self.current_slide_path
        )
        
        logger.debug(f"Ingested to RAG: {speaker}: {text}")

    async def handle_slide_captured(self, filepath: str):
        # ISSUE #2: This handler only updates the active slide path. It does not run OCR
        # on the captured image to extract text content for embedding into ChromaDB.
        # An OCR pass should be added here before or after updating current_slide_path.
        logger.info(f"New slide captured: {filepath}")
        self.current_slide_path = filepath
