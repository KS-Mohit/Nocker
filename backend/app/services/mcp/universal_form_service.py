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
        
        prompt = f"""Find the element reference for: {target_description}

Look for button elements with names like "Next", "Continue", "Review", "Submit".
The snapshot contains elements with references like [ref=e123].

SNAPSHOT:
{snapshot[:20000]}

Return ONLY a JSON object with:
- "ref": the element reference (just the ID like "e123", not the full "[ref=e123]")
- "found": true/false
- "element_text": the button text you found

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
                # Clean ref if it contains [ref=...]
                if "[ref=" in ref:
                    ref = ref.replace("[ref=", "").replace("]", "")
                logger.info(f"Claude found ref: {ref} ({data.get('element_text', 'unknown')})")
                
                result = await self.mcp.click(element=target_description, ref=ref)
                return result.success
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {e}")
        
        return False
    
    async def _analyze_and_fill_form(self, snapshot: str, user_profile: Dict, job_details: Dict) -> List[Dict]:
        """Use Claude to analyze form from accessibility snapshot and determine what to fill"""
        
        # Check if snapshot actually contains form elements
        if not snapshot or len(snapshot) < 100:
            logger.warning("Snapshot too short, form may not have loaded yet")
            return []
        
        system = """You are an expert at filling job application forms. 
Analyze the accessibility snapshot and return a JSON array of form fields to fill.

The snapshot contains elements with references like [ref=e123]. Look for:
- textbox elements that are empty - use type "text"
- combobox elements (dropdowns with "Select an option") - use type "select"  
- radio buttons (Yes/No options) - use type "click" with the LABEL's ref (the generic element containing "Yes" or "No" text)
- required fields (marked with * or showing error messages)

For each field that needs input, provide:
- "ref": the element reference (e.g., "e123")
- "value": the value to enter or select
- "type": "text", "select", or "click"
- "label": field label for logging

CRITICAL FOR RADIO BUTTONS:
- Look for structure like: generic [ref=e1035]: radio "Yes" + generic [ref=e1036]: "Yes"
- Use the LABEL ref (e1036 in this example), NOT the parent ref (e1035)
- The label ref is the generic element that contains just the text "Yes" or "No"

Return ONLY a valid JSON array. Examples:
[{"ref": "e1036", "value": "Yes", "type": "click", "label": "Bachelor's Degree - Yes"}]
[{"ref": "e789", "value": "3", "type": "text", "label": "Years of Python experience"}]"""

        # Build work experience summary with dates for calculating years
        work_exp_summary = []
        for exp in user_profile.get('work_experience', [])[:3]:
            work_exp_summary.append(f"- {exp.get('title')} at {exp.get('company')} ({exp.get('start_date')} - {exp.get('end_date')})")
            if exp.get('technologies'):
                work_exp_summary.append(f"  Technologies: {', '.join(exp.get('technologies', []))}")
        
        # Get pre-answered Q&A pairs
        qa_pairs = user_profile.get('qa_pairs', {}) or {}
        qa_summary = ""
        if qa_pairs:
            qa_summary = "\n\nPRE-ANSWERED QUESTIONS (use these exact answers):\n"
            for q, a in list(qa_pairs.items())[:15]:
                qa_summary += f"Q: {q}\nA: {a}\n"
        
        prompt = f"""Analyze this form and provide field mappings.

SNAPSHOT (look for textbox, combobox, radio elements with [ref=]):
{snapshot[:15000]}

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Email: {user_profile.get('email', 'N/A')}
Phone: {user_profile.get('phone', 'N/A')}
Location: {user_profile.get('location', 'N/A')}
LinkedIn: {user_profile.get('linkedin_url', 'N/A')}
Skills: {', '.join(user_profile.get('skills', [])[:15])}

WORK EXPERIENCE (use dates to calculate years of experience):
{chr(10).join(work_exp_summary) if work_exp_summary else 'N/A'}

EDUCATION:
{user_profile.get('education', [{}])[0].get('degree', 'N/A') if user_profile.get('education') else 'N/A'}
{qa_summary}
JOB: {job_details.get('title', 'Unknown')} at {job_details.get('company', 'Unknown')}

IMPORTANT RULES:
1. For "years of experience with X" questions, check PRE-ANSWERED QUESTIONS first, otherwise estimate from work experience dates
2. For radio "Yes" elements for Yes/No questions - use type "click"
3. For textbox elements for experience questions - use type "text"  
4. For combobox/listbox for dropdowns - use type "select"
5. For Bachelor's Degree question - answer "Yes" if user has B.Tech/Bachelor's

