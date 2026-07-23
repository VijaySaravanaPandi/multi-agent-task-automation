"""
Central configuration for the system.
Phase 1: just loads environment variables and exposes typed settings.
Later phases (4, 7, 8) will extend this with risk tiers, cost limits, etc.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Dry-run defaults to True so nothing external ever fires by accident.
    DRY_RUN_MODE: bool = os.getenv("DRY_RUN_MODE", "true").lower() == "true"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
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