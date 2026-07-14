import logging
import requests
import asyncio

logger = logging.getLogger("NotificationWorker")

class NotificationWorker:
    def __init__(self, topic_url: str):
        self.topic_url = topic_url
        logger.info(f"NotificationWorker initialized with topic URL: {self.topic_url}")

    async def handle_alert(self, payload: dict):
        """Consumes TriggerAlert events and sends a push notification via ntfy.sh."""
        if not self.topic_url:
            logger.warning("No topic URL configured. Notification skipped.")
            return

        title = payload.get("title", "Meet Assistant Alert")
        message = payload.get("message", "No content provided.")
        priority = payload.get("priority", "default")

        headers = {
            "Title": title,
            "Priority": priority
        }

        logger.info(f"Dispatching alert to ntfy.sh: {title} - {message}")
        
        try:
            response = await asyncio.to_thread(
                requests.post,
                self.topic_url,
                data=message.encode('utf-8'),
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Push notification sent successfully.")
            else:
                logger.error(f"Failed to send push notification: HTTP {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
