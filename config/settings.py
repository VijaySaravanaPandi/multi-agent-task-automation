"""
Central configuration for the system.
Phase 2 adds Groq LLM settings on top of Phase 1's env loading.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DRY_RUN_MODE: bool = os.getenv("DRY_RUN_MODE", "true").lower() == "true"

    GROQ_API_KEY_1: str = os.getenv("GROQ_API_KEY_1", "")
    GROQ_API_KEY_2: str = os.getenv("GROQ_API_KEY_2", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")

    EMAIL_SMTP_HOST: str = os.getenv("EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    EMAIL_ADDRESS: str = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")

    ALLOWED_EMAIL_DOMAINS: list[str] = [
        d.strip() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()
    ]

    LOG_DIR: str = "logs"


settings = Settings()