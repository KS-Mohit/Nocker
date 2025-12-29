"""
Universal Form Filler Service - Claude AI Only

Uses Claude to:
1. Analyze pages and find correct selectors
2. Fill form fields intelligently
3. Answer application questions based on user profile
4. Handle multi-page forms automatically
"""

import re
import json
import asyncio
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import anthropic

from app.services.mcp.mcp_client import MCPClient, MCPResponse, get_mcp_client


class JobSite(str, Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GENERIC = "generic"


@dataclass
class ApplicationResult:
    success: bool
    status: str
    message: str
    form_responses: Dict[str, str] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    error: Optional[str] = None
    pages_processed: int = 0


class UniversalFormService:
    """
    Fully automated job application service using Claude AI.
    """
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        claude_api_key: Optional[str] = None,
        **kwargs
    ):
        self.mcp = mcp_client or get_mcp_client()
        
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = claude_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment")
            raise ValueError("ANTHROPIC_API_KEY is required. Set it in .env file or pass claude_api_key parameter")
        
        self.claude = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        
        self.form_responses: Dict[str, str] = {}
        self.screenshots: List[str] = []
        self.current_handler = None
        
        logger.info("Using Claude AI for intelligent form automation")
    
    async def _ask_claude(self, prompt: str, system: str = None, max_tokens: int = 1000) -> str:
        """Ask Claude a question"""
        try:
            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    async def _get_html(self) -> str:
        """Get page HTML for Claude to analyze"""
        result = await self.mcp.call_tool("playwright_get_visible_html", {
            "removeScripts": True,
            "removeStyles": True,
            "maxLength": 15000
        })
        return result.content if result.success else ""
    
    async def _analyze_and_click(self, target_description: str, html: str = None) -> bool:
        """Use Claude to find and click the right element"""
        if not html:
            html = await self._get_html()
        
        prompt = f"""Analyze this HTML and find the CSS selector for: {target_description}

HTML:
{html[:12000]}

Return ONLY a JSON object with:
- "selector": the CSS selector to click (be specific, prefer classes and IDs)
- "found": true/false

Examples of good selectors:
- "button.jobs-apply-button" for LinkedIn Easy Apply
- "button[aria-label*='Next']" for Next buttons
- "button.artdeco-button--primary" for primary buttons

JSON only, no explanation:"""

        response = await self._ask_claude(prompt, max_tokens=200)
        
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = re.sub(r'^```\w*\n?', '', clean)
                clean = re.sub(r'\n?```$', '', clean)
            
            data = json.loads(clean)
            
            if data.get("found") and data.get("selector"):
                selector = data["selector"]
                logger.info(f"Claude found selector: {selector}")
                
                result = await self.mcp.click(element=target_description, ref=selector)
                return result.success
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
        
        return False
    
    async def _analyze_and_fill_form(self, html: str, user_profile: Dict, job_details: Dict) -> List[Dict]:
        """Use Claude to analyze form and determine what to fill"""
        
        system = """You are an expert at filling job application forms. 
Analyze the HTML and return a JSON array of form fields to fill.

For each field, provide:
- "selector": CSS selector for the input
- "value": value to fill from the user profile
- "type": "text", "select", or "click"
- "label": field label for logging

Be smart about matching:
- Phone fields get phone number (without country code if separate)
- Email fields get email
- Name fields get appropriate name parts
- Experience questions get relevant years based on profile
- Use the user's actual data, don't make things up

Return ONLY valid JSON array."""

        prompt = f"""Analyze this form and provide field mappings.

HTML:
{html[:10000]}

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Email: {user_profile.get('email', 'N/A')}
Phone: {user_profile.get('phone', 'N/A')}
Location: {user_profile.get('location', 'N/A')}
LinkedIn: {user_profile.get('linkedin_url', 'N/A')}
Summary: {user_profile.get('summary', 'N/A')[:500] if user_profile.get('summary') else 'N/A'}
Skills: {', '.join(user_profile.get('skills', [])[:15])}
Experience: {json.dumps(user_profile.get('work_experience', [])[:2], default=str)[:1000]}

JOB:
Title: {job_details.get('title', 'Unknown')}
Company: {job_details.get('company', 'Unknown')}

Return JSON array of fields to fill:"""

        response = await self._ask_claude(prompt, system=system, max_tokens=2000)
        
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = re.sub(r'^```\w*\n?', '', clean)
                clean = re.sub(r'\n?```$', '', clean)
            
            return json.loads(clean)
        except Exception as e:
            logger.error(f"Failed to parse form analysis: {e}")
            return []

    async def _answer_question(self, question: str, user_profile: Dict, job_details: Dict) -> str:
        """Use Claude to generate an answer for application questions"""
        
        system = """You are helping fill out a job application. 
Give concise, professional answers based on the user's profile.
For years of experience questions, return just a number.
For yes/no questions, return just "Yes" or "No".
For text questions, keep answers brief (1-2 sentences max)."""

        prompt = f"""Answer this job application question based on the user profile.

QUESTION: {question}

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Skills: {', '.join(user_profile.get('skills', [])[:10])}
Experience: {json.dumps(user_profile.get('work_experience', [])[:2], default=str)[:800]}
Education: {json.dumps(user_profile.get('education', [])[:1], default=str)[:300]}

JOB: {job_details.get('title', 'Unknown')} at {job_details.get('company', 'Unknown')}

Answer (be concise):"""

        response = await self._ask_claude(prompt, system=system, max_tokens=200)
        return response.strip()
    
    async def apply_to_job(
        self,
        job_url: str,
        user_profile: Dict,
        job_details: Dict,
        kb_id: Optional[int] = None,
        dry_run: bool = True,
        max_pages: int = 10,
        resume_path: Optional[str] = None
    ) -> ApplicationResult:
        """
        Fully automated job application using Claude AI.
        """
        logger.info(f"Starting application: {job_details.get('title')} at {job_details.get('company')}")
        logger.info(f"URL: {job_url}")
        
        try:
            # Health check
            if not await self.mcp.health_check():
                return ApplicationResult(
                    success=False, status="failed",
                    message="MCP Server not available",
                    error="Start MCP: npx @executeautomation/playwright-mcp-server --port 8931"
                )
            
            # Navigate to job
            logger.info("Navigating to job page...")
            nav_result = await self.mcp.navigate(job_url)
            if not nav_result.success:
                return ApplicationResult(
                    success=False, status="failed",
                    message="Failed to navigate", error=nav_result.error
                )
            
            await self.mcp.wait_for(time=3)
            
            # Get page HTML for Claude to analyze
            logger.info("Claude analyzing page to find apply button...")
            html = await self._get_html()
            
            # Use Claude to find and click the Apply button
            clicked = await self._analyze_and_click(
                "Apply button - this could be 'Easy Apply', 'Apply Now', 'Apply', 'Submit Application', or similar button to start the job application process",
                html
            )
            
            if not clicked:
                return ApplicationResult(
                    success=False, status="failed",
                    message="Could not find apply button",
                    error="Claude couldn't identify the apply button. Try a different job posting."
                )
            
            await self.mcp.wait_for(time=2)
            logger.info("Apply button clicked")
            
            # Process form pages
            for page_num in range(1, max_pages + 1):
                logger.info(f"Processing page {page_num}...")
                await self.mcp.wait_for(time=1.5)
                
                html = await self._get_html()
                text_result = await self.mcp.get_snapshot()
                page_text = text_result.content or ""
                
                # Check for success
                if any(x in page_text.lower() for x in ["application sent", "application submitted", "application complete"]):
                    logger.info("Application submitted successfully")
                    return ApplicationResult(
                        success=True, status="submitted",
                        message="Application submitted successfully!",
                        form_responses=self.form_responses,
                        pages_processed=page_num
                    )
                
                # Check if on review page
                is_review_page = "review your application" in page_text.lower() or "submit application" in page_text.lower()
                
                if is_review_page:
                    if dry_run:
                        logger.info("DRY RUN: Stopping at review page")
                        return ApplicationResult(
                            success=True, status="needs_review",
                            message="Dry run complete - ready to submit!",
                            form_responses=self.form_responses,
                            pages_processed=page_num
                        )
                    else:
                        logger.info("Submitting application...")
                        await self._analyze_and_click("Submit application button", html)
                        await self.mcp.wait_for(time=3)
                        
                        return ApplicationResult(
                            success=True, status="submitted",
                            message="Application submitted!",
                            form_responses=self.form_responses,
                            pages_processed=page_num
                        )
                
                # Handle resume upload
                if "upload resume" in page_text.lower() or "resume" in page_text.lower()[:500]:
                    if resume_path:
                        logger.info(f"Uploading resume: {resume_path}")
                        upload_result = await self.mcp.upload_file(
                            selector="input[type='file']",
                            file_path=resume_path
                        )
                        if upload_result.success:
                            logger.info("Resume uploaded")
                        else:
                            logger.warning(f"Resume upload may need manual intervention: {upload_result.error}")
                    else:
                        logger.warning("Resume required but no path provided")
                
                # Use Claude to analyze and fill form fields
                logger.info("Claude analyzing form fields...")
                field_mappings = await self._analyze_and_fill_form(html, user_profile, job_details)
                
                for mapping in field_mappings:
                    selector = mapping.get("selector", "")
                    value = mapping.get("value", "")
                    field_type = mapping.get("type", "text")
                    label = mapping.get("label", "Unknown field")
                    
                    if not selector or not value:
                        continue
                    
                    try:
                        if field_type == "text":
                            result = await self.mcp.type_text(element=label, ref=selector, text=str(value))
                        elif field_type == "select":
                            result = await self.mcp.call_tool("playwright_select", {
                                "selector": selector,
                                "value": str(value)
                            })
                        elif field_type == "click":
                            result = await self.mcp.click(element=label, ref=selector)
                        else:
                            result = await self.mcp.type_text(element=label, ref=selector, text=str(value))
                        
                        if result.success:
                            self.form_responses[label] = str(value)
                            logger.info(f"Filled {label}: {str(value)[:50]}")
                    except Exception as e:
                        logger.warning(f"Could not fill {label}: {e}")
                
                # Answer any questions using Claude
                questions = re.findall(r'How many years.*?\?|Do you have.*?\?|Are you.*?\?|What is your.*?\?', page_text, re.I)
                for question in questions[:5]:
                    if question not in self.form_responses:
                        answer = await self._answer_question(question, user_profile, job_details)
                        self.form_responses[question] = answer
                        logger.info(f"Q: {question[:50]}... A: {answer}")
                
                # Use Claude to find and click Next button
                logger.info("Looking for Next button...")
                next_clicked = await self._analyze_and_click(
                    "Next, Continue, or Review button to proceed to the next step",
                    html
                )
                
                if not next_clicked:
                    logger.warning("Could not find Next button")
                
                await self.mcp.wait_for(time=1.5)
            
            return ApplicationResult(
                success=False, status="incomplete",
                message="Max pages reached",
                form_responses=self.form_responses,
                pages_processed=max_pages
            )
            
        except Exception as e:
            logger.error(f"Application error: {e}")
            return ApplicationResult(
                success=False, status="failed",
                message="Application error",
                error=str(e),
                form_responses=self.form_responses
            )


_service: Optional[UniversalFormService] = None

def get_universal_form_service(use_claude: bool = True, claude_api_key: Optional[str] = None) -> UniversalFormService:
    global _service
    if _service is None:
        _service = UniversalFormService(claude_api_key=claude_api_key)
    return _service