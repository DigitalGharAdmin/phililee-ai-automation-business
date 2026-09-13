"""Local configuration; explicit process variables override project .env values."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lead_generation.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

APP_TITLE = "Phililee AI Labs — Lead Generation Agent"
APP_VERSION = "1.0.0"
