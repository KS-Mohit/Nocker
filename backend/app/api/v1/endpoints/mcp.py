"""
MCP Application API Endpoints

Provides REST API for:
- MCP server health check
- Browser automation controls
"""

from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from app.services.mcp.mcp_client import get_mcp_client, MCPClient


router = APIRouter(prefix="/mcp", tags=["MCP Browser Automation"])


# ==========================================================================
# Request/Response Models
# ==========================================================================

class MCPHealthResponse(BaseModel):
    """MCP server health status"""
    healthy: bool
    server_url: str
    tools_available: int = 0
    message: str


class NavigateRequest(BaseModel):
    """Request to navigate browser"""
    url: str


class ClickRequest(BaseModel):
    """Request to click element"""
    element: str = Field(..., description="Human-readable element description")
    ref: str = Field(..., description="Element reference from snapshot (e.g., 'ref=s1e45')")


class TypeRequest(BaseModel):
    """Request to type text"""
    element: str
    ref: str
    text: str
    submit: bool = False


class SnapshotResponse(BaseModel):
    """Page snapshot response"""
    success: bool
    snapshot: Optional[str] = None
    error: Optional[str] = None


# ==========================================================================
# Health & Status Endpoints
# ==========================================================================

@router.get("/health", response_model=MCPHealthResponse)
async def check_mcp_health():
    """
    Check if the Playwright MCP server is running and healthy.
    
    The MCP server should be started separately with:
    ```
    npx @playwright/mcp@latest --port 8931 --user-data-dir ./browser-data
    ```
    """
    client = get_mcp_client()
    
    try:
        healthy = await client.health_check()
        
        if healthy:
            tools = await client.list_tools()
            return MCPHealthResponse(
                healthy=True,
                server_url=client.server_url,
                tools_available=len(tools),
                message=f"MCP server is running with {len(tools)} tools available"
            )
        else:
            return MCPHealthResponse(
                healthy=False,
                server_url=client.server_url,
                message="MCP server is not responding"
            )
    except Exception as e:
        return MCPHealthResponse(
            healthy=False,
            server_url=client.server_url,
            message=f"Error connecting to MCP server: {str(e)}"
        )


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools from the Playwright MCP server"""
    client = get_mcp_client()
    
    try:
        tools = await client.list_tools()
        return {
            "success": True,
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MCP server error: {str(e)}")


# ==========================================================================
# Login Check Endpoint
# ==========================================================================

@router.post("/login-check")
async def check_linkedin_login():
    """
    Check if we're currently logged into LinkedIn.
    
    Navigates to LinkedIn and checks for logged-in indicators.
    """
    client = get_mcp_client()
    
    try:
        # Navigate to LinkedIn
        await client.navigate("https://www.linkedin.com/feed/")
        await client.wait_for(time=2)
        
        # Get snapshot
        snapshot = await client.get_snapshot()
        
        # Check for login indicators
        logged_in_indicators = ["messaging", "my network", "notifications", "home"]
        logged_out_indicators = ["sign in", "join now", "log in"]
        
        snapshot_lower = snapshot.content.lower() if snapshot.content else ""
        
        is_logged_in = any(ind in snapshot_lower for ind in logged_in_indicators)
        is_logged_out = any(ind in snapshot_lower for ind in logged_out_indicators)
        
        if is_logged_in and not is_logged_out:
            return {
                "logged_in": True,
                "message": "You are logged into LinkedIn!",
                "ready_to_apply": True
            }
        else:
            return {
                "logged_in": False,
                "message": "Not logged into LinkedIn",
                "tip": "Navigate to LinkedIn login page and log in manually",
                "ready_to_apply": False
            }
            
    except Exception as e:
        return {
            "logged_in": False,
            "error": str(e),
            "tip": "Make sure MCP server is running"
        }


# ==========================================================================
# Low-Level Browser Control Endpoints
# ==========================================================================

@router.post("/navigate")
async def navigate_browser(request: NavigateRequest):
    """Navigate the browser to a URL"""
    client = get_mcp_client()
    result = await client.navigate(request.url)
    
    return {
        "success": result.success,
        "content": result.content,
        "error": result.error
    }


@router.get("/snapshot", response_model=SnapshotResponse)
async def get_page_snapshot():
    """
    Get the accessibility snapshot of the current page.
    
    This returns a structured text representation of the page that
    includes all interactive elements with their refs for automation.
    """
    client = get_mcp_client()
    result = await client.get_snapshot()
    
    return SnapshotResponse(
        success=result.success,
        snapshot=result.content if result.success else None,
        error=result.error
    )


@router.post("/click")
async def click_element(request: ClickRequest):
    """Click on an element by its ref"""
    client = get_mcp_client()
    result = await client.click(
        element=request.element,
        ref=request.ref
    )
    
    return {
        "success": result.success,
        "content": result.content,
        "error": result.error
    }


@router.post("/type")
async def type_text(request: TypeRequest):
    """Type text into an element"""
    client = get_mcp_client()
    result = await client.type_text(
        element=request.element,
        ref=request.ref,
        text=request.text,
        submit=request.submit
    )
    
    return {
        "success": result.success,
        "content": result.content,
        "error": result.error
    }


@router.post("/screenshot")
async def take_screenshot(filename: Optional[str] = None, full_page: bool = False):
    """Take a screenshot of the current page"""
    client = get_mcp_client()
    result = await client.take_screenshot(
        filename=filename,
        full_page=full_page
    )
    
    return {
        "success": result.success,
        "content": result.content,
        "error": result.error
    }


@router.post("/close")
async def close_browser():
    """Close the browser page"""
    client = get_mcp_client()
    result = await client.close_browser()
    
    return {
        "success": result.success,
        "message": "Browser closed" if result.success else result.error
    }


# ==========================================================================
# Utility Endpoints
# ==========================================================================

@router.get("/setup-guide")
async def get_setup_guide():
    """
    Get instructions for setting up the Playwright MCP server.
    """
    return {
        "title": "Playwright MCP Server Setup Guide",
        "steps": [
            {
                "step": 1,
                "title": "Install Node.js",
                "description": "Ensure Node.js 18+ is installed",
                "command": "node --version"
            },
            {
                "step": 2,
                "title": "Start MCP Server (Development)",
                "description": "Run in a separate terminal with persistent profile",
                "command": "npx @playwright/mcp@latest --port 8931 --user-data-dir ./browser-data"
            },
            {
                "step": 3,
                "title": "Start MCP Server (Headless)",
                "description": "For servers without display",
                "command": "npx @playwright/mcp@latest --port 8931 --headless --user-data-dir ./browser-data"
            },
            {
                "step": 4,
                "title": "Verify Server",
                "description": "Check if server is running",
                "endpoint": "GET /api/v1/mcp/health"
            },
            {
                "step": 5,
                "title": "Login to LinkedIn (Manual)",
                "description": "Navigate to LinkedIn and login manually once. Session will be saved.",
                "tip": "Use POST /api/v1/mcp/navigate with url='https://www.linkedin.com/login'"
            }
        ],
        "configuration": {
            "server_url": "http://localhost:8931",
            "persistent_profile": "./browser-data",
            "recommended_flags": [
                "--port 8931",
                "--user-data-dir ./browser-data",
                "--viewport-size 1920x1080"
            ]
        }
    }