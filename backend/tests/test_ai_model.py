import unittest
import os
from core.llm_client import LLMClient

class TestAIModel(unittest.TestCase):
    def test_llm_client_integration(self):
        # Load API key from local .env
        api_key = None
        env_path = "/home/sarthak/Documents/meet-assistant/.env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip().startswith("OPENROUTER_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
        
        if not api_key:
            self.skipTest("No OPENROUTER_API_KEY found in .env, skipping integration test.")

        # Configure LLM Client
        config = {
            "llm": {
                "provider": "openrouter",
                "api_url": "https://openrouter.ai/api/v1/chat/completions",
                "model_name": "openrouter/free",
                "api_key": api_key,
            }
        }

        # Initialize LLM Client
        client = LLMClient(config)

        # Query model
        response = client.query("How many r's are in the word 'strawberry'?")
        
        self.assertTrue(len(response) > 0, "LLM client returned an empty response")
        
        # Verify correctness
        has_correct_answer = "3" in response or "three" in response.lower()
        self.assertTrue(has_correct_answer, f"Model failed to answer correctly: {response}")
        print(f"\n[AI Model Test Output] Response: \"{response}\"")

if __name__ == "__main__":
    unittest.main()