Return ONLY valid JSON array (no explanation):"""

        response = await self._ask_claude(prompt, system=system, max_tokens=1500)
        
        try:
            clean = response.strip()
            logger.debug(f"Claude form analysis response: {clean[:300]}")
            
            # Remove markdown code blocks
            if clean.startswith("```"):
                clean = re.sub(r'^```\w*\n?', '', clean)
                clean = re.sub(r'\n?```$', '', clean)
            
            # Try to find JSON array in response
            if not clean.startswith("["):
                # Try to extract JSON array from response
                import re as regex
                match = regex.search(r'\[[\s\S]*\]', clean)
                if match:
                    clean = match.group()
            
            result = json.loads(clean)
            logger.info(f"Found {len(result)} fields to fill")
            return result
        except Exception as e:
            logger.error(f"Failed to parse form analysis: {e}")
            logger.debug(f"Raw response was: {response[:500]}")
            return []

    async def _answer_question(self, question: str, user_profile: Dict, job_details: Dict) -> str:
        """Use Claude to generate an answer for application questions"""
        
        # First check if we have a pre-answered Q&A pair
        qa_pairs = user_profile.get('qa_pairs', {}) or {}
        question_lower = question.lower().strip()
        
        # Direct match or close match
        for q, a in qa_pairs.items():
            if q.lower().strip() == question_lower:
                logger.info(f"Found exact Q&A match: {a}")
                return a
            # Fuzzy match for years of experience questions
            if "years" in question_lower and "experience" in question_lower:
                # Extract skill from question
                for skill in ['python', 'c++', 'sql', 'java', 'fastapi', 'machine learning', 
                              'docker', 'aws', 'azure', 'nlp', 'deep learning', 'tensorflow', 
                              'pytorch', 'langchain', 'react', 'javascript']:
                    if skill in question_lower and skill in q.lower():
                        logger.info(f"Found Q&A match for {skill}: {a}")
                        return a
        
        system = """You are helping fill out a job application. 
Give concise, professional answers based on the user's profile.
For years of experience questions, return just a number.
For yes/no questions, return just "Yes" or "No".
For text questions, keep answers brief (1-2 sentences max)."""

        # Build work experience summary with dates
        work_exp_summary = []
        for exp in user_profile.get('work_experience', [])[:3]:
            work_exp_summary.append(f"- {exp.get('title')} at {exp.get('company')} ({exp.get('start_date')} - {exp.get('end_date')})")
            if exp.get('technologies'):
                work_exp_summary.append(f"  Technologies: {', '.join(exp.get('technologies', []))}")

        prompt = f"""Answer this job application question based on the user profile.

QUESTION: {question}

USER PROFILE:
Name: {user_profile.get('full_name', 'N/A')}
Skills: {', '.join(user_profile.get('skills', [])[:15])}
Work Experience:
{chr(10).join(work_exp_summary) if work_exp_summary else 'N/A'}
Education: {json.dumps(user_profile.get('education', [])[:1], default=str)[:300]}

JOB: {job_details.get('title', 'Unknown')} at {job_details.get('company', 'Unknown')}

