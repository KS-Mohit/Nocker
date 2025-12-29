"""
MCP Client using FastMCP with stdio transport

Uses FastMCP to communicate with Microsoft Playwright MCP via stdio.
This is cleaner and more reliable than HTTP/SSE.

Requires: pip install fastmcp
Server: npx @playwright/mcp@latest --browser chrome --user-data-dir ./browser-data
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from loguru import logger
from dataclasses import dataclass
from enum import Enum

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logger.warning("MCP package not installed. Run: pip install mcp")


class MCPToolName(str, Enum):
    """Available MCP tools from Microsoft Playwright MCP"""
    NAVIGATE = "browser_navigate"
    CLICK = "browser_click"
    TYPE = "browser_type"
    SELECT = "browser_select_option"
    SNAPSHOT = "browser_snapshot"
    SCREENSHOT = "browser_take_screenshot"
    PRESS_KEY = "browser_press_key"
    UPLOAD_FILE = "browser_file_upload"
    CLOSE = "browser_close"


@dataclass
class MCPResponse:
    """Response from MCP tool call"""
    success: bool
    content: Any
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class MCPClient:
    """
    MCP Client using stdio transport via FastMCP.
    Spawns Microsoft Playwright MCP as subprocess.
    """
    
    def __init__(
        self,
        browser: str = "chrome",
        user_data_dir: str = "./browser-data",
        headless: bool = False
    ):
        self.browser = browser
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._session: Optional[ClientSession] = None
        self._client = None
        self._connected = False
        
        # For compatibility
        self.server_url = "stdio://playwright-mcp"
    
    async def connect(self) -> bool:
        """Connect to Playwright MCP via stdio"""
        if self._connected and self._session:
            return True
        
        if not HAS_MCP:
            logger.error("MCP package not installed. Run: pip install mcp")
            return False
        
        try:
            logger.info("Starting Playwright MCP via stdio...")
            
            # Build command args
            args = ["@playwright/mcp@latest"]
            args.extend(["--browser", self.browser])
            args.extend(["--user-data-dir", self.user_data_dir])
            if self.headless:
                args.append("--headless")
            
            server_params = StdioServerParameters(
                command="npx",
                args=args
            )
            
            # Create stdio client
            self._client = stdio_client(server_params)
            self._read, self._write = await self._client.__aenter__()
            
            # Create session
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            
            # Initialize
            await self._session.initialize()
            
            self._connected = True
            logger.info("Playwright MCP connected via stdio")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP"""
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._client:
            await self._client.__aexit__(None, None, None)
        self._connected = False
        self._session = None
        logger.info("Disconnected from Playwright MCP")
    
    async def call_tool(self, tool_name: str, arguments: Dict = None) -> MCPResponse:
        """Call an MCP tool"""
        if not self._connected:
            if not await self.connect():
                return MCPResponse(success=False, content=None, error="Not connected")
        
        try:
            result = await self._session.call_tool(tool_name, arguments or {})
            
            # Extract text content
            text_content = ""
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        text_content += item.text
            
            is_error = result.isError if hasattr(result, 'isError') else False
            
            return MCPResponse(
                success=not is_error,
                content=text_content or str(result),
                error=text_content if is_error else None
            )
            
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return MCPResponse(success=False, content=None, error=str(e))
    
    async def list_tools(self) -> List[Dict]:
        """List available tools"""
        if not self._connected:
            if not await self.connect():
                return []
        
        try:
            result = await self._session.list_tools()
            return [{"name": t.name, "description": t.description} for t in result.tools]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if MCP is available"""
        try:
            if not self._connected:
                return await self.connect()
            tools = await self.list_tools()
            return len(tools) > 0
        except:
            return False
    
    # High-level methods
    
    async def navigate(self, url: str) -> MCPResponse:
        """Navigate to a URL"""
        logger.info(f"Navigating: {url}")
        return await self.call_tool("browser_navigate", {"url": url})
    
    async def click(self, element: str, ref: str) -> MCPResponse:
        """Click on an element"""
        logger.info(f"Click: {element}")
        return await self.call_tool("browser_click", {"element": ref, "ref": ref})
    
    async def type_text(self, element: str, ref: str, text: str, submit: bool = False) -> MCPResponse:
        """Type text into an element"""
        logger.info(f"Type: {element}")
        params = {"element": ref, "ref": ref, "text": text}
        if submit:
            params["submit"] = True
        return await self.call_tool("browser_type", params)
    
    async def get_snapshot(self) -> MCPResponse:
        """Get accessibility snapshot of the page"""
        logger.info("Getting page snapshot")
        return await self.call_tool("browser_snapshot", {})
    
    async def take_screenshot(self, filename: Optional[str] = None, full_page: bool = False) -> MCPResponse:
        """Take a screenshot"""
        logger.info("Taking screenshot")
        params = {}
        if filename:
            params["filename"] = filename
        if full_page:
            params["fullPage"] = True
        return await self.call_tool("browser_take_screenshot", params)
    
    async def press_key(self, key: str) -> MCPResponse:
        """Press a keyboard key"""
        logger.info(f"Pressing key: {key}")
        return await self.call_tool("browser_press_key", {"key": key})
    
    async def upload_file(self, selector: str, file_path: str) -> MCPResponse:
        """Upload a file"""
        logger.info(f"Uploading file: {file_path}")
        return await self.call_tool("browser_file_upload", {"paths": [file_path]})
    
    async def select_option(self, element: str, ref: str, value: str) -> MCPResponse:
        """Select an option from dropdown"""
        logger.info(f"Select: {element} = {value}")
        return await self.call_tool("browser_select_option", {
            "element": ref,
            "ref": ref, 
            "values": [value]
        })
    
    async def wait_for(self, time: Optional[float] = None) -> MCPResponse:
        """Wait for a specified time"""
        if time:
            await asyncio.sleep(time)
        return MCPResponse(success=True, content="OK")
    
    async def close_browser(self) -> MCPResponse:
        """Close the browser"""
        logger.info("Closing browser")
        return await self.call_tool("browser_close", {})


# Singleton
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def shutdown_mcp_client():
    global _mcp_client
    if _mcp_client:
        await _mcp_client.disconnect()
        _mcp_client = None