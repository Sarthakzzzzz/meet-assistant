import asyncio
import logging
from typing import Callable, Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EventBus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._queue = asyncio.Queue()
        self._running = False
        self._task = None

    def subscribe(self, topic: str, callback: Callable):
        """Registers an asynchronous callback for a specific topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)
            logger.info(f"Subscribed callback '{callback.__name__}' to topic '{topic}'")

    def publish(self, topic: str, data: Any = None):
        """Places an event onto the queue to be processed non-blockingly."""
        try:
            self._queue.put_nowait((topic, data))
            logger.debug(f"Event published to '{topic}'")
        except asyncio.QueueFull:
            logger.error(f"Event queue full! Dropped event for '{topic}'")

    async def _process_events(self):
        """Background task that continuously routes queued events to subscribers."""
        self._running = True
        logger.info("Event Bus is online and routing events...")
        while self._running:
            try:
                topic, data = await self._queue.get()
                subscribers = self._subscribers.get(topic, [])
                
                for callback in subscribers:
                    asyncio.create_task(callback(data))
                
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event loop: {e}")

    def start(self):
        """Spawns the background event processor."""
        if not self._task:
            self._task = asyncio.create_task(self._process_events())

    async def stop(self):
        """Gracefully shuts down the event bus."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event Bus stopped.")
