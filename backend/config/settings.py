import os
from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Financial Document Analyzer"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: os.urandom(32).hex(),
        description="JWT secret key"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    MONGODB_URL: str = Field(
        # default="mongodb://admin:password123@localhost:27017",
        default="mongodb://mongo:27017/wingify",
        description="MongoDB connection URL"
    )
    DATABASE_NAME: str = Field(
        default="financial_analyzer",
        description="Database name"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # LLM Configuration
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key"
    )
    LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model name"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM temperature"
    )
    
    # Search API
    SERPER_API_KEY: str = Field(
        default="",
        description="Serper.dev API key for web search"
    )
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum file size in bytes"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".docx", ".txt"],
        description="Allowed file extensions"
    )
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Upload directory path"
    )
    
    # Rate Limiting
    RATE_LIMIT_CALLS: int = Field(
        default=100,
        description="Max API calls per period"
    )
    RATE_LIMIT_PERIOD: int = Field(
        default=3600,  # 1 hour
        description="Rate limit period in seconds"
    )
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "https://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173"
        ],
        description="Allowed CORS origins"
    )
    
    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment name"
    )
    
    @property
    def DEBUG(self) -> bool:
        return self.ENVIRONMENT.lower() in ["development", "dev", "debug"]
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        if not v:
            raise ValueError("OPENAI_API_KEY is required")
        return v

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

settings = Settings()