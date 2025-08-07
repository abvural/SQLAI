from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os
from pathlib import Path

class Settings(BaseSettings):
    # Application Settings
    app_name: str = Field(default="SQLAI", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Settings
    api_host: str = Field(default="localhost", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    
    # Database Cache (SQLite)
    cache_database_url: str = Field(
        default="sqlite:///./cache.db", 
        env="CACHE_DATABASE_URL"
    )
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-here-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # AI Model Settings
    sentence_transformer_model: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2",
        env="SENTENCE_TRANSFORMER_MODEL"
    )
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    max_query_complexity: int = Field(default=10, env="MAX_QUERY_COMPLEXITY")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # Connection Pool Settings
    pool_size: int = Field(default=5, env="POOL_SIZE")
    max_overflow: int = Field(default=10, env="MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="POOL_TIMEOUT")
    
    # Performance Settings
    chunk_size: int = Field(default=10000, env="CHUNK_SIZE")
    max_result_size: int = Field(default=100000, env="MAX_RESULT_SIZE")
    
    # LLM Configuration
    use_local_llm: bool = Field(default=False, env="USE_LOCAL_LLM")
    ollama_host: str = Field(default="http://localhost:11434", env="OLLAMA_HOST")
    mistral_model: str = Field(default="mistral:7b-instruct-q4_K_M", env="MISTRAL_MODEL")
    sqlcoder_model: str = Field(default="sqlcoder", env="SQLCODER_MODEL")
    llm_timeout: int = Field(default=30, env="LLM_TIMEOUT")
    max_context_size: int = Field(default=8192, env="MAX_CONTEXT_SIZE")
    llm_temperature: float = Field(default=0.1, env="LLM_TEMPERATURE")
    llm_top_p: float = Field(default=0.95, env="LLM_TOP_P")
    
    # ChromaDB Configuration
    chroma_persist_path: str = Field(default="./chroma_db", env="CHROMA_PERSIST_PATH")
    chroma_collection_prefix: str = Field(default="sqlai_", env="CHROMA_COLLECTION_PREFIX")
    
    # Master Key (for compatibility)
    sqlai_master_key: str = Field(default="sqlai-fixed-master-key-2024-v1", env="SQLAI_MASTER_KEY")
    
    # CORS Settings
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env

settings = Settings()