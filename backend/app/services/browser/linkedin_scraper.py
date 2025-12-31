from typing import Dict, Tuple, Optional
from loguru import logger
import time
import os
import re
import asyncio
from app.services.browser.playwright_service import PlaywrightService
from app.services.ai.ollama_service import OllamaService

class LinkedInScraper(PlaywrightService):
    """Scrape job details from LinkedIn using Visual AI (Text-as-Image)"""
    
    COOKIES_FILE = "linkedin_cookies.json"
    
    def __init__(self):
        super().__init__()
        # Initialize the AI service to handle the vision part
        self.ai_service = OllamaService()
    
    def _normalize_job_url(self, job_url: str) -> str:
        """Convert any LinkedIn job URL format to direct view URL"""
        
        # 1. Clean the input (remove markdown artifacts)
        clean_url = job_url.replace("[", "").replace("]", "").replace("(", "").replace(")", "").strip()
        
        patterns = [
            r'currentJobId=(\d+)',
            r'/jobs/view/(\d+)',
            r'jobId=(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_url)
            if match:
                job_id = match.group(1)
                normalized_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                logger.info(f"Normalized URL: {normalized_url}")
                return normalized_url
        
        logger.warning(f"Could not normalize URL: {clean_url}")
        return clean_url

    def _capture_visuals_sync(self, save_screenshot: bool) -> Tuple[bytes, Optional[str]]:
        """
        SYNC method to handle CSS injection and Screenshot.
        Must run in the same thread as the browser.
        """
        if not self.page:
            raise ValueError("Browser page is not initialized")

        # --- STEP 1: CSS Injection for Density ---
        logger.info("🎨 Optimizing page density for AI readability...")
        self.page.evaluate("""() => {
            // Remove clutter
            const selectorsToRemove = [
                'header', '.ad-banner', '#chat-container', 
                '.jobs-details__right-rail', 'aside', 'footer',
                '.similar-jobs', '.jobs-upsell', '.global-nav'
            ];
            selectorsToRemove.forEach(s => {
                const el = document.querySelector(s);
                if (el) el.style.display = 'none';
            });

            // Optimize readability for AI (High Contrast)
            document.body.style.backgroundColor = 'white';
            document.body.style.color = 'black';
            
            // Try to expand the description if there's a "Show more" button
            const showMoreBtn = document.querySelector('.jobs-description__footer-button');
            if(showMoreBtn) showMoreBtn.click();
        }""")
        
        # Brief wait for "Show more" expansion (Sync sleep is fine here as it's in a thread)
        time.sleep(1)

        # --- STEP 2: Capture Screenshot ---
        logger.info("📸 Capturing optimized screenshot for AI analysis...")
        screenshot_bytes = None
        
        try:
            # Try to target the main job card container
            screenshot_bytes = self.page.locator('.job-view-layout').screenshot()
        except Exception:
            # Fallback to full page
            logger.warning("Main job layout not found, taking full page screenshot.")
            screenshot_bytes = self.page.screenshot(full_page=True)
        
        # Save screenshot for debugging
        screenshot_path = None
        if save_screenshot:
            screenshot_path = f"screenshot_{int(time.time())}.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)
            logger.info(f"Screenshot saved: {screenshot_path}")

        return screenshot_bytes, screenshot_path
    
    async def scrape_job(self, job_url: str, save_screenshot: bool = True) -> Dict:
        """
        Scrape job details by taking a screenshot and sending it to AI.
        """
        job_url = self._normalize_job_url(job_url)
        
        await self.start()
        
        try:
            await self._load_cookies()
            await self.goto(job_url)
            
            # Wait for initial load
            time.sleep(4) 
            
            # --- CRITICAL FIX: Run CSS/Screenshot logic in the Executor ---
            # We cannot call self.page.evaluate directly here because we are in the wrong thread.
            loop = asyncio.get_event_loop()
            screenshot_bytes, screenshot_path = await loop.run_in_executor(
                self.executor, 
                self._capture_visuals_sync, 
                save_screenshot
            )
            
            # --- STEP 3: Send to Gemini (Visual Parsing) ---
            logger.info("🤖 Sending image to AI for extraction...")
            job_data = await self.ai_service.parse_job_screenshot(screenshot_bytes)
            
            # Add metadata
            job_data['url'] = job_url
            job_data['screenshot_path'] = screenshot_path
            
            logger.info(f"✅ Successfully scraped job: {job_data.get('title', 'Unknown')}")
            return job_data
            
        except Exception as e:
            logger.error(f"Error scraping job: {e}")
            raise
        finally:
            await self.close()
            await self.ai_service.close()
    
    def _load_cookies_sync(self):
        """Load cookies from file (sync)"""
        if not os.path.exists(self.COOKIES_FILE):
            logger.warning("No cookies file found. Please login first.")
            return
        
        if not self.context:
            return
        
        import json
        with open(self.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        
        self.context.add_cookies(cookies)
        logger.info(f"Cookies loaded from {self.COOKIES_FILE}")
    
    async def _load_cookies(self):
        """Load cookies from file"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._load_cookies_sync)

    async def check_easy_apply(self) -> bool:
        """
        Check if job has Easy Apply button. 
        """
        if not self.page:
            return False
            
        # We must also wrap this simple check because it uses self.page
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _check_sync():
            try:
                easy_apply_button = self.page.query_selector(
                    "button.jobs-apply-button, button:has-text('Easy Apply')"
                )
                return easy_apply_button is not None
            except Exception:
                return False

        return await loop.run_in_executor(self.executor, _check_sync)