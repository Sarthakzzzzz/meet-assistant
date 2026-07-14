import unittest
from unittest.mock import MagicMock
from sensors.browser_sensor import BrowserSensor

class TestBrowserSensor(unittest.TestCase):
    def setUp(self):
        self.bus = MagicMock()
        self.config = {
            "app": {"platform": "microsoft_teams"},
            "browser": {
                "meeting_url": "https://teams.microsoft.com/meet/123",
                "headless": True,
                "guest_name": "Test Bot"
            }
        }
        self.sensor = BrowserSensor(self.bus, self.config)

    def test_get_new_suffix_normal(self):
        old = "Hello world this is a test"
        new = "Hello world this is a test of the system"
        suffix = self.sensor._get_new_suffix(old, new)
        self.assertEqual(suffix, "of the system")

    def test_get_new_suffix_overlap(self):
        old = "world this is a test"
        new = "is a test of the emergency broadcast"
        suffix = self.sensor._get_new_suffix(old, new)
        self.assertEqual(suffix, "of the emergency broadcast")

    def test_parse_teams_captions_with_initials(self):
        caption_text = "BB\nBalaji Bodkhe\nHello from the team\nHow is everyone?"
        blocks = self.sensor._parse_teams_captions(caption_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["speaker"], "Balaji Bodkhe")
        self.assertEqual(blocks[0]["text"], "Hello from the team How is everyone?")

    def test_parse_teams_captions_without_initials(self):
        caption_text = "Balaji Bodkhe\nThis is a caption statement."
        blocks = self.sensor._parse_teams_captions(caption_text)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["speaker"], "Balaji Bodkhe")
        self.assertEqual(blocks[0]["text"], "This is a caption statement.")

if __name__ == "__main__":
    unittest.main()
