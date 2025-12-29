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
        """Get page snapshot for Claude to analyze"""
        result = await self.mcp.get_snapshot()
        return result.content if result.success else ""
    
    async def _analyze_and_click(self, target_description: str, snapshot: str = None) -> bool:
        """Use Claude to find and click the right element from accessibility snapshot"""
        if not snapshot:
            snapshot = await self._get_html()
        
        prompt = f"""Analyze this accessibility snapshot and find the element reference for: {target_description}

The snapshot contains elements with references like [ref=s1e15]. Find the correct ref for the target element.

SNAPSHOT:
{snapshot[:12000]}

Return ONLY a JSON object with:
- "ref": the element reference (e.g., "s1e15" or the full "[ref=s1e15]")
- "found": true/false
- "element_text": brief description of what you found

JSON only, no explanation:"""

        response = await self._ask_claude(prompt, max_tokens=200)
        
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = re.sub(r'^```\w*\n?', '', clean)
                clean = re.sub(r'\n?```$', '', clean)
            
            data = json.loads(clean)
            
            if data.get("found") and data.get("ref"):
                ref = data["ref"]
                logger.info(f"Claude found ref: {ref}")
                
                result = await self.mcp.click(element=target_description, ref=ref)
                return result.success
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
        
        return False
    
    async def _analyze_and_fill_form(self, snapshot: str, user_profile: Dict, job_details: Dict) -> List[Dict]:
        """Use Claude to analyze form from accessibility snapshot and determine what to fill"""
        
        system = """You are an expert at filling job application forms. 
Analyze the accessibility snapshot and return a JSON array of form fields to fill.

The snapshot contains elements with references like [ref=s1e15]. Use these refs to identify fields.

For each field, provide:
- "ref": the element reference from the snapshot (e.g., "s1e15")
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

        prompt = f"""Analyze this form snapshot and provide field mappings.

SNAPSHOT:
{snapshot[:10000]}

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
            
            # Get page snapshot for Claude to analyze
            logger.info("Claude analyzing page to find apply button...")
            snapshot = await self._get_html()
            
            # Use Claude to find and click the Apply button
            clicked = await self._analyze_and_click(
                "Apply button - this could be 'Easy Apply', 'Apply Now', 'Apply', 'Submit Application', or similar button to start the job application process",
                snapshot
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
                
                snapshot = await self._get_html()
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
                        await self._analyze_and_click("Submit application button", snapshot)
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
                field_mappings = await self._analyze_and_fill_form(snapshot, user_profile, job_details)
                
                for mapping in field_mappings:
                    ref = mapping.get("ref", "")
                    value = mapping.get("value", "")
                    field_type = mapping.get("type", "text")
                    label = mapping.get("label", "Unknown field")
                    
                    if not ref or not value:
                        continue
                    
                    try:
                        if field_type == "text":
                            result = await self.mcp.type_text(element=label, ref=ref, text=str(value))
                        elif field_type == "select":
                            result = await self.mcp.select_option(element=label, ref=ref, value=str(value))
                        elif field_type == "click":
                            result = await self.mcp.click(element=label, ref=ref)
                        else:
                            result = await self.mcp.type_text(element=label, ref=ref, text=str(value))
                        
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
                    snapshot
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