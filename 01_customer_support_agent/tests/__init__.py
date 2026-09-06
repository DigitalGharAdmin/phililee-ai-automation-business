import hashlib
import os
import secrets


# Isolate application initialization from any developer or deployment credential.
TEST_SERVICE_KEY = secrets.token_urlsafe(48)
os.environ["N8N_SERVICE_KEY_SHA256"] = hashlib.sha256(
    TEST_SERVICE_KEY.encode("utf-8")
).hexdigest()
os.environ["APP_ENV"] = "development"
os.environ["ENABLE_DEBUG_ENDPOINTS"] = "true"
