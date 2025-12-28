"""
Universal Form Filler Service

Works with ANY job application website, not just LinkedIn.
Uses MCP for browser automation and supports multiple LLM providers.

Supported Sites:
- LinkedIn (Easy Apply)
- Indeed
- Glassdoor
- Lever
- Greenhouse
- Workday
- Any custom career page
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger

from app.services.mcp.mcp_client import MCPClient, MCPResponse, get_mcp_client
from app.services.rag.rag_service import RAGService, get_rag_service


class JobSite(str, Enum):
    """Supported job application sites"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    WORKDAY = "workday"
    GENERIC = "generic"  # Fallback for unknown sites


class FormFieldType(str, Enum):
    """Types of form fields"""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    DATE = "date"
    PHONE = "phone"
    EMAIL = "email"


@dataclass
class FormField:
    """Represents a form field extracted from page snapshot"""
    ref: str
    field_type: FormFieldType
    label: str
    required: bool = False
    options: List[str] = field(default_factory=list)
    current_value: str = ""
    placeholder: str = ""


@dataclass 
class FormPage:
    """Represents a page/step in a multi-page form"""
    page_number: int
    fields: List[FormField]
    has_next: bool = False
    has_submit: bool = False
    next_button_ref: Optional[str] = None
    submit_button_ref: Optional[str] = None


@dataclass
class ApplicationResult:
    """Result of a form submission attempt"""
    success: bool
    status: str  # "submitted", "needs_review", "failed", "in_progress"
    message: str
    form_responses: Dict[str, str] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    error: Optional[str] = None
    pages_processed: int = 0


# =============================================================================
# LLM Provider Interface
# =============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def analyze_form(
        self,
        snapshot: str,
        user_profile: Dict,
        job_details: Dict
    ) -> List[Dict]:
        """Analyze form and return field mappings"""
        pass


class ClaudeProvider(LLMProvider):
    """Claude API provider - RECOMMENDED for production"""
    
    def __init__(self, api_key: Optional[str] = None):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    async def analyze_form(
        self,
        snapshot: str,
        user_profile: Dict,
        job_details: Dict
    ) -> List[Dict]:
        """Use Claude to analyze form and map fields to user data"""
        
        system_prompt = """You are an expert at analyzing web form accessibility snapshots and mapping form fields to user profile data.

Given a page snapshot and user profile, identify all fillable form fields and determine the appropriate value for each.

Return a JSON array of field mappings. Each mapping should have:
- ref: The element reference (e.g., "ref=s1e45")
- label: The field label/question
- value: The value to fill (from user profile or generated)
- field_type: One of "text", "select", "radio", "checkbox", "textarea"
- confidence: Your confidence in the mapping (high, medium, low)

For custom questions (not direct profile fields), generate professional, concise answers."""

        prompt = f"""Analyze this form and provide field mappings.

PAGE SNAPSHOT:
{snapshot[:8000]}  # Truncate to stay within limits

USER PROFILE:
{json.dumps(user_profile, indent=2)[:3000]}

JOB DETAILS:
Title: {job_details.get('title', 'Unknown')}
Company: {job_details.get('company', 'Unknown')}
Description: {job_details.get('description', '')[:1000]}

Return ONLY a valid JSON array of field mappings. No explanation, just JSON."""

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=2000
        )
        
        # Parse JSON from response
        try:
            # Clean up response (remove markdown code blocks if present)
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = re.sub(r'^```\w*\n?', '', clean_response)
                clean_response = re.sub(r'\n?```$', '', clean_response)
            
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Response was: {response[:500]}")
            return []


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider - FREE but lower quality"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        import httpx
        self.client = httpx.AsyncClient(timeout=120.0)
        self.base_url = base_url
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens}
        }
        if system_prompt:
            payload["system"] = system_prompt
        
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    
    async def analyze_form(
        self,
        snapshot: str,
        user_profile: Dict,
        job_details: Dict
    ) -> List[Dict]:
        """Use Ollama to analyze form - simpler prompt for local model"""
        
        prompt = f"""You are filling out a job application form.

FORM FIELDS (from accessibility snapshot):
{snapshot[:4000]}

USER INFO:
Name: {user_profile.get('full_name')}
Email: {user_profile.get('email')}
Phone: {user_profile.get('phone')}
Location: {user_profile.get('location')}

For each empty form field, provide the value to fill.
Return JSON array: [{{"ref": "ref=xxx", "label": "field name", "value": "value to fill"}}]

JSON ONLY:"""

        response = await self.generate(prompt, max_tokens=1500)
        
        try:
            clean = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except:
            return []


# =============================================================================
# Site-Specific Handlers
# =============================================================================

