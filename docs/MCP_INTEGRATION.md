# Playwright MCP Integration Guide

## Overview

This document explains how to set up and use the Playwright MCP (Model Context Protocol) integration for automating LinkedIn job applications.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Backend                                │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐    │
│  │ RAG Service  │  │ Ollama AI    │  │ MCP Client Service         │    │
│  │ (Qdrant)     │  │ (Local LLM)  │  │ (HTTP Client)              │    │
│  └──────────────┘  └──────────────┘  └─────────────┬──────────────┘    │
│                                                     │                   │
│  ┌─────────────────────────────────────────────────┼─────────────────┐ │
│  │              LinkedIn Application Service        │                 │ │
│  │  Orchestrates: RAG → AI → MCP for form filling  │                 │ │
│  └─────────────────────────────────────────────────┼─────────────────┘ │
└─────────────────────────────────────────────────────┼───────────────────┘
                                                      │ HTTP (port 8931)
┌─────────────────────────────────────────────────────▼───────────────────┐
│                     Playwright MCP Server (Separate Process)            │
│  • Runs as independent Node.js process                                  │
│  • Manages Chromium browser instance                                    │
│  • Provides standardized MCP tools for browser automation               │
│  • Persists login session in user-data-dir                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why Playwright MCP?

| Feature | Old Approach (Vision) | New Approach (MCP) |
|---------|----------------------|-------------------|
| **Page Understanding** | Screenshot → Gemini Vision API | Accessibility Tree (structured text) |
| **Speed** | Slow (image upload + processing) | Fast (text-based) |
| **Cost** | Expensive (Vision API calls) | Free (local processing) |
| **Reliability** | Depends on visual recognition | Deterministic element refs |
| **LLM Requirements** | Vision-capable model needed | Any text LLM works |
| **Debugging** | Hard (image-based) | Easy (structured snapshots) |

## Quick Start

### 1. Install Prerequisites

```bash
# Node.js 18+ required
node --version  # Should be v18.x or higher

# Install Playwright MCP globally (optional)
npm install -g @playwright/mcp
```

### 2. Start the MCP Server

**Option A: Using the startup script (Recommended)**
```bash
# Linux/Mac
chmod +x scripts/start_mcp_server.sh
./scripts/start_mcp_server.sh

# Windows
scripts\start_mcp_server.bat
```

**Option B: Direct command**
```bash
npx @playwright/mcp@latest --port 8931 --user-data-dir ./browser-data
```

**Option C: Docker**
```bash
docker run -d -p 8931:8931 \
  mcr.microsoft.com/playwright/mcp \
  --headless --browser chromium --no-sandbox --port 8931
```

### 3. First-Time LinkedIn Login

Since the MCP server maintains a persistent browser profile, you need to log in to LinkedIn once:

1. Start MCP server (non-headless mode)
2. Call the navigate endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/mcp/navigate \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.linkedin.com/login"}'
   ```
3. Log in manually in the browser window
4. Your session is now saved in `./browser-data`

### 4. Verify Setup

```bash
# Check MCP server health
curl http://localhost:8000/api/v1/mcp/health

# Expected response:
{
  "healthy": true,
  "server_url": "http://localhost:8931",
  "tools_available": 25,
  "message": "MCP server is running with 25 tools available"
}
```

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/health` | GET | Check MCP server status |
| `/api/v1/mcp/tools` | GET | List available MCP tools |
| `/api/v1/mcp/setup-guide` | GET | Get setup instructions |

### Job Application

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/apply` | POST | Apply to a job |

**Apply to Job Request:**
```json
{
  "job_url": "https://www.linkedin.com/jobs/view/123456789/",
  "kb_id": 1,
  "dry_run": true
}
```

**Parameters:**
- `job_url`: LinkedIn job URL
- `kb_id`: Knowledge base ID (user profile)
- `dry_run`: If true, won't actually submit (default: true)

### Low-Level Browser Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcp/navigate` | POST | Navigate to URL |
| `/api/v1/mcp/snapshot` | GET | Get page accessibility snapshot |
| `/api/v1/mcp/click` | POST | Click element |
| `/api/v1/mcp/type` | POST | Type text |
| `/api/v1/mcp/screenshot` | POST | Take screenshot |
| `/api/v1/mcp/close` | POST | Close browser |

## How It Works

### 1. Page Snapshot

Instead of taking screenshots, MCP provides an **accessibility snapshot** - a structured text representation of the page:

```
- navigation "LinkedIn"
  - link "Home" [ref=s1e5]
  - link "Jobs" [ref=s1e10]
- main
  - heading "Software Engineer at Google" [ref=s1e20]
  - button "Easy Apply" [ref=s1e25]
  - form
    - textbox "First name" [ref=s1e30]: ""
    - textbox "Email" [ref=s1e35]: "john@example.com"
    - combobox "Country" [ref=s1e40]
    - button "Next" [ref=s1e45]
```

### 2. Element References

Each element has a unique `ref` that can be used for interactions:
- `ref=s1e25` → Click Easy Apply button
- `ref=s1e30` → Type into First name field

### 3. Form Filling Flow

```
1. Navigate to job URL
2. Get snapshot → Find "Easy Apply" button → Click
3. Loop for each form page:
   a. Get snapshot → Parse form fields
   b. For each field:
      - Try direct mapping (name, email, phone)
      - OR use RAG + AI to generate answer
   c. Fill field using MCP type/select
   d. Find Next/Submit button → Click
4. Detect "Application sent" → Success!
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# MCP Server
MCP_SERVER_URL=http://localhost:8931
MCP_TIMEOUT=60
MCP_USER_DATA_DIR=./browser-data
```

### MCP Server Options

```bash
npx @playwright/mcp@latest \
  --port 8931 \
  --user-data-dir ./browser-data \
  --viewport-size 1920x1080 \
  --headless  # Add for headless mode
```

| Option | Description |
|--------|-------------|
| `--port` | HTTP port for MCP server |
| `--user-data-dir` | Directory to persist browser profile |
| `--viewport-size` | Browser window size |
| `--headless` | Run without visible browser |
| `--browser` | Browser to use (chromium, firefox, webkit) |

## Troubleshooting

### MCP Server Not Responding

```bash
# Check if server is running
curl http://localhost:8931/health

# Check if port is in use
lsof -i :8931  # Linux/Mac
netstat -ano | findstr 8931  # Windows
```

### LinkedIn Login Issues

1. Delete browser data and re-login:
   ```bash
   rm -rf ./browser-data
   ./scripts/start_mcp_server.sh
   # Then navigate to LinkedIn and login again
   ```

2. Check for CAPTCHA - may need manual intervention

### Form Field Not Found

1. Get the page snapshot:
   ```bash
   curl http://localhost:8000/api/v1/mcp/snapshot
   ```

2. Look for the field in the output
3. Use the correct `ref` value

### Slow Performance

- Use `--headless` mode
- Ensure Ollama is running locally
- Check Qdrant connection

## Migration from Old System

If you're migrating from the old vision-based system:

### Files to Replace

| Old File | New File | Notes |
|----------|----------|-------|
| `services/browser/form_filler.py` | `services/mcp/linkedin_application_service.py` | Complete replacement |
| `services/browser/playwright_service.py` | `services/mcp/mcp_client.py` | Complete replacement |

### Files to Keep

- `services/rag/rag_service.py` - Still used for context retrieval
- `services/ai/ollama_service.py` - Still used for answer generation
- `services/embeddings/` - Still used for RAG
- `services/qdrant/` - Still used for vector storage

### API Changes

| Old Endpoint | New Endpoint |
|--------------|--------------|
| `POST /scraper/auto-apply` | `POST /mcp/apply` |

## Best Practices

1. **Always use dry_run=true first** to verify the application flow
2. **Keep browser-data** directory backed up for session persistence
3. **Monitor token usage** when using AI for custom questions
4. **Add Q&A pairs** to knowledge base for common questions
5. **Test with simple jobs** before complex multi-page applications

## Security Considerations

- The MCP server has access to your browser session
- LinkedIn cookies are stored in `user-data-dir`
- Don't expose MCP port (8931) to the internet
- Use Docker network isolation in production
