import unittest
import asyncio
from core.event_bus import EventBus

class TestEventBus(unittest.IsolatedAsyncioTestCase):
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received_data = []

        async def callback(data):
            received_data.append(data)

        bus.subscribe("TestTopic", callback)
        bus.start()

        bus.publish("TestTopic", "Hello EventBus")
        
        # Give some time for the queue processor to handle the event
        await asyncio.sleep(0.1)

        self.assertIn("Hello EventBus", received_data)
        await bus.stop()

    async def test_multiple_subscribers(self):
        bus = EventBus()
        received_1 = []
        received_2 = []

        async def cb1(data):
            received_1.append(data)

        async def cb2(data):
            received_2.append(data)

        bus.subscribe("TopicX", cb1)
        bus.subscribe("TopicX", cb2)
        bus.start()

        bus.publish("TopicX", "Broadcast")
        await asyncio.sleep(0.1)

        self.assertIn("Broadcast", received_1)
        self.assertIn("Broadcast", received_2)
        await bus.stop()

if __name__ == "__main__":
    unittest.main()
