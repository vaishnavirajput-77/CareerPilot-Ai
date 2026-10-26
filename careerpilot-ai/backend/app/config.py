import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "careerpilot.db").resolve()

raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url:
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
else:
    # Normalize postgres:// or postgresql:// to postgresql+psycopg:// for SQLAlchemy 2.0 + psycopg v3
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_db_url.startswith("postgresql://") and "+psycopg" not in raw_db_url:
        DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        DATABASE_URL = raw_db_url

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-careerpilot-insecure-secret-key-change-in-production-32chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1", "yes")

