from app.settings import SETTINGS


OPENAI_API_KEY = SETTINGS.openai_api_key

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to the .env file."
    )
