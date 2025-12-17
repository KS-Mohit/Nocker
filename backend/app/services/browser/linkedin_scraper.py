from typing import Dict
from loguru import logger
import time
import os
import re
from app.services.browser.playwright_service import PlaywrightService


class LinkedInScraper(PlaywrightService):
    """Scrape job details from LinkedIn"""
    
    COOKIES_FILE = "linkedin_cookies.json"
    
    def _normalize_job_url(self, job_url: str) -> str:
        """Convert any LinkedIn job URL format to direct view URL"""
        
        # Extract job ID from URL
        patterns = [
            r'currentJobId=(\d+)',  # Collection URL
            r'/jobs/view/(\d+)',     # Direct view URL
            r'jobId=(\d+)',          # Other formats
        ]
        
        for pattern in patterns:
            match = re.search(pattern, job_url)
            if match:
                job_id = match.group(1)
                normalized_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                logger.info(f"Normalized URL: {normalized_url}")
                return normalized_url
        
        # If no match, return original
        logger.warning(f"Could not normalize URL: {job_url}")
        return job_url
    
    async def scrape_job(self, job_url: str, save_screenshot: bool = True) -> Dict:
        """
        Scrape job details from LinkedIn job posting
        
        Args:
            job_url: LinkedIn job URL (any format)
            save_screenshot: Whether to save a screenshot for debugging
            
        Returns:
            Dictionary with job details
        """
        # Normalize URL to direct view format
        job_url = self._normalize_job_url(job_url)
        
        await self.start()
        
        try:
            # Load cookies if available
            await self._load_cookies()
            
            # Navigate to job
            await self.goto(job_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Take screenshot for debugging
            screenshot_path = None
            if save_screenshot:
                screenshot_path = f"screenshot_{int(time.time())}.png"
                await self.screenshot(screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Extract job details
            job_data = await self._extract_job_details()
            job_data['screenshot_path'] = screenshot_path
            
            logger.info(f"✅ Successfully scraped job: {job_data.get('title', 'Unknown')}")
            return job_data
            
        except Exception as e:
            logger.error(f"Error scraping job: {e}")
            raise
        finally:
            await self.close()
    
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
    
    async def _extract_job_details(self) -> Dict:
        """Extract job details from the page"""
        job_data = {}
        
        try:
            # Job Title - updated selector
            title_selectors = [
                "h1.t-24.t-bold",
                "h1",
                ".job-details-jobs-unified-top-card__job-title"
            ]
            
            for selector in title_selectors:
                title = await self.get_text(selector)
                if title and title.strip():
                    job_data['title'] = title.strip()
                    logger.info(f"Title: {job_data['title']}")
                    break
            
            if not job_data.get('title'):
                job_data['title'] = None
                logger.warning("Could not extract title")
                
        except Exception as e:
            logger.warning(f"Could not extract title: {e}")
            job_data['title'] = None
        
        try:
            # Company Name - updated selector
            company_selectors = [
                ".job-details-jobs-unified-top-card__company-name a",
                ".job-details-jobs-unified-top-card__company-name",
                "a[data-tracking-control-name='public_jobs_topcard-org-name']"
            ]
            
            for selector in company_selectors:
                company = await self.get_text(selector)
                if company and company.strip():
                    job_data['company'] = company.strip()
                    logger.info(f"Company: {job_data['company']}")
                    break
            
            if not job_data.get('company'):
                job_data['company'] = None
                logger.warning("Could not extract company")
                
        except Exception as e:
            logger.warning(f"Could not extract company: {e}")
            job_data['company'] = None
        
        try:
            # Location - updated selector
            location_selectors = [
                ".job-details-jobs-unified-top-card__primary-description-container span.t-black--light",
                ".job-details-jobs-unified-top-card__bullet"
            ]
            
            for selector in location_selectors:
                location = await self.get_text(selector)
                if location and location.strip():
                    # Clean up location text (remove extra info)
                    location_parts = location.strip().split('·')[0]
                    job_data['location'] = location_parts.strip()
                    logger.info(f"Location: {job_data['location']}")
                    break
            
            if not job_data.get('location'):
                job_data['location'] = None
                logger.warning("Could not extract location")
                
        except Exception as e:
            logger.warning(f"Could not extract location: {e}")
            job_data['location'] = None
        
        try:
            # Job Description - updated selector
            desc_selectors = [
                ".jobs-description__content .jobs-description-content__text",
                ".show-more-less-html__markup",
                "#job-details"
            ]
            
            for selector in desc_selectors:
                description = await self.get_text(selector)
                if description and description.strip():
                    job_data['description'] = description.strip()
                    desc_preview = job_data['description'][:100] if job_data['description'] else "None"
                    logger.info(f"Description: {desc_preview}...")
                    break
            
            if not job_data.get('description'):
                job_data['description'] = None
                logger.warning("Could not extract description")
                
        except Exception as e:
            logger.warning(f"Could not extract description: {e}")
            job_data['description'] = None
        
        try:
            # Workplace Type (On-site/Remote/Hybrid) - from badges
            workplace_text = await self.get_text("span.ui-label:has-text('On-site'), span.ui-label:has-text('Remote'), span.ui-label:has-text('Hybrid')")
            job_data['workplace_type'] = workplace_text.strip() if workplace_text else None
            
        except Exception:
            job_data['workplace_type'] = None
        
        try:
            # Job Type (Full-time/Part-time) - from badges
            job_type_text = await self.get_text("span.ui-label:has-text('Full-time'), span.ui-label:has-text('Part-time'), span.ui-label:has-text('Contract')")
            job_data['job_type'] = job_type_text.strip() if job_type_text else None
            
        except Exception:
            job_data['job_type'] = None
        
        return job_data
    
    def _check_easy_apply_sync(self) -> bool:
        """Check if job has Easy Apply button (sync)"""
        try:
            if not self.page:
                return False
            easy_apply_button = self.page.query_selector(
                "button.jobs-apply-button, button:has-text('Easy Apply')"
            )
            return easy_apply_button is not None
        except Exception:
            return False
    
    async def check_easy_apply(self) -> bool:
        """Check if job has Easy Apply button"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._check_easy_apply_sync)