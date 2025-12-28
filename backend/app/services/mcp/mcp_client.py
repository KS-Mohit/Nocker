"""
MCP Client with Persistent SSE Connection

The MCP SSE protocol requires:
1. SSE connection stays OPEN for the entire session
2. Messages are sent via HTTP POST while SSE is open
3. Responses come back via the SSE stream

Server: npx @executeautomation/playwright-mcp-server --port 8931
"""

import httpx
import json
import asyncio
import re
from typing import Dict, List, Optional, Any
from loguru import logger
from dataclasses import dataclass
from enum import Enum
import aiohttp


class MCPToolName(str, Enum):
    """Available MCP tools"""
    NAVIGATE = "playwright_navigate"
    CLICK = "playwright_click"
    FILL = "playwright_fill"
    SELECT = "playwright_select"
    HOVER = "playwright_hover"
    SCREENSHOT = "playwright_screenshot"
    GET_TEXT = "playwright_get_text"
    CLOSE = "playwright_close"
    EVALUATE = "playwright_evaluate"


@dataclass
class MCPResponse:
    """Response from MCP tool call"""
    success: bool
    content: Any
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class MCPClient:
    """
    MCP Client with persistent SSE connection.
    Uses aiohttp for SSE to keep connection alive.
    """
    
    def __init__(
        self,
        server_url: str = "http://localhost:8931",
        timeout: float = 60.0
    ):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self._request_id = 0
        self._session_id: Optional[str] = None
        self._initialized = False
        self._sse_session: Optional[aiohttp.ClientSession] = None
        self._sse_response: Optional[aiohttp.ClientResponse] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._responses: Dict[int, asyncio.Future] = {}
        self._connected = False
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client

    async def _sse_listener(self):
        """Background task to listen to SSE events"""
        try:
            async for line in self._sse_response.content:
                line = line.decode('utf-8').strip()
                
                if line.startswith('data:'):
                    data = line[5:].strip()
                    
                    # Check for session endpoint
                    if 'sessionId=' in data:
                        match = re.search(r'sessionId=([a-f0-9-]+)', data)
                        if match:
                            self._session_id = match.group(1)
                            logger.info(f"✅ SSE Session ID: {self._session_id}")
                            self._connected = True
                    else:
                        # Try to parse as JSON response
                        try:
                            response = json.loads(data)
                            req_id = response.get('id')
                            if req_id and req_id in self._responses:
                                self._responses[req_id].set_result(response)
                        except json.JSONDecodeError:
                            pass
                            
        except asyncio.CancelledError:
            logger.info("SSE listener cancelled")
        except Exception as e:
            logger.error(f"SSE listener error: {e}")
            self._connected = False
    
    async def connect(self) -> bool:
        """Establish persistent SSE connection"""
        if self._connected and self._session_id:
            return True
        
        try:
            logger.info("🔌 Opening persistent SSE connection...")
            
            # Create aiohttp session for SSE
            self._sse_session = aiohttp.ClientSession()
            self._sse_response = await self._sse_session.get(
                f"{self.server_url}/sse",
                headers={"Accept": "text/event-stream"}
            )
            
            # Start background listener
            self._sse_task = asyncio.create_task(self._sse_listener())
            
            # Wait for session ID
            for _ in range(50):  # 5 second timeout
                if self._session_id:
                    break
                await asyncio.sleep(0.1)
            
            if not self._session_id:
                logger.error("❌ Timeout waiting for session ID")
                return False
            
            # Initialize protocol
            await asyncio.sleep(0.2)  # Give SSE a moment
            return await self._initialize_protocol()
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def _initialize_protocol(self) -> bool:
        """Send MCP initialize handshake"""
        try:
            result = await self._send_message("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "job-agent", "version": "1.0.0"}
            })
            
            if result:
                self._initialized = True
                logger.info("✅ MCP protocol initialized")
                return True
            return False
            
        except Exception as e:
            # Some servers don't need initialize - try without it
            logger.warning(f"⚠️ Initialize not required or failed: {e}")
            self._initialized = True  # Proceed anyway
            return True
    
    async def _send_message(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send JSON-RPC message while SSE is connected"""
        if not self._session_id:
            raise Exception("No session - call connect() first")
        
        request_id = self._next_request_id()
        
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            payload["params"] = params
        
        url = f"{self.server_url}/messages?sessionId={self._session_id}"
        logger.debug(f"📤 [{request_id}] {method}")
        
        try:
            # Create a future to receive the response via SSE
            response_future = asyncio.Future()
            self._responses[request_id] = response_future
            
            # Send the request
            client = await self._get_http_client()
            http_response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for immediate error
            if http_response.status_code >= 400:
                try:
                    error_data = http_response.json()
                    logger.error(f"❌ HTTP {http_response.status_code}: {error_data}")
                except:
                    logger.error(f"❌ HTTP {http_response.status_code}: {http_response.text}")
                del self._responses[request_id]
                raise Exception(f"HTTP {http_response.status_code}")
            
            # For 202 Accepted, wait for response via SSE
            if http_response.status_code == 202:
                try:
                    result = await asyncio.wait_for(response_future, timeout=30.0)
                    del self._responses[request_id]
                    
                    if "error" in result and result["error"]:
                        raise Exception(f"MCP Error: {result['error']}")
                    
                    return result.get("result", result)
                except asyncio.TimeoutError:
                    del self._responses[request_id]
                    logger.warning(f"⏱️ Timeout waiting for response {request_id}")
                    return {"status": "timeout"}
            
            # For 200 OK, parse response directly
            result = http_response.json()
            del self._responses[request_id]
            
            if "error" in result and result["error"]:
                raise Exception(f"MCP Error: {result['error']}")
            
            logger.debug(f"📥 [{request_id}] OK")
            return result.get("result", result)
            
        except Exception as e:
            if request_id in self._responses:
                del self._responses[request_id]
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> MCPResponse:
        """Call an MCP tool"""
        try:
            if not self._connected or not self._initialized:
                connected = await self.connect()
                if not connected:
                    return MCPResponse(success=False, content=None, error="Failed to connect")
            
            result = await self._send_message("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            # Parse response content
            content = ""
            if result:
                if isinstance(result, dict):
                    content_list = result.get("content", [])
                    if isinstance(content_list, list):
                        for item in content_list:
                            if isinstance(item, dict) and item.get("type") == "text":
                                content += item.get("text", "")
                    else:
                        content = str(content_list)
                else:
                    content = str(result)
            
            return MCPResponse(success=True, content=content or "OK", raw_response=result)
            
        except Exception as e:
            logger.error(f"❌ Tool [{tool_name}] failed: {e}")
            return MCPResponse(success=False, content=None, error=str(e))
    
    # ==========================================================================
    # Browser Operations
    # ==========================================================================
    
    async def navigate(self, url: str) -> MCPResponse:
        logger.info(f"🔗 Navigating: {url}")
        return await self.call_tool("playwright_navigate", {"url": url})
    
    async def click(self, element: str, ref: str, **kwargs) -> MCPResponse:
        logger.info(f"🖱️ Click: {element}")
        return await self.call_tool("playwright_click", {"selector": ref})
    
    async def type_text(self, element: str, ref: str, text: str, **kwargs) -> MCPResponse:
        logger.info(f"⌨️ Type: {element}")
        return await self.call_tool("playwright_fill", {"selector": ref, "value": text})
    
    async def get_snapshot(self) -> MCPResponse:
        logger.info("📸 Getting page content")
        return await self.call_tool("playwright_get_text", {"selector": "body"})
    
    async def take_screenshot(self, filename: Optional[str] = None, **kwargs) -> MCPResponse:
        logger.info("📷 Screenshot")
        params = {"path": filename} if filename else {}
        return await self.call_tool("playwright_screenshot", params)
    
    async def select_option(self, element: str, ref: str, values: List[str]) -> MCPResponse:
        return await self.call_tool("playwright_select", {"selector": ref, "value": values[0] if values else ""})
    
    async def hover(self, element: str, ref: str) -> MCPResponse:
        return await self.call_tool("playwright_hover", {"selector": ref})
    
    async def evaluate(self, script: str) -> MCPResponse:
        return await self.call_tool("playwright_evaluate", {"script": script})
    
    async def close_browser(self) -> MCPResponse:
        logger.info("🔒 Close browser")
        return await self.call_tool("playwright_close", {})
    
    async def wait_for(self, time: Optional[float] = None, **kwargs) -> MCPResponse:
        if time:
            await asyncio.sleep(time)
        return MCPResponse(success=True, content="OK")
    
    async def press_key(self, key: str) -> MCPResponse:
        return await self.evaluate(f"document.activeElement?.dispatchEvent(new KeyboardEvent('keydown', {{key: '{key}', bubbles: true}}))")
    
    async def fill_form(self, fields: List[Dict]) -> MCPResponse:
        ok = 0
        for f in fields:
            r = await self.call_tool("playwright_fill", {"selector": f.get("selector") or f.get("ref"), "value": f.get("value", "")})
            if r.success:
                ok += 1
        return MCPResponse(success=ok == len(fields), content=f"Filled {ok}/{len(fields)}")
    
    # ==========================================================================
    # Connection Management
    # ==========================================================================
    
    async def health_check(self) -> bool:
        try:
            client = await self._get_http_client()
            r = await client.get(f"{self.server_url}/health")
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "ok":
                logger.info(f"✅ MCP healthy (v{data.get('version')})")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
    
    async def list_tools(self) -> List[Dict]:
        try:
            if not self._initialized:
                await self.connect()
            result = await self._send_message("tools/list")
            return result.get("tools", []) if result else []
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    async def close(self):
        """Cleanup connections"""
        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
        
        if self._sse_response:
            self._sse_response.close()
        
        if self._sse_session:
            await self._sse_session.close()
        
        if self._http_client:
            await self._http_client.aclose()
        
        self._session_id = None
        self._initialized = False
        self._connected = False
        logger.info("MCP Client closed")


# Singleton
_mcp_client: Optional[MCPClient] = None


def get_mcp_client(server_url: str = "http://localhost:8931") -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient(server_url=server_url)
    return _mcp_client


async def shutdown_mcp_client():
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None