Answer (be concise, for years questions just return a number):"""

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
            
            await self.mcp.wait_for(time=4)  # Wait longer for modal
            logger.info("Apply button clicked")
            
            # Track previous snapshot to detect stuck pages
            prev_snapshot_hash = None
            stuck_count = 0  # Move outside loop
            
            # Process form pages
            for page_num in range(1, max_pages + 1):
                logger.info(f"Processing page {page_num}...")
                await self.mcp.wait_for(time=3)  # Wait for form to fully load
                
                # Try to get a good snapshot (retry if only errors)
                snapshot = ""
                for attempt in range(3):
                    snapshot_result = await self.mcp.get_snapshot()
                    snapshot = snapshot_result.content or ""
                    
                    # Check if snapshot has actual page content
                    if "[ref=" in snapshot or "button" in snapshot.lower() or "input" in snapshot.lower():
                        break
                    
                    logger.warning(f"Snapshot attempt {attempt+1} only has errors, retrying...")
                    await self.mcp.wait_for(time=2)
                
                page_text = snapshot
                
                # Log what we got - show actual page content, not just errors
                logger.debug(f"Snapshot length: {len(snapshot)}, has refs: {'[ref=' in snapshot}")
                
                # Find where actual page content starts (skip console messages)
                page_content_start = snapshot.find("- Page URL:")
                if page_content_start == -1:
                    page_content_start = snapshot.find("Page Snapshot:")
                if page_content_start == -1:
                    page_content_start = snapshot.find("```yaml")
                if page_content_start == -1:
                    page_content_start = snapshot.find("- generic [ref=")
                if page_content_start == -1:
                    page_content_start = snapshot.find("- dialog [ref=")  # Modal dialog
                if page_content_start == -1:
                    page_content_start = snapshot.find("[ref=")
                
                if page_content_start > 0:
                    page_preview = snapshot[page_content_start:page_content_start+2000]
                    logger.info(f"Page content: {page_preview}")
                    
                    # Also log if we see form elements
                    if "textbox" in snapshot.lower():
                        logger.info("Found textbox elements in snapshot")
                    if "radio" in snapshot.lower():
                        logger.info("Found radio elements in snapshot")
                    if "combobox" in snapshot.lower():
                        logger.info("Found combobox elements in snapshot")
                else:
                    # Log first part that isn't console errors
                    non_error_start = 0
                    for i, line in enumerate(snapshot.split('\n')):
                        if not line.startswith('-') and not 'console' in line.lower() and not 'error' in line.lower():
                            non_error_start = snapshot.find(line)
                            break
                    logger.warning(f"Page content unclear. Sample: {snapshot[non_error_start:non_error_start+500]}")
                
                # Check for success/completion FIRST
                success_indicators = ["application sent", "application submitted", "application complete", "your application was sent", "applied to"]
                if any(x in page_text.lower() for x in success_indicators):
                    logger.info("Application submitted successfully!")
                    return ApplicationResult(
                        success=True, status="submitted",
                        message="Application submitted successfully!",
                        form_responses=self.form_responses,
                        pages_processed=page_num
                    )
                
                # If still no good snapshot, try to continue anyway
                if "[ref=" not in snapshot:
                    logger.error("Could not get valid page snapshot with element refs")
                    # Try a direct click on common Next button patterns
                    logger.info("Attempting direct Next button click by text...")
                    result = await self.mcp.click_by_text("Next")
                    if result.success and "error" not in result.content.lower():
                        await self.mcp.wait_for(time=2)
                        continue
                    else:
                        logger.warning(f"Direct click failed, trying 'Continue': {result.error}")
                        result = await self.mcp.click_by_text("Continue")
                        if result.success:
                            await self.mcp.wait_for(time=2)
                            continue
                
                # Check if stuck on same page
                import hashlib
                snapshot_hash = hashlib.md5(snapshot[:1000].encode()).hexdigest()  # Use more of snapshot for hash
                
                if snapshot_hash == prev_snapshot_hash:
                    stuck_count += 1
                    logger.warning(f"Detected stuck on same page (count: {stuck_count})")
                    
                    if stuck_count >= 2:
                        # We've tried clicking Next multiple times - there must be required fields
                        logger.info("Multiple stuck attempts - forcing form analysis")
                        fields = await self._analyze_and_fill_form(snapshot, user_profile, job_details)
                        if fields:
                            for mapping in fields:
                                ref = mapping.get("ref", "")
                                value = mapping.get("value", "")
                                field_type = mapping.get("type", "text")
                                label = mapping.get("label", "Unknown")
                                
                                if not ref or not value:
                                    continue
                                
                                try:
                                    if field_type == "click":
                                        # For radio buttons, click the ref directly
                                        # The label ref (e.g., e1036 for "Yes") should work
                                        result = await self.mcp.click(element=label, ref=ref)
                                        if not result.success:
                                            # Try clicking the label text ref (usually ref+1)
                                            logger.info(f"Click failed, trying alternate ref")
                                            # Try incrementing ref number
                                            try:
                                                ref_num = int(ref.replace('e', ''))
                                                alt_ref = f"e{ref_num + 1}"
                                                result = await self.mcp.click(element=label, ref=alt_ref)
                                            except:
                                                pass
                                        logger.info(f"Clicked {label} (radio/checkbox)")
                                    elif field_type == "select":
                                        result = await self.mcp.select_option(element=label, ref=ref, value=str(value))
                                        # If select fails, try click (might be a radio button)
                                        if not result.success and "not a <select>" in str(result.error):
                                            logger.info(f"Select failed, trying click for {label}")
                                            result = await self.mcp.click(element=label, ref=ref)
                                    else:
                                        result = await self.mcp.type_text(element=label, ref=ref, text=str(value))
                                    
                                    if result.success:
                                        self.form_responses[label] = str(value)
                                        logger.info(f"Filled {label}: {str(value)[:50]}")
                                    else:
                                        logger.warning(f"Failed to fill {label}: {result.error}")
                                except Exception as e:
                                    logger.warning(f"Could not fill {label}: {e}")
                        
                        stuck_count = 0  # Reset after filling
                    
                    await self._analyze_and_click("Next button or Continue button or Review button", snapshot)
                    await self.mcp.wait_for(time=2)
                    continue
                else:
                    stuck_count = 0  # Reset when page changes
                    
                prev_snapshot_hash = snapshot_hash
                
                # Log snapshot preview for debugging
                logger.debug(f"Snapshot preview: {snapshot[:500]}")
                
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
                            # If select fails (not a <select> element), try click (might be radio button)
                            if not result.success and "not a <select>" in str(result.error):
                                logger.info(f"Select failed for {label}, trying click (likely radio button)")
                                result = await self.mcp.click(element=label, ref=ref)
                        elif field_type == "click":
                            # For radio buttons, click the ref directly
                            result = await self.mcp.click(element=label, ref=ref)
                            if not result.success:
                                # Try clicking the label text ref (usually ref+1)
                                logger.info(f"Click failed for {label}, trying alternate ref")
                                try:
                                    ref_num = int(ref.replace('e', ''))
                                    alt_ref = f"e{ref_num + 1}"
                                    result = await self.mcp.click(element=label, ref=alt_ref)
                                except:
                                    pass
                        else:
                            result = await self.mcp.type_text(element=label, ref=ref, text=str(value))
                        
                        if result.success:
                            self.form_responses[label] = str(value)
                            logger.info(f"Filled {label}: {str(value)[:50]}")
                        else:
                            logger.warning(f"Failed to fill {label}: {result.error}")
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