from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "platform-self-service")
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite+pysqlite:///./platform_self_service.db"
    )
    api_key: str | None = os.getenv("API_KEY")
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
    artifacts_dir: str = os.getenv("ARTIFACTS_DIR", "./artifacts")


settings = Settings()
