"""
MCP (Model Context Protocol) Integration Module

This module provides integration with Playwright MCP server for browser automation.
Supports any job application website with multiple LLM providers.
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
    FormFieldType,
    SiteHandler,
    LinkedInHandler,
    IndeedHandler,
    GenericHandler,
    LLMProvider,
    ClaudeProvider,
    OllamaProvider,
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
    "FormFieldType",
    "get_universal_form_service",
    
    # Site Handlers
    "SiteHandler",
    "LinkedInHandler",
    "IndeedHandler",
    "GenericHandler",
    
    # LLM Providers
    "LLMProvider",
    "ClaudeProvider",
    "OllamaProvider",
]
