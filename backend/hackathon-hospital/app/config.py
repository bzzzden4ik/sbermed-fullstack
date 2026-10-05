import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./clinic_db.sqlite3"
    SECRET_KEY: str = "supersecretkeyclinicmanagement12345!@#$%"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "uploads"
    PRIVATE_UPLOAD_DIR: str = "private_uploads"  # not served publicly; files are returned by authorized endpoints
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_TIMEOUT_SECONDS: int = 15
    CLINIC_NAME: str = "SIRIUS"
    CLINIC_CITY: str = "Москва"
    CLINIC_ADDRESS: str = "119048, ул. Доватора, 15"
    CLINIC_CONTACT_PHONE: str = "+7 915 163-07-01"
    FRONTEND_URL: str = "http://127.0.0.1:5173"  # used for links in emails
    # Comma-separated origins allowed to call the API from a browser (CORS)
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Version of the user agreement / privacy policy / data-processing consent. Changing it asks patients to accept again.
    LEGAL_DOCS_VERSION: str = "2026-10-05"
    # RAG knowledge base: OpenAI embedding model (1536 dimensions) and folder with the Markdown sources
    KNOWLEDGE_EMBEDDING_MODEL: str = "text-embedding-3-small"
    KNOWLEDGE_DIR: str = "knowledge"
    OPENAI_API_KEY: str = ""
    # Retries with exponential backoff on OpenAI rate limits (429), timeouts and 5xx errors
    OPENAI_MAX_RETRIES: int = 5
    OPENAI_TIMEOUT_SECONDS: float = 60
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
