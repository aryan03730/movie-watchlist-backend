import os

# These must be set BEFORE the app is imported: config.py and tmdb.py read them at import time.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # throwaway DB, never your real one
os.environ["SECRET_KEY"] = "test-secret-key-long-enough-for-hs256-signing"
os.environ.pop("TMDB_API_KEY", None)  # tests must never call the real TMDB API

import pytest
import app as app_module


@pytest.fixture
def client():
    flask_app = app_module.create_app()  # fresh app + fresh empty database per test
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def make_user(client):
    """Sign up a user and return the Authorization header for them."""
    def _make(email="a@example.com", password="password123"):
        res = client.post("/auth/signup", json={"email": email, "password": password})
        assert res.status_code == 201
        return {"Authorization": f"Bearer {res.get_json()['token']}"}
    return _make
