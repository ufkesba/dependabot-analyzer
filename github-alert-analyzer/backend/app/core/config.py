"""Application configuration using Pydantic settings."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "GitHub Alert Analyzer"
    environment: str = "development"
    debug: bool = True
    
    # Database (Supabase)
    database_url: str = "postgresql://postgres:password@db.project.supabase.co:5432/postgres"
    database_echo: bool = False
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/auth/callback/github"
    
    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