class SiteHandler(ABC):
    """Base class for site-specific form handling"""
    
    @abstractmethod
    def detect(self, url: str, snapshot: str) -> bool:
        """Check if this handler should be used for the given page"""
        pass
    
    @abstractmethod
    def find_apply_button(self, snapshot: str) -> Optional[str]:
        """Find the apply/submit button reference"""
        pass
    
    @abstractmethod
    def find_navigation_buttons(self, snapshot: str) -> Tuple[Optional[str], Optional[str]]:
        """Find next and submit button references"""
        pass
    
    @abstractmethod
    def is_success_page(self, snapshot: str) -> bool:
        """Check if we're on a success/confirmation page"""
        pass


class LinkedInHandler(SiteHandler):
    """Handler for LinkedIn Easy Apply"""
    
    def detect(self, url: str, snapshot: str) -> bool:
        return "linkedin.com" in url.lower()
    
    def find_apply_button(self, snapshot: str) -> Optional[str]:
        patterns = [
            r'button "Easy Apply".*?\[ref=([^\]]+)\]',
            r'button.*?Easy Apply.*?\[ref=([^\]]+)\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, snapshot, re.IGNORECASE)
            if match:
                return f"ref={match.group(1)}"
        return None
    
    def find_navigation_buttons(self, snapshot: str) -> Tuple[Optional[str], Optional[str]]:
        next_ref = None
        submit_ref = None
        
        # Find Submit
        submit_match = re.search(r'button "Submit.*?".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if submit_match:
            submit_ref = f"ref={submit_match.group(1)}"
        
        # Find Next
        next_match = re.search(r'button "(Next|Continue|Review)".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if next_match:
            next_ref = f"ref={next_match.group(2)}"
        
        return next_ref, submit_ref
    
    def is_success_page(self, snapshot: str) -> bool:
        indicators = ["application sent", "application submitted", "application complete"]
        return any(ind in snapshot.lower() for ind in indicators)


class IndeedHandler(SiteHandler):
    """Handler for Indeed applications"""
    
    def detect(self, url: str, snapshot: str) -> bool:
        return "indeed.com" in url.lower()
    
    def find_apply_button(self, snapshot: str) -> Optional[str]:
        patterns = [
            r'button "Apply.*?".*?\[ref=([^\]]+)\]',
            r'link "Apply.*?".*?\[ref=([^\]]+)\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, snapshot, re.IGNORECASE)
            if match:
                return f"ref={match.group(1)}"
        return None
    
    def find_navigation_buttons(self, snapshot: str) -> Tuple[Optional[str], Optional[str]]:
        next_ref = None
        submit_ref = None
        
        submit_match = re.search(r'button "(Submit|Apply|Send)".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if submit_match:
            submit_ref = f"ref={submit_match.group(2)}"
        
        next_match = re.search(r'button "(Continue|Next)".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if next_match:
            next_ref = f"ref={next_match.group(2)}"
        
        return next_ref, submit_ref
    
    def is_success_page(self, snapshot: str) -> bool:
        indicators = ["application submitted", "thank you for applying", "application received"]
        return any(ind in snapshot.lower() for ind in indicators)


class GenericHandler(SiteHandler):
    """Generic handler for unknown sites"""
    
    def detect(self, url: str, snapshot: str) -> bool:
        return True  # Fallback handler
    
    def find_apply_button(self, snapshot: str) -> Optional[str]:
        patterns = [
            r'button "(Apply|Submit Application|Start Application)".*?\[ref=([^\]]+)\]',
            r'link "(Apply|Apply Now|Submit)".*?\[ref=([^\]]+)\]',
        ]
        for pattern in patterns:
            match = re.search(pattern, snapshot, re.IGNORECASE)
            if match:
                return f"ref={match.group(2)}"
        return None
    
    def find_navigation_buttons(self, snapshot: str) -> Tuple[Optional[str], Optional[str]]:
        next_ref = None
        submit_ref = None
        
        # Generic submit patterns
        submit_match = re.search(r'button "(Submit|Apply|Send|Finish)".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if submit_match:
            submit_ref = f"ref={submit_match.group(2)}"
        
        # Generic next patterns
        next_match = re.search(r'button "(Next|Continue|Proceed|Save.*Continue)".*?\[ref=([^\]]+)\]', snapshot, re.I)
        if next_match:
            next_ref = f"ref={next_match.group(2)}"
        
        return next_ref, submit_ref
    
    def is_success_page(self, snapshot: str) -> bool:
        indicators = [
            "thank you",
            "application submitted",
            "application received",
            "we received your application",
            "application complete",
            "successfully submitted"
        ]
        return any(ind in snapshot.lower() for ind in indicators)


# =============================================================================
# Universal Form Service
# =============================================================================

class UniversalFormService:
    """
    Universal form filler that works with any job application website.
    
    Features:
    - Auto-detects job site type
    - Uses appropriate handler for each site
    - Supports multiple LLM providers (Claude, Ollama)
    - Uses RAG for context retrieval
    - Handles multi-page forms
    """
    
    # Site handlers in order of priority
    HANDLERS = [
        LinkedInHandler(),
        IndeedHandler(),
        GenericHandler(),  # Fallback
    ]
    
    def __init__(
        self,
        mcp_client: Optional[MCPClient] = None,
        llm_provider: Optional[LLMProvider] = None,
        rag_service: Optional[RAGService] = None,
        use_claude: bool = True,  # Default to Claude for better quality
        claude_api_key: Optional[str] = None
    ):
        self.mcp = mcp_client or get_mcp_client()
        self.rag = rag_service or get_rag_service()
        
        # Initialize LLM provider
        if llm_provider:
            self.llm = llm_provider
        elif use_claude:
            self.llm = ClaudeProvider(api_key=claude_api_key)
            logger.info("Using Claude API for form analysis")
        else:
            self.llm = OllamaProvider()
            logger.info("Using Ollama (local) for form analysis")
        
        # State
        self.current_handler: Optional[SiteHandler] = None
        self.form_responses: Dict[str, str] = {}
        self.screenshots: List[str] = []
    
    def _detect_site(self, url: str, snapshot: str) -> SiteHandler:
        """Detect which site we're on and return appropriate handler"""
        for handler in self.HANDLERS:
            if handler.detect(url, snapshot):
                logger.info(f"Detected site type: {handler.__class__.__name__}")
                return handler
        return GenericHandler()
    
    async def apply_to_job(
        self,
        job_url: str,
        user_profile: Dict,
        job_details: Dict,
        kb_id: Optional[int] = None,
        dry_run: bool = True,
        max_pages: int = 15
    ) -> ApplicationResult:
        """
        Apply to a job at any supported site.
        
        Args:
            job_url: URL of the job posting
            user_profile: User's profile data
            job_details: Job details (title, company, description)
            kb_id: Knowledge base ID for RAG (optional)
            dry_run: If True, won't click final submit
            max_pages: Maximum form pages to process
        """
        logger.info(f"🚀 Starting application: {job_details.get('title')} at {job_details.get('company')}")
        logger.info(f"📍 URL: {job_url}")
        
        try:
            # 1. Health check
            if not await self.mcp.health_check():
                return ApplicationResult(
                    success=False,
                    status="failed",
                    message="MCP Server not available",
                    error="Start the MCP server: npx @playwright/mcp@latest --port 8931"
                )
            
            # 2. Navigate to job page
            nav_result = await self.mcp.navigate(job_url)
            if not nav_result.success:
                return ApplicationResult(
                    success=False,
                    status="failed",
                    message="Failed to navigate to job page",
                    error=nav_result.error
                )
            
            await self.mcp.wait_for(time=2)
            
            # 3. Get initial snapshot and detect site
            snapshot = await self.mcp.get_snapshot()
            self.current_handler = self._detect_site(job_url, snapshot.content)
            
            # 4. Find and click apply button
            apply_ref = self.current_handler.find_apply_button(snapshot.content)
            if not apply_ref:
                await self.mcp.take_screenshot(filename="debug_no_apply_button.png")
                return ApplicationResult(
                    success=False,
                    status="failed",
                    message="Apply button not found",
                    error="Could not find apply button on this page",
                    screenshots=["debug_no_apply_button.png"]
                )
            
            await self.mcp.click(element="Apply button", ref=apply_ref)
            await self.mcp.wait_for(time=2)
            logger.info("✅ Apply button clicked, starting form...")
            
            # 5. Process form pages
            for page_num in range(1, max_pages + 1):
                logger.info(f"📄 Processing page {page_num}...")
                
                # Get current page snapshot
                snapshot = await self.mcp.get_snapshot()
                snapshot_text = snapshot.content
                
                # Check for success
                if self.current_handler.is_success_page(snapshot_text):
                    return ApplicationResult(
                        success=True,
                        status="submitted",
                        message="Application submitted successfully!",
                        form_responses=self.form_responses,
                        screenshots=self.screenshots,
                        pages_processed=page_num
                    )
                
                # Use LLM to analyze form and get field mappings
                field_mappings = await self._get_field_mappings(
                    snapshot_text,
                    user_profile,
                    job_details,
                    kb_id
                )
                
                # Fill each field
                for mapping in field_mappings:
                    await self._fill_field(mapping)
                
                # Find navigation buttons
                next_ref, submit_ref = self.current_handler.find_navigation_buttons(snapshot_text)
                
                if submit_ref:
                    if dry_run:
                        logger.info("🛑 DRY RUN: Would submit here")
                        await self.mcp.take_screenshot(filename="final_review.png")
                        return ApplicationResult(
                            success=True,
                            status="needs_review",
                            message="Dry run complete. Ready to submit.",
                            form_responses=self.form_responses,
                            screenshots=self.screenshots + ["final_review.png"],
                            pages_processed=page_num
                        )
                    else:
                        logger.info("📤 Submitting application...")
                        await self.mcp.click(element="Submit button", ref=submit_ref)
                        await self.mcp.wait_for(time=3)
                        
                        # Verify submission
                        final_snapshot = await self.mcp.get_snapshot()
                        if self.current_handler.is_success_page(final_snapshot.content):
                            return ApplicationResult(
                                success=True,
                                status="submitted",
                                message="Application submitted!",
                                form_responses=self.form_responses,
                                screenshots=self.screenshots,
                                pages_processed=page_num
                            )
                
                elif next_ref:
                    logger.info("➡️ Moving to next page...")
                    await self.mcp.click(element="Next button", ref=next_ref)
                    await self.mcp.wait_for(time=1.5)
                
                else:
                    # No navigation found - try Enter key
                    logger.warning("No navigation button found, pressing Enter...")
                    await self.mcp.press_key("Enter")
                    await self.mcp.wait_for(time=1.5)
            
            return ApplicationResult(
                success=False,
                status="failed",
                message="Maximum pages reached without submission",
                form_responses=self.form_responses,
                screenshots=self.screenshots,
                pages_processed=max_pages
            )
            
        except Exception as e:
            logger.error(f"❌ Application error: {e}")
            return ApplicationResult(
                success=False,
                status="failed",
                message="Application failed with error",
                error=str(e),
                form_responses=self.form_responses,
                screenshots=self.screenshots
            )
    
    async def _get_field_mappings(
        self,
        snapshot: str,
        user_profile: Dict,
        job_details: Dict,
        kb_id: Optional[int]
    ) -> List[Dict]:
        """Get field mappings using LLM + RAG"""
        
        # Enrich profile with RAG context if kb_id provided
        enriched_profile = user_profile.copy()
        
        if kb_id and self.rag:
            # Get relevant context for this job
            try:
                context = self.rag.retrieve_relevant_context(
                    question=f"Job: {job_details.get('title')} at {job_details.get('company')}",
                    kb_id=kb_id,
                    max_experiences=3,
                    max_projects=2,
                    max_skills=10
                )
                enriched_profile["rag_context"] = self.rag.build_context_string(context)
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
        
        # Use LLM to analyze form
        return await self.llm.analyze_form(snapshot, enriched_profile, job_details)
    
    async def _fill_field(self, mapping: Dict) -> bool:
        """Fill a single form field based on mapping"""
        ref = mapping.get("ref", "")
        label = mapping.get("label", "Unknown field")
        value = mapping.get("value", "")
        field_type = mapping.get("field_type", "text")
        
        if not ref or not value:
            return False
        
        # Ensure ref format
        if not ref.startswith("ref="):
            ref = f"ref={ref}"
        
        # Store response
        self.form_responses[label] = value
        
        try:
            if field_type in ["text", "textarea", "email", "phone"]:
                result = await self.mcp.type_text(
                    element=label,
                    ref=ref,
                    text=str(value)
                )
            elif field_type == "select":
                result = await self.mcp.select_option(
                    element=label,
                    ref=ref,
                    values=[str(value)]
                )
            elif field_type in ["radio", "checkbox"]:
                result = await self.mcp.click(
                    element=label,
                    ref=ref
                )
            else:
                result = await self.mcp.type_text(
                    element=label,
                    ref=ref,
                    text=str(value)
                )
            
            logger.info(f"{'✅' if result.success else '❌'} {label}: {value[:50]}...")
            return result.success
            
        except Exception as e:
            logger.error(f"Failed to fill {label}: {e}")
            return False


# =============================================================================
# Factory Functions
# =============================================================================

_universal_service: Optional[UniversalFormService] = None


def get_universal_form_service(
    use_claude: bool = True,
    claude_api_key: Optional[str] = None
) -> UniversalFormService:
    """Get or create universal form service"""
    global _universal_service
    if _universal_service is None:
        _universal_service = UniversalFormService(
            use_claude=use_claude,
            claude_api_key=claude_api_key
        )
    return _universal_service