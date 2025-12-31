"""
MCP (Model Context Protocol) Integration Module
This module provides integration with Playwright MCP server for browser automation.
"""

from app.services.mcp.mcp_client import (
    MCPClient,
    MCPResponse,
    MCPToolName,
    get_mcp_client,
    shutdown_mcp_client
)

from app.services.mcp.universal_form_service import (
    UniversalFormService,
    JobSite,
    ApplicationResult,
    get_universal_form_service
)

__all__ = [
    # MCP Client
    "MCPClient",
    "MCPResponse",
    "MCPToolName",
    "get_mcp_client",
    "shutdown_mcp_client",
    # Universal Form Service
    "UniversalFormService",
    "ApplicationResult",
    "JobSite",
    "get_universal_form_service",
]