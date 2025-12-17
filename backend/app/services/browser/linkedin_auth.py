from typing import Optional
from loguru import logger
import time
import os
from app.services.browser.playwright_service import PlaywrightService


class LinkedInAuth(PlaywrightService):
    """Handle LinkedIn authentication"""
    
    COOKIES_FILE = "linkedin_cookies.json"
    
    async def login(self, email: str, password: str) -> bool:
        """
        Login to LinkedIn
        
        Args:
            email: LinkedIn email
            password: LinkedIn password
            
        Returns:
            True if login successful
        """
        await self.start()
        
        try:
            # Navigate to LinkedIn login
            await self.goto("https://www.linkedin.com/login")
            
            logger.info("Entering credentials...")
            
            # Fill login form
            await self.fill('input[name="session_key"]', email)
            await self.fill('input[name="session_password"]', password)
            
            # Click login button
            await self.click('button[type="submit"]')
            
            # Wait for redirect
            time.sleep(5)
            
            # Check if login successful
            current_url = self.page.url
            
            if "feed" in current_url or "mynetwork" in current_url:
                logger.info("Login successful!")
                
                # Save cookies for future use
                await self._save_cookies()
                
                return True
            else:
                logger.error("Login failed - might need 2FA or verification")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
        finally:
            await self.close()
    
    def _save_cookies_sync(self):
        """Save cookies to file (sync)"""
        if not self.context:
            return
        
        cookies = self.context.cookies()
        import json
        with open(self.COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"Cookies saved to {self.COOKIES_FILE}")
    
    async def _save_cookies(self):
        """Save cookies to file"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._save_cookies_sync)
    
    def _load_cookies_sync(self):
        """Load cookies from file (sync)"""
        if not os.path.exists(self.COOKIES_FILE):
            return False
        
        if not self.context:
            return False
        
        import json
        with open(self.COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
        
        self.context.add_cookies(cookies)
        logger.info(f"Cookies loaded from {self.COOKIES_FILE}")
        return True
    
    async def load_cookies(self) -> bool:
        """Load cookies from file"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._load_cookies_sync)
    
    async def is_logged_in(self) -> bool:
        """Check if currently logged in"""
        await self.start()
        
        try:
            # Try loading saved cookies
            cookies_loaded = await self.load_cookies()
            
            if not cookies_loaded:
                await self.close()
                return False
            
            # Navigate to LinkedIn
            await self.goto("https://www.linkedin.com/feed")
            
            time.sleep(3)
            
            # Check if on feed page (means logged in)
            current_url = self.page.url
            is_logged_in = "feed" in current_url
            
            await self.close()
            return is_logged_in
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            await self.close()
            return False