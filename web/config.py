import os

BACKEND_URL = os.environ.get("WEB_BACKEND_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = float(os.environ.get("WEB_REQUEST_TIMEOUT", "120"))
