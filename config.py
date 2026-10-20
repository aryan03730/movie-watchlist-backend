import os

_db_url = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/watchlist")
# Name the driver explicitly. Newer SQLAlchemy versions default "postgresql://"
# to psycopg (v3), but this project installs psycopg2-binary.
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

DB_URL = _db_url
DEBUG = os.getenv("DEBUG", "1") == "1"
SECRET_KEY = os.getenv("SECRET_KEY")
