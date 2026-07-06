import os
from dotenv import load_dotenv

load_dotenv()


def require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


OPENAI_API_KEY: str = require_env("OPENAI_API_KEY")
DATABASE_URL: str = require_env("DATABASE_URL")
DEFAULT_USER_ID: str = os.getenv("USER_ID", "")

EMBEDDING_MODEL: str = "text-embedding-3-small"
CHAT_MODEL: str = "gpt-4.1-mini"
TOP_K_DEFAULT: int = 5
