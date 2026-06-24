import os
from dotenv import load_dotenv

load_dotenv(os.environ.get("ENV_FILE", ".env.production"))

SECRET_ENCRYPTION_KEY = os.environ.get("SECRET_ENCRYPTION_KEY", "")

# File uploads
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

ADMIN_WA = os.getenv("ADMIN_WA", "6281234567890")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://kantorteman.my.id")
_DEFAULT_CORS = "https://kantorteman.my.id,https://www.kantorteman.my.id,https://office.kantorteman.my.id,https://office-kantor-teman.vercel.app,http://localhost:3000,http://localhost:3001,http://localhost:3002"
CORS_ORIGIN = os.getenv("CORS_ORIGIN", _DEFAULT_CORS)
CORS_LIST = [o.strip() for o in CORS_ORIGIN.split(",") if o.strip()]

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
PLACES_NEW_SEARCH_URL = os.environ.get("PLACES_NEW_SEARCH_URL", "https://places.googleapis.com/v1/places:searchText")
FONNTE_WEBHOOK_SECRET = os.environ.get("FONNTE_WEBHOOK_SECRET", "")

# Hermes Gateway
HERMES_GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL", "")
HERMES_GATEWAY_TOKEN = os.getenv("HERMES_GATEWAY_TOKEN", "")

# Google Calendar
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or len(JWT_SECRET) < 16:
    raise RuntimeError("JWT_SECRET env var is required (min 16 chars). Set JWT_SECRET in .env.production.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

LOGIN_RATE_MAX = 5
LOGIN_RATE_WINDOW = 300
LOGIN_LOCKOUT_SECONDS = 900

USD_TO_IDR = 17000

SENSITIVE_SETTING_KEYS = {
    "fonnte_token", "ai_api_key", "google_api_key", "google_service_account_json",
    "cms_api_token", "external_lead_api_key", "smtp_password",
}

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
if "mysql" in DATABASE_URL and "pymysql" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")

# Production detection: explicit flag or MySQL = production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "").lower() == "production" or "mysql" in DATABASE_URL

# P1-6: warn if localhost origins in production CORS list
if IS_PRODUCTION:
    for origin in CORS_LIST:
        if "localhost" in origin.lower():
            import sys as _sys
            print(f"[CORS SECURITY WARNING] localhost origin '{origin}' detected in production CORS list!", flush=True)
            break

AUTH_ALLOWED_EMAIL_DOMAINS = [
    domain.strip().lower()
    for domain in os.getenv("AUTH_ALLOWED_EMAIL_DOMAINS", "temanumkmkita.com").split(",")
    if domain.strip()
]
