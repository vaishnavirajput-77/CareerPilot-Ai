import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "careerpilot.db").resolve()

raw_db_url = os.getenv("DATABASE_URL")
if not raw_db_url:
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
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

