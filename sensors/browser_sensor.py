import asyncio
import logging
import os
import datetime
from playwright.async_api import async_playwright

logger = logging.getLogger("BrowserSensor")

class BrowserSensor:
    def __init__(self, bus, config):
        self.bus = bus
        self.config = config
        
        self.platform = config.get("app", {}).get("platform", "google_meet")
        self.selectors = config.get("selectors", {}).get(self.platform, {})
        
        browser_cfg = config.get("browser", {})
        self.meeting_url = browser_cfg.get("meeting_url", "https://meet.google.com")
        self.headless = browser_cfg.get("headless", False)
        self.guest_name = browser_cfg.get("guest_name", "Sarthak Pujari")
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._running = False
        self._tasks = []
        
        self.slides_dir = "data/presentation_slides"
        os.makedirs(self.slides_dir, exist_ok=True)
        self.last_slide_hash = None

    async def start(self):
        """Starts Playwright, launches the browser and navigates to the meeting."""
        logger.info(f"Launching Playwright Chromium (headless={self.headless})...")
        self.playwright = await async_playwright().start()
        
        user_data_dir = os.path.join(os.getcwd(), "data", "browser_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=self.headless,
            permissions=["microphone", "camera"],
            args=['--use-fake-ui-for-media-stream']
        )
        
        self.page = self.context.pages[0]
        
        logger.info(f"Navigating to {self.platform} meeting: {self.meeting_url}")
        await self.page.goto(self.meeting_url)
        
        if self.platform == "google_meet":
            try:
                logger.info("Waiting for pre-join screen to load...")
                await asyncio.sleep(5)
                
                logger.info("Disabling Microphone and Camera...")
                await self.page.keyboard.press("Control+d")
                await asyncio.sleep(1)
                await self.page.keyboard.press("Control+e")
                await asyncio.sleep(1)
                
                name_input = self.page.locator("input[placeholder='Your name']")
                if await name_input.is_visible():
                    logger.info(f"Entering guest name: {self.guest_name}...")
                    await name_input.fill(self.guest_name)
                    await asyncio.sleep(1)
                
                join_buttons = ["Ask to join", "Join now"]
                for btn_text in join_buttons:
                    btn = self.page.locator(f"span:has-text('{btn_text}')")
                    if await btn.is_visible():
                        logger.info(f"Clicking '{btn_text}'...")
                        await btn.click()
                        break
                
                logger.info("Waiting to be admitted into the meeting (timeout=60s)...")
                chat_button = self.selectors.get("chat_button")
                if chat_button:
                    await self.page.wait_for_selector(chat_button, timeout=60000)
                    logger.info("Joined the meeting! Opening chat panel...")
                    await self.page.click(chat_button)
                    await asyncio.sleep(1.5)
            except Exception as e:
                logger.error(f"Error during automated meeting join: {e}")
                
        elif self.platform == "microsoft_teams":
            try:
                logger.info("Handling Microsoft Teams landing page...")
                web_join_btn = self.page.locator("button:has-text('Continue on this browser'), button[data-tid='joinOnWeb']")
                if await web_join_btn.is_visible():
                    logger.info("Clicking 'Continue on this browser'...")
                    await web_join_btn.click()
                
                await asyncio.sleep(6)
                
                name_inputs = [
                    self.page.locator("input[placeholder='Enter name']"),
                    self.page.locator("input[placeholder='Type your name']"),
                    self.page.locator("input[data-tid='prejoin-display-name-input']")
                ]
                for n_in in name_inputs:
                    if await n_in.is_visible():
                        logger.info(f"Entering guest name: {self.guest_name}...")
                        await n_in.fill(self.guest_name)
                        await asyncio.sleep(1)
                        break
                
                logger.info("Toggling off microphone and camera...")
                mic_toggle = self.page.locator("button[data-tid='prejoin-audio-toggle']")
                cam_toggle = self.page.locator("button[data-tid='prejoin-video-toggle']")
                
                if await mic_toggle.is_visible():
                    await mic_toggle.click()
                    await asyncio.sleep(0.5)
                if await cam_toggle.is_visible():
                    await cam_toggle.click()
                    await asyncio.sleep(0.5)
                
                join_btn = self.page.locator("button:has-text('Join now'), button[data-tid='prejoin-join-button']")
                if await join_btn.is_visible():
                    logger.info("Clicking 'Join now'...")
                    await join_btn.click()
                
                logger.info("Waiting to be admitted into the Teams meeting...")
                chat_button = self.selectors.get("chat_button")
                if chat_button:
                    await self.page.wait_for_selector(chat_button, timeout=60000)
                    logger.info("Joined Teams meeting! Opening chat panel...")
                    await self.page.click(chat_button)
                    await asyncio.sleep(1.5)
            except Exception as e:
                logger.error(f"Error during automated Teams join: {e}")
        
        self.bus.subscribe("SendChat", self.handle_send_chat)
        
        self._running = True
        self._tasks.append(asyncio.create_task(self._monitor_chat()))
        self._tasks.append(asyncio.create_task(self._monitor_presentation()))

    async def stop(self):
        """Gracefully shuts down Playwright and cancels background loops."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser sensor offline.")

    async def handle_send_chat(self, message: str):
        """Types and submits a chat message inside the meeting window."""
        if not self.page:
            logger.warning("Browser page not ready. Cannot send chat.")
            return

        chat_input = self.selectors.get("chat_input")
        if not chat_input:
            logger.error("Chat input selector not configured.")
            return

        try:
            chat_button = self.selectors.get("chat_button")
            if chat_button:
                is_visible = await self.page.is_visible(chat_input)
                if not is_visible:
                    logger.info("Chat panel is hidden. Opening chat panel...")
                    await self.page.click(chat_button)
                    await asyncio.sleep(0.5)

            logger.info(f"Typing chat: {message}")
            await self.page.fill(chat_input, message)
            await self.page.press(chat_input, "Enter")
        except Exception as e:
            logger.error(f"Error typing chat message: {e}")

    async def _monitor_chat(self):
        """Polls the DOM to extract new chat messages."""
        logger.info("Chat monitoring active.")
        chat_messages_selector = self.selectors.get("chat_messages")
        if not chat_messages_selector:
            logger.warning("No chat message selector configured. Monitoring disabled.")
            return

        last_seen_count = 0
        
        while self._running:
            try:
                elements = self.page.locator(chat_messages_selector)
                count = await elements.count()
                
                if count > last_seen_count:
                    logger.info(f"New chat messages detected! Index {last_seen_count} -> {count}")
                    for i in range(last_seen_count, count):
                        text = await elements.nth(i).text_content()
                        if text:
                            self.bus.publish("ChatReceived", text.strip())
                    last_seen_count = count
            except Exception as e:
                logger.error(f"Error parsing chat messages: {e}")
                
            await asyncio.sleep(1)

    async def _monitor_presentation(self):
        """Saves screenshots of presentation slides when visual changes occur."""
        logger.info("Presentation monitor active.")
        presentation_selector = self.selectors.get("presentation_area")
        if not presentation_selector:
            logger.warning("No presentation area selector configured. Slide capture disabled.")
            return

        while self._running:
            try:
                presentation_element = self.page.locator(presentation_selector)
                if await presentation_element.is_visible():
                    screenshot_bytes = await presentation_element.screenshot()
                    
                    current_hash = hash(screenshot_bytes)
                    if current_hash != self.last_slide_hash:
                        self.last_slide_hash = current_hash
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"slide_{timestamp}.png"
                        filepath = os.path.join(self.slides_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(screenshot_bytes)
                        
                        logger.info(f"Saved new presentation slide: {filepath}")
                        self.bus.publish("SlideCaptured", filepath)
            except Exception as e:
                logger.error(f"Error checking presentation slides: {e}")
                
            await asyncio.sleep(5)
