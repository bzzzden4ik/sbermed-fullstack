import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./clinic_db.sqlite3"
    SECRET_KEY: str = "supersecretkeyclinicmanagement12345!@#$%"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "uploads"
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_TIMEOUT_SECONDS: int = 15
    CLINIC_NAME: str = "Название клиники"
    CLINIC_CITY: str = "Казань"
    CLINIC_ADDRESS: str = ""
    CLINIC_CONTACT_PHONE: str = "+7 (915) 163-07-01"
    OPENAI_API_KEY: str = ""
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
