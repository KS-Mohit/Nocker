"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Supports environment variables and .env files.

MERGED: Original settings + MCP settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # ==========================================================================
    # API Settings 
    # ==========================================================================
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Job Application Agent"
    DEBUG: bool = False
    
    # ==========================================================================
    # Database - PostgreSQL 
    # ==========================================================================
    POSTGRES_SERVER: str = "127.0.0.1"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "job_agent"
    POSTGRES_PORT: int = 5432
    
    @property
    def DATABASE_URL(self) -> str:
        """Async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync PostgreSQL connection URL (for Alembic)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # ==========================================================================
    # Redis 
    # ==========================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==========================================================================
    # Celery 
    # ==========================================================================
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # ==========================================================================
    # JWT / Security 
    # ==========================================================================
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ==========================================================================
    # Qdrant - Vector Database 
    # ==========================================================================
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    
    # Embedding model 
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # ==========================================================================
    # Ollama - Local AI 
    # ==========================================================================
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    OLLAMA_TIMEOUT: int = 120  # seconds (NEW)

    # ==========================================================================
    # Google Gemini - Vision AI 
    # ==========================================================================
    GOOGLE_API_KEY: Optional[str] = None
    
    # ==========================================================================
    # Anthropic Claude API 
    # ==========================================================================
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    
    # ==========================================================================
    # Browser - Legacy Playwright 
    # ==========================================================================
    BROWSER_HEADLESS: bool = False
    MAX_CONCURRENT_BROWSERS: int = 5
    
    # ==========================================================================
    # MCP Server - Playwright Browser Automation 
    # ==========================================================================
    MCP_SERVER_URL: str = "http://localhost:8931"
    MCP_TIMEOUT: int = 60  # seconds
    MCP_USER_DATA_DIR: str = "./browser-data"
    
    # ==========================================================================
    # File Storage 
    # ==========================================================================
    UPLOAD_DIR: str = "./uploads"
    SCREENSHOT_DIR: str = "./screenshots"
    OUTPUT_DIR: str = "./outputs"
    
    # ==========================================================================
    # Rate Limiting 
    # ==========================================================================
    MAX_APPLICATIONS_PER_HOUR: int = 10
    MIN_DELAY_BETWEEN_APPLICATIONS: int = 30  # seconds
    
    # ==========================================================================
    # Token Tracking 
    # ==========================================================================
    ENABLE_TOKEN_TRACKING: bool = True
    TOKEN_BUDGET_DAILY: Optional[int] = None  # None = unlimited
    TOKEN_BUDGET_MONTHLY: Optional[int] = None
    
    # ==========================================================================
    # Pydantic Settings Config 
    # ==========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()