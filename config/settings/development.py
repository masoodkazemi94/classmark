import secrets

from .base import *

load_dotenv(BASE_DIR / ".env", override=True)

DEBUG = get_bool_env("DEBUG", default=True)

if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(50)

if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
