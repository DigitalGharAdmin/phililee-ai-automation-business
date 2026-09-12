"""Local configuration, read from the process environment at startup."""

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lead_generation.db")

APP_TITLE = "Phililee AI Labs — Lead Generation Agent"
APP_VERSION = "1.0.0"
