"""Environment-backed application configuration."""

import os

from dotenv import load_dotenv


load_dotenv()


def get_database_url() -> str:
    """Return the configured PostgreSQL URL or explain how to configure it."""

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Copy backend/.env.example to "
            "backend/.env and set a local PostgreSQL connection URL."
        )
    return database_url
