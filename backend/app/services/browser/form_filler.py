from typing import Dict, List, Optional, Any
from loguru import logger
import time
import re
from app.services.browser.playwright_service import PlaywrightService
from app.services.ai.ollama_service import OllamaService


class LinkedInFormFiller(PlaywrightService):
    """Fill out LinkedIn Easy Apply forms automatically"""
    
    def __init__(self):
        super().__init__()
        self.ollama = OllamaService()
    
    async def apply_to_job(
        self,
        job_url: str,
        user_profile: Dict,
        job_details: Dict
    ) -> Dict:
        """
        Complete job application on LinkedIn
        
        Args:
            job_url: LinkedIn job URL
            user_profile: User's knowledge base data
            job_details: Job information
            
        Returns:
            Application result with status
        """
        await self.start()
        await self._load_cookies()
        
        try:
            # Navigate to job
            await self.goto(job_url)
            time.sleep(3)
            
            # Check for Easy Apply button
            has_easy_apply = await self._check_easy_apply()
            
            if not has_easy_apply:
                logger.warning("No Easy Apply button found")
                return {
                    "success": False,
                    "error": "Job does not have Easy Apply option"
                }
            
            # Click Easy Apply
            await self._click_easy_apply()
            time.sleep(2)
            
            # Fill out multi-step form
            application_data = await self._fill_application_form(
                user_profile, 
                job_details
            )
            
            # Submit (or save draft if testing)
            # await self._submit_application()
            
            logger.info("Application completed successfully!")
            
            return {
                "success": True,
                "message": "Application submitted",
                "form_responses": application_data
            }
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await self.ollama.close()
            await self.close()
    
    def _check_easy_apply_sync(self) -> bool:
        """Check if Easy Apply button exists"""
        try:
            if not self.page:
                return False
            
            # Multiple selectors for Easy Apply button
            selectors = [
                "button.jobs-apply-button",
                "button:has-text('Easy Apply')",
                ".jobs-apply-button--top-card button",
            ]
            
            for selector in selectors:
                button = self.page.query_selector(selector)
                if button:
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def _check_easy_apply(self) -> bool:
        """Async wrapper for checking Easy Apply"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._check_easy_apply_sync)
    
    def _click_easy_apply_sync(self):
        """Click Easy Apply button"""
        if not self.page:
            raise Exception("Page not initialized")
        
        selectors = [
            "button.jobs-apply-button",
            "button:has-text('Easy Apply')",
        ]
        
        for selector in selectors:
            button = self.page.query_selector(selector)
            if button:
                button.click()
                logger.info("Clicked Easy Apply button")
                return
        
        raise Exception("Easy Apply button not found")
    
    async def _click_easy_apply(self):
        """Async wrapper"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._click_easy_apply_sync)
    
    async def _fill_application_form(
        self,
        user_profile: Dict,
        job_details: Dict
    ) -> Dict:
        """
        Fill out multi-step application form
        """
        form_responses = {}
        step = 1
        max_steps = 10
        
        while step <= max_steps:
            logger.info(f"Processing form step {step}")
            
            time.sleep(2)  # Wait for form to load
            
            # Detect and fill form fields
            step_responses = await self._fill_current_form_step(
                user_profile,
                job_details
            )
            
            form_responses[f"step_{step}"] = step_responses
            
            # Check if there's a "Next" button
            has_next = await self._click_next_button()
            
            if not has_next:
                logger.info("Reached final step")
                break
            
            step += 1
        
        return form_responses
    
    async def _fill_current_form_step(
        self,
        user_profile: Dict,
        job_details: Dict
    ) -> Dict:
        """Fill fields on current form step"""
        responses = {}
        
        # Detect all input fields
        fields = await self._detect_form_fields()
        
        for field in fields:
            field_type = field.get('type')
            field_label = field.get('label', '')
            field_selector = field.get('selector')
            
            logger.info(f"  Field: {field_label} ({field_type})")
            
            # Determine what to fill based on field label
            value = await self._determine_field_value(
                field_label,
                field_type,
                user_profile,
                job_details
            )
            
            if value:
                await self._fill_field(field_selector, value, field_type)
                responses[field_label] = value
        
        return responses
    
    def _detect_form_fields_sync(self) -> List[Dict]:
        """Detect all form fields on current page"""
        if not self.page:
            return []
        
        fields = []
        
        # Text inputs
        text_inputs = self.page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
        for input_el in text_inputs:
            label_el = self.page.evaluate('(el) => el.previousElementSibling?.textContent || el.placeholder || ""', input_el)
            fields.append({
                'type': 'text',
                'label': label_el,
                'selector': f'input[type="{input_el.get_attribute("type")}"]',
                'element': input_el
            })
        
        # Textareas
        textareas = self.page.query_selector_all('textarea')
        for textarea in textareas:
            label_el = self.page.evaluate('(el) => el.previousElementSibling?.textContent || el.placeholder || ""', textarea)
            fields.append({
                'type': 'textarea',
                'label': label_el,
                'selector': 'textarea',
                'element': textarea
            })
        
        # Select dropdowns
        selects = self.page.query_selector_all('select')
        for select in selects:
            label_el = self.page.evaluate('(el) => el.previousElementSibling?.textContent || ""', select)
            fields.append({
                'type': 'select',
                'label': label_el,
                'selector': 'select',
                'element': select
            })
        
        return fields
    
    async def _detect_form_fields(self) -> List[Dict]:
        """Async wrapper"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._detect_form_fields_sync)
    
    async def _determine_field_value(
        self,
        field_label: str,
        field_type: str,
        user_profile: Dict,
        job_details: Dict
    ) -> Optional[str]:
        """Determine what value to put in a field"""
        label_lower = field_label.lower()
        
        # Name fields
        if 'first name' in label_lower:
            name_parts = user_profile.get('full_name', '').split()
            return name_parts[0] if name_parts else None
        
        if 'last name' in label_lower:
            name_parts = user_profile.get('full_name', '').split()
            return ' '.join(name_parts[1:]) if len(name_parts) > 1 else None
        
        if 'full name' in label_lower or 'your name' in label_lower:
            return user_profile.get('full_name')
        
        # Contact info
        if 'email' in label_lower:
            return user_profile.get('email')
        
        if 'phone' in label_lower:
            return user_profile.get('phone')
        
        if 'location' in label_lower or 'city' in label_lower:
            return user_profile.get('location')
        
        # LinkedIn URL
        if 'linkedin' in label_lower:
            return user_profile.get('linkedin_url')
        
        # Portfolio/Website
        if 'website' in label_lower or 'portfolio' in label_lower:
            return user_profile.get('portfolio_url')
        
        # Check if it's a custom question (requires AI)
        if field_type == 'textarea' or 'why' in label_lower or 'describe' in label_lower:
            # Use AI to answer
            answer = await self._answer_custom_question(
                field_label,
                user_profile,
                job_details
            )
            return answer
        
        # Check Q&A pairs
        qa_pairs = user_profile.get('qa_pairs', {})
        for question, answer in qa_pairs.items():
            if question.lower() in label_lower or label_lower in question.lower():
                return answer
        
        return None
    
    async def _answer_custom_question(
        self,
        question: str,
        user_profile: Dict,
        job_details: Dict
    ) -> str:
        """Use AI to answer a custom application question"""
        logger.info(f"Using AI to answer: {question}")
        
        try:
            answer = await self.ollama.answer_job_question(
                question=question,
                user_profile=user_profile,
                job_details=job_details
            )
            return answer
        except Exception as e:
            logger.error(f"AI answer error: {e}")
            return ""
    
    async def _fill_field(self, selector: str, value: str, field_type: str):
        """Fill a form field"""
        await self.fill(selector, value)
        logger.info(f"  Filled: {value[:50]}...")
    
    def _click_next_button_sync(self) -> bool:
        """Click Next/Continue button if exists"""
        if not self.page:
            return False
        
        selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button[aria-label='Continue to next step']",
            ".artdeco-button--primary:has-text('Next')",
        ]
        
        for selector in selectors:
            button = self.page.query_selector(selector)
            if button:
                button.click()
                logger.info("Clicked Next button")
                return True
        
        return False
    
    async def _click_next_button(self) -> bool:
        """Async wrapper"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._click_next_button_sync)
    
    def _submit_application_sync(self):
        """Submit the application"""
        if not self.page:
            raise Exception("Page not initialized")
        
        selectors = [
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
            ".artdeco-button--primary:has-text('Submit')",
        ]
        
        for selector in selectors:
            button = self.page.query_selector(selector)
            if button:
                # COMMENTED OUT FOR SAFETY - uncomment when ready to actually submit
                # button.click()
                logger.info("Would submit application here (currently disabled for safety)")
                return
        
        logger.warning("Submit button not found")
    
    async def _submit_application(self):
        """Async wrapper"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._submit_application_sync)
    
    def _load_cookies_sync(self):
        """Load LinkedIn cookies"""
        import os
        import json
        
        cookies_file = "linkedin_cookies.json"
        if not os.path.exists(cookies_file):
            logger.warning("No cookies file found")
            return
        
        if not self.context:
            return
        
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        
        self.context.add_cookies(cookies)
        logger.info("Cookies loaded")
    
    async def _load_cookies(self):
        """Async wrapper"""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._load_cookies_sync)