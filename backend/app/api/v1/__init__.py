from fastapi import APIRouter
from app.api.v1.endpoints import jobs, scraper, auth, ai, knowledge_base, rag, applications, token_usage, evaluations, mcp, apply

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(token_usage.router, prefix="/token-usage", tags=["Token Usage"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])

# MCP Browser Automation
api_router.include_router(mcp.router, tags=["MCP Browser"])
api_router.include_router(apply.router, tags=["Job Applications"])
