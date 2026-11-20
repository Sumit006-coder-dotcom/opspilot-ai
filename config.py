from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    demo_mode: bool = True
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    database_url: str = "sqlite:///./opspilot.db"
    api_token: str = "change-this-demo-token"
    jwt_secret: str = "change-this-insecure-jwt-secret"
    jwt_expire_minutes: int = 30
    admin_bootstrap_key: str = ""
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    upload_dir: str = "./data/uploads"
    vector_dir: str = "./data/vector_store"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 150
    rag_top_k: int = 4
    rag_similarity_threshold: float = 0.18
    workflow_checkpoint_path: str = "./data/workflow_checkpoints.sqlite"
    mcp_timeout_seconds: float = 180.0

    @model_validator(mode="after")
    def require_production_secrets(self):
        if not self.demo_mode:
            if len(self.jwt_secret) < 32 or self.jwt_secret.startswith("change-this"):
                raise ValueError("Set JWT_SECRET to a random value of at least 32 characters when DEMO_MODE=false")
            if len(self.api_token) < 32 or self.api_token.startswith("change-this"):
                raise ValueError("Set API_TOKEN to a random value of at least 32 characters when DEMO_MODE=false")
        return self

settings = Settings()
