"""Local configuration, read from the process environment at startup."""

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lead_generation.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

APP_TITLE = "Phililee AI Labs — Lead Generation Agent"
APP_VERSION = "1.0.0"
