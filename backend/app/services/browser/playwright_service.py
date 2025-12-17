from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from typing import Optional
from loguru import logger
from app.core.config import settings
import asyncio
from concurrent.futures import ThreadPoolExecutor


class PlaywrightService:
    """Base service for browser automation with Playwright"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _start_sync(self):
        """Initialize Playwright and launch browser (sync)"""
        logger.info("Starting Playwright browser...")
        self.playwright = sync_playwright().start()
        
        # Launch browser (Chromium)
        self.browser = self.playwright.chromium.launch(
            headless=settings.BROWSER_HEADLESS,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        # Create context with realistic settings
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Create page
        self.page = self.context.new_page()
        
        # Add stealth scripts
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("Browser started successfully")
    
    async def start(self):
        """Async wrapper for start"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._start_sync)
        
    def _close_sync(self):
        """Close browser (sync)"""
        logger.info("Closing browser...")
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Browser closed")
        
    async def close(self):
        """Async wrapper for close"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._close_sync)
        
    def _goto_sync(self, url: str, wait_until: str = "domcontentloaded"):
        """Navigate to URL (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        logger.info(f"Navigating to: {url}")
        self.page.goto(url, wait_until=wait_until, timeout=30000)
    
    async def goto(self, url: str, wait_until: str = "domcontentloaded"):
        """Async wrapper for goto"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._goto_sync, url, wait_until)
        
    def _screenshot_sync(self, path: str):
        """Take screenshot (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        self.page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot saved: {path}")
    
    async def screenshot(self, path: str):
        """Async wrapper for screenshot"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._screenshot_sync, path)
        
    def _wait_for_selector_sync(self, selector: str, timeout: int = 10000):
        """Wait for element (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        self.page.wait_for_selector(selector, timeout=timeout)
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000):
        """Async wrapper"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._wait_for_selector_sync, selector, timeout)
        
    def _click_sync(self, selector: str):
        """Click element (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        self.page.click(selector)
        logger.info(f"Clicked: {selector}")
    
    async def click(self, selector: str):
        """Async wrapper"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._click_sync, selector)
        
    def _fill_sync(self, selector: str, text: str):
        """Fill input (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        self.page.fill(selector, text)
        logger.info(f"Filled: {selector}")
    
    async def fill(self, selector: str, text: str):
        """Async wrapper"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._fill_sync, selector, text)
        
    def _get_text_sync(self, selector: str) -> str:
        """Get text (sync)"""
        if not self.page:
            raise Exception("Browser not started.")
        
        element = self.page.query_selector(selector)
        if element:
            return element.inner_text()
        return ""
    
    async def get_text(self, selector: str) -> str:
        """Async wrapper"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._get_text_sync, selector)