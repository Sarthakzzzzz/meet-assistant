import asyncio
import logging
import os
import datetime
import io
from PIL import Image
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
        self.last_slide_img = None
        self.speaker_last_text = {}
        self.committed_block_hashes = set()
        self.last_active_text = ""
        self.last_active_speaker = ""
        self.last_active_changed_time = 0.0
        self.last_active_committed = False

    async def start(self):
        """Starts Playwright, launches the browser and navigates to the meeting."""
        logger.info(f"Launching Playwright Chromium (headless={self.headless})...")
        self.playwright = await async_playwright().start()
        
        user_data_dir = os.path.join(os.getcwd(), "data", "browser_profile")
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Support running both natively and in Docker as root safely
        launch_args = []
        try:
            if os.getuid() == 0 or os.path.exists('/.dockerenv'):
                launch_args.extend(['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        except AttributeError:
            pass

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=self.headless,
            args=launch_args
        )
        
        self.page = self.context.pages[0]
        
        logger.info(f"Navigating to {self.platform} meeting: {self.meeting_url}")
        await self.page.goto(self.meeting_url, wait_until="commit")
        
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
                    logger.info("Automatically enabling Google Meet closed captions...")
                    await self.page.keyboard.press("c")
                    await asyncio.sleep(1)
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
                    logger.info("Automatically enabling Microsoft Teams closed captions...")
                    await self.page.click("body", force=True) # Ensure focus
                    await self.page.keyboard.press("Control+Shift+C")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error during automated Teams join: {e}")
        
        self.bus.subscribe("SendChat", self.handle_send_chat)
        
        self._running = True
        self._tasks.append(asyncio.create_task(self._monitor_chat()))
        self._tasks.append(asyncio.create_task(self._monitor_presentation()))
        self._tasks.append(asyncio.create_task(self._monitor_captions()))

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

    def _is_new_slide(self, current_bytes):
        try:
            current_img = Image.open(io.BytesIO(current_bytes)).convert("L").resize((32, 32))
            if self.last_slide_img is None:
                self.last_slide_img = current_img
                return True
            
            cur_data = list(current_img.getdata())
            last_data = list(self.last_slide_img.getdata())
            
            mean_diff = sum(abs(c - l) for c, l in zip(cur_data, last_data)) / len(cur_data)
            
            # A threshold of 15 (out of 255) detects slide layout changes while ignoring cursors or selects
            if mean_diff > 15:
                self.last_slide_img = current_img
                return True
            return False
        except Exception as e:
            logger.error(f"Error comparing slides: {e}")
            return False

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
                    
                    if self._is_new_slide(screenshot_bytes):
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

    def _get_new_suffix(self, old_str: str, new_str: str) -> str:
        if not old_str:
            return new_str
        if new_str.startswith(old_str):
            return new_str[len(old_str):].strip()
            
        old_words = old_str.split()
        new_words = new_str.split()
        
        max_overlap = 0
        for i in range(1, min(len(old_words), len(new_words)) + 1):
            old_slice = [w.lower() for w in old_words[-i:]]
            new_slice = [w.lower() for w in new_words[:i]]
            if old_slice == new_slice:
                max_overlap = i
                
        if max_overlap > 0:
            return " ".join(new_words[max_overlap:])
        return new_str

    def _parse_teams_captions(self, text: str):
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        parsed_blocks = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line looks like avatar initials (1-2 uppercase letters)
            is_initials = len(line) <= 2 and line.isupper() and line.isalpha()
            
            # If we see initials, the next line is the speaker name
            if is_initials and i + 1 < len(lines):
                speaker_name = lines[i+1]
                text_lines = []
                j = i + 2
                while j < len(lines):
                    next_line = lines[j]
                    if len(next_line) <= 2 and next_line.isupper() and next_line.isalpha():
                        break
                    text_lines.append(next_line)
                    j += 1
                
                parsed_blocks.append({
                    "speaker": speaker_name,
                    "text": " ".join(text_lines)
                })
                i = j
            else:
                # E.g. "Balaji Bodkhe" (no initials, or picture loaded instead)
                # A name line is typically 1-3 words, capitalized, no punctuation
                words = line.split()
                if len(words) <= 3 and all(w[0].isupper() for w in words if w.isalpha()) and not any(c in line for c in ".?!,"):
                    speaker_name = line
                    text_lines = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        next_words = next_line.split()
                        is_next_initials = len(next_line) <= 2 and next_line.isupper() and next_line.isalpha()
                        is_next_speaker = len(next_words) <= 3 and all(w[0].isupper() for w in next_words if w.isalpha()) and not any(c in next_line for c in ".?!,")
                        if is_next_initials or is_next_speaker:
                            break
                        text_lines.append(next_line)
                        j += 1
                    parsed_blocks.append({
                        "speaker": speaker_name,
                        "text": " ".join(text_lines)
                    })
                    i = j
                else:
                    # Treat as pure caption text
                    parsed_blocks.append({
                        "speaker": "Platform CC",
                        "text": line
                    })
                    i += 1
        return parsed_blocks

    async def _monitor_captions(self):
        """Scrapes live meeting captions from the DOM if enabled."""
        logger.info("Caption monitor active. Waiting for captions to appear...")
        caption_container = self.selectors.get("captions_container")
        caption_text_selector = self.selectors.get("captions_text")
        
        if not caption_container or not caption_text_selector:
            logger.warning("Caption selectors not configured. Captions disabled.")
            return

        last_caption = ""

        while self._running:
            try:
                containers = self.page.locator(caption_container)
                count = await containers.count()
                target_container = None
                
                # Find the actual visible caption container
                for i in range(count):
                    if await containers.nth(i).is_visible():
                        target_container = containers.nth(i)
                        break
                        
                if target_container:
                    # Get all visible text directly from the container
                    full_text = await target_container.inner_text()
                    
                    if self.platform == "microsoft_teams":
                        blocks = self._parse_teams_captions(full_text)
                        if blocks:
                            now = asyncio.get_event_loop().time()
                            
                            # 1. Commit all completed blocks (all except the last one)
                            for block in blocks[:-1]:
                                speaker = block["speaker"]
                                text = block["text"].strip()
                                if not text:
                                    continue
                                
                                block_id = f"{speaker}:{text}"
                                if block_id not in self.committed_block_hashes:
                                    last_text = self.speaker_last_text.get(speaker, "")
                                    new_text = self._get_new_suffix(last_text, text)
                                    if new_text and "Captions will be shown" not in new_text:
                                        logger.info(f"Committed CC (Completed): [{speaker}] {new_text}")
                                        self.bus.publish("PlatformCaption", {"speaker": speaker, "text": new_text})
                                        self.speaker_last_text[speaker] = text
                                    self.committed_block_hashes.add(block_id)
                            
                            # 2. Check the active block (the last one)
                            active_block = blocks[-1]
                            active_speaker = active_block["speaker"]
                            active_text = active_block["text"].strip()
                            
                            if active_text:
                                if active_speaker == self.last_active_speaker and active_text == self.last_active_text:
                                    # Text has not changed. Check if we should commit due to pause
                                    if not self.last_active_committed:
                                        if now - self.last_active_changed_time > 3.0:
                                            # Commit active block!
                                            last_text = self.speaker_last_text.get(active_speaker, "")
                                            new_text = self._get_new_suffix(last_text, active_text)
                                            if new_text and "Captions will be shown" not in new_text:
                                                logger.info(f"Committed CC (Pause): [{active_speaker}] {new_text}")
                                                self.bus.publish("PlatformCaption", {"speaker": active_speaker, "text": new_text})
                                                self.speaker_last_text[active_speaker] = active_text
                                            
                                            block_id = f"{active_speaker}:{active_text}"
                                            self.committed_block_hashes.add(block_id)
                                            self.last_active_committed = True
                                else:
                                    # Active text or speaker changed, reset tracking
                                    self.last_active_speaker = active_speaker
                                    self.last_active_text = active_text
                                    self.last_active_changed_time = now
                                    self.last_active_committed = False
                    else:
                        full_text = full_text.replace('\n', ' ').strip()
                        if full_text and full_text != last_caption and "Captions will be shown" not in full_text:
                            new_text = self._get_new_suffix(last_caption, full_text)
                            if new_text:
                                speaker = "Platform CC"
                                logger.info(f"Captured CC: [{speaker}] {new_text}")
                                self.bus.publish("PlatformCaption", {"speaker": speaker, "text": new_text})
                                last_caption = full_text
            except Exception as e:
                pass # Don't spam logs if captions just disappear/reappear
                
            await asyncio.sleep(1)
