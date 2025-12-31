from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import time
import asyncio
import os
import re
import json
from app.services.browser.playwright_service import PlaywrightService
from app.services.ai.ollama_service import OllamaService

class LinkedInFormFiller(PlaywrightService):
    """
    AI-Powered Form Filler using Vision (Gemini) + Playwright.
    """
    
    COOKIES_FILE = "linkedin_cookies.json"
    
    def __init__(self):
        super().__init__()
        self.ai_service = OllamaService()
    
    def _normalize_job_url(self, job_url: str) -> str:
        """Convert any LinkedIn job URL format to direct view URL to ensure consistent DOM"""
        # Clean the input
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
                return f"https://www.linkedin.com/jobs/view/{job_id}/"
        
        return clean_url

    async def apply_to_job(self, job_url: str, user_profile: Dict, job_details: Dict) -> Dict:
        """
        Main orchestration method for applying to a job.
        """
        # 1. Normalize URL to force the "Clean Layout"
        target_url = self._normalize_job_url(job_url)
        
        await self.start()
        
        try:
            # 2. Setup & Navigate
            await self._load_cookies()
            logger.info(f"🔗 Navigating to CLEAN job view: {target_url}")
            await self.goto(target_url)
            
            # 3. Click Easy Apply (With Retry & Wait)
            clicked = await self._click_easy_apply()
            
            if not clicked:
                await self._save_debug_screenshot()
                logger.error("❌ Easy Apply button missing. Saved 'debug_no_button.png'.")
                return {"success": False, "error": "No Easy Apply button found (Check debug_no_button.png)"}
            
            logger.info("✅ Easy Apply clicked. Starting Vision Form Loop...")
            
            # 4. The Vision Loop
            max_pages = 10
            page_count = 0
            
            while page_count < max_pages:
                page_count += 1
                logger.info(f"📄 Processing Form Page {page_count}...")
                
                # A. Capture State
                screenshot_bytes, form_status = await self._capture_form_state()
                
                # Check if we are done
                if form_status == "submitted":
                    return {"success": True, "message": "Application Submitted!"}

                # B. AI Analysis
                actions = await self.ai_service.analyze_form_screenshot(screenshot_bytes, user_profile)
                
                if not actions:
                    logger.warning("⚠️ AI found no actions. Attempting to force 'Next'...")
                    actions = [{"action": "click_button", "text": "Next"}]

                # C. Execute Actions
                result = await self._execute_actions(actions)
                
                if result == "submitted":
                     return {"success": True, "message": "Application Submitted!"}
                
                # Wait for next page transition
                time.sleep(3)

            return {"success": False, "error": "Max pages reached"}

        except Exception as e:
            logger.error(f"❌ Application Error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await self.close()
            await self.ai_service.close()

    # =========================================================================
    # SYNC HELPERS (Run in Executor)
    # =========================================================================

    def _click_easy_apply_sync(self) -> bool:
        """Find and click the Easy Apply button with Waiting"""
        if not self.page: return False
        
        # Robust selectors list
        selectors = [
            "button.jobs-apply-button",
            "button[aria-label*='Easy Apply']", 
            "button:has-text('Easy Apply')",
            ".jobs-apply-button--top-card button",
            # Fallback: Find any button that contains the text 'Easy Apply' inside it
            "button:has(.artdeco-button__text:has-text('Easy Apply'))"
        ]

        logger.info("👀 Looking for Easy Apply button...")
        
        # Try to find it for up to 10 seconds
        start_time = time.time()
        while time.time() - start_time < 10:
            for selector in selectors:
                try:
                    btn = self.page.query_selector(selector)
                    if btn and btn.is_visible():
                        logger.info(f"✅ Found button with selector: {selector}")
                        btn.click()
                        return True
                except:
                    continue
            time.sleep(1) # Wait a bit before retrying
        
        return False

    def _save_debug_screenshot_sync(self):
        if self.page:
            try:
                self.page.screenshot(path="debug_no_button.png")
            except Exception as e:
                logger.error(f"Failed to save debug screenshot: {e}")

    def _capture_form_state_sync(self) -> Tuple[Optional[bytes], str]:
        if not self.page: raise ValueError("Browser not active")
        
        # 1. Check for success indicators
        try:
            success_text = self.page.get_by_text("Application sent", exact=False)
            if success_text.count() > 0 and success_text.first.is_visible():
                return None, "submitted"
        except:
            pass

        # 2. Focus on the modal
        try:
            modal = self.page.locator(".jobs-easy-apply-content")
            if modal.count() > 0 and modal.first.is_visible():
                time.sleep(0.5) 
                return modal.first.screenshot(), "active"
            else:
                return self.page.screenshot(), "active"
        except:
            return self.page.screenshot(), "active"

    def _execute_actions_sync(self, actions: List[Dict]) -> str:
        if not self.page: return "error"
        
        for act in actions:
            action_type = act.get("action")
            label = act.get("label_text")
            value = act.get("value")
            text = act.get("text")

            try:
                if action_type == "fill":
                    logger.info(f"✍️ Filling '{label}' with '{value}'")
                    inp = self.page.get_by_label(label, exact=False)
                    if inp.count() == 0:
                        inp = self.page.get_by_placeholder(label, exact=False)
                    
                    if inp.count() > 0:
                        inp.first.fill(str(value))
                    else:
                        logger.warning(f"Field '{label}' not found.")

                elif action_type == "click":
                    logger.info(f"🔘 Clicking option '{label}'")
                    self.page.get_by_text(label, exact=True).first.click()

                elif action_type == "select":
                    logger.info(f"🔽 Selecting '{value}' for '{label}'")
                    try:
                        self.page.get_by_label(label, exact=False).select_option(label=value)
                    except:
                        self.page.get_by_label(label, exact=False).click()
                        time.sleep(0.5)
                        self.page.get_by_text(value, exact=True).first.click()

                elif action_type == "click_button":
                    btn_text = text
                    logger.info(f"👉 Clicking Button: {btn_text}")
                    if "Submit" in btn_text:
                        # UNCOMMENT TO APPLY
                        # self.page.get_by_role("button", name=btn_text, exact=False).click()
                        logger.info("🛑 SAFETY MODE: Would have submitted here.")
                        return "submitted"
                    else:
                        btn = self.page.get_by_role("button", name=btn_text, exact=False)
                        if btn.count() > 0:
                            btn.first.click()
                        else:
                            self.page.get_by_text(btn_text, exact=False).click()
            
            except Exception as e:
                logger.error(f"Failed to execute action {act}: {e}")
        
        return "continue"

    def _load_cookies_sync(self):
        if os.path.exists(self.COOKIES_FILE) and self.context:
            try:
                with open(self.COOKIES_FILE, 'r') as f:
                    self.context.add_cookies(json.load(f))
                logger.info("🍪 Cookies loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")

    # =========================================================================
    # ASYNC WRAPPERS
    # =========================================================================
    
    async def _click_easy_apply(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._click_easy_apply_sync)

    async def _save_debug_screenshot(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._save_debug_screenshot_sync)

    async def _capture_form_state(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._capture_form_state_sync)

    async def _execute_actions(self, actions):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._execute_actions_sync, actions)
    
    async def _load_cookies(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._load_cookies_sync)