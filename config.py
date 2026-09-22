import os
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@localhost:5432/watchlist")
DEBUG = os.getenv("DEBUG", "1") == "1"
