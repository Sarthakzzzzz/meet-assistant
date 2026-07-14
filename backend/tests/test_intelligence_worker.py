import unittest
from unittest.mock import MagicMock, patch
import asyncio
from workers.intelligence_worker import IntelligenceWorker
from langchain_core.documents import Document

class TestIntelligenceWorker(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.state = MagicMock()
        self.config = {
            "llm": {
                "provider": "openrouter",
                "api_url": "https://openrouter.ai/api/v1/chat/completions",
                "model_name": "google/gemini-2.5-flash",
                "api_key": "mock-api-key",
            }
        }
        
        # Patch the dependencies of IntelligenceWorker
        self.vector_store_patcher = patch("workers.intelligence_worker.MeetingVectorStore")
        self.llm_client_patcher = patch("workers.intelligence_worker.LLMClient")
        
        self.mock_vector_store = self.vector_store_patcher.start().return_value
        self.mock_llm_client = self.llm_client_patcher.start().return_value
        
        self.worker = IntelligenceWorker(self.bus, self.state, self.config)

    def tearDown(self):
        self.vector_store_patcher.stop()
        self.llm_client_patcher.stop()

    async def test_handle_slide_captured(self):
        # Trigger slide captured event
        await self.worker.handle_slide_captured("slide_1.png")
        self.assertEqual(self.worker.current_slide_path, "slide_1.png")

    async def test_handle_platform_caption(self):
        # Setup slide path
        self.worker.current_slide_path = "slide_1.png"
        
        # Trigger caption event
        payload = {"speaker": "Sarthak", "text": "Hello world"}
        await self.worker.handle_platform_caption(payload)
        
        # Verify vector store ingestion
        self.mock_vector_store.add_caption.assert_called_once_with(
            speaker="Sarthak",
            text="Hello world",
            slide_path="slide_1.png"
        )

    async def test_handle_user_chat_query(self):
        # Mock vector store similarity search return value
        self.mock_vector_store.similarity_search.return_value = [
            Document(page_content="Sarthak: Hello world", metadata={"slide": "slide_1.png"})
        ]
        
        # Mock LLM client response
        self.mock_llm_client.query.return_value = "Response from AI"
        
        # Trigger chat query
        await self.worker.handle_user_chat_query("What did Sarthak say?")
        
        # Verify RAG pipeline steps
        self.mock_vector_store.similarity_search.assert_called_once_with("What did Sarthak say?", k=5)
        self.mock_llm_client.query.assert_called_once()
        self.bus.publish.assert_called_with("SendChat", "Response from AI")

class TestIntelligenceWorkerIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_live_openrouter_api(self):
        # Parse API key from the local .env file
        api_key = None
        env_path = "/home/sarthak/Documents/meet-assistant/.env"
        import os
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
        
        if not api_key:
            self.skipTest("No OPENROUTER_API_KEY found in .env, skipping live integration test.")

        bus = MagicMock()
        state = MagicMock()
        config = {
            "llm": {
                "provider": "openrouter",
                "api_url": "https://openrouter.ai/api/v1/chat/completions",
                "model_name": "openrouter/free",
                "api_key": api_key,
            }
        }
        
        # Create worker without patching
        worker = IntelligenceWorker(bus, state, config)
        
        # Ingest mock caption so similarity search returns something
        worker.vector_store.add_caption(
            speaker="Sarthak",
            text="The secret launch date is September 1st.",
            slide_path="slide_1.png"
        )
        
        # Execute query
        await worker.handle_user_chat_query("What is the launch date?")
        
        # Verify that SendChat was called with a non-empty response
        self.assertTrue(bus.publish.called)
        call_args = bus.publish.call_args[0]
        self.assertEqual(call_args[0], "SendChat")
        self.assertTrue(len(call_args[1]) > 0)
        print(f"\n[Integration Test Output] Generated reply: \"{call_args[1]}\"")

if __name__ == "__main__":
    unittest.main()
