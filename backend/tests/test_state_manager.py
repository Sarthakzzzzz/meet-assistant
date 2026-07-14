import unittest
import os
import shutil
from core.state_manager import StateManager

class TestStateManager(unittest.TestCase):
    def setUp(self):
        self.test_log_dir = "logs/test_runs"
        self.test_log_path = os.path.join(self.test_log_dir, "test_transcript.txt")
        self.state = StateManager(transcript_log_path=self.test_log_path)

    def tearDown(self):
        # Cleanup test logs
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir)

    def test_add_and_retrieve_transcript(self):
        self.state.add_transcript("Balaji", "Hello from Balaji")
        self.state.add_transcript("Sarthak", "Hi Balaji")

        recent = self.state.get_recent_transcript(limit=2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["speaker"], "Balaji")
        self.assertEqual(recent[0]["text"], "Hello from Balaji")
        self.assertEqual(recent[1]["speaker"], "Sarthak")
        self.assertEqual(recent[1]["text"], "Hi Balaji")

    def test_context_management(self):
        self.state.update_context("active_slide", "slide_1.png")
        self.assertEqual(self.state.get_context("active_slide"), "slide_1.png")
        self.assertIsNone(self.state.get_context("non_existent_key"))

if __name__ == "__main__":
    unittest.main()
