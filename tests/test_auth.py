import datetime
import os

import jwt

from models import User


def test_signup_returns_token_and_user(client):
    res = client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["token"]
    assert body["user"]["email"] == "new@example.com"
    assert "password" not in body["user"] and "password_hash" not in body["user"]


def test_signup_duplicate_email_rejected(client, make_user):
    make_user("dup@example.com")
    res = client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


def test_signup_email_is_case_insensitive(client, make_user):
    make_user("Mixed@Example.com")
    res = client.post("/auth/login", json={"email": "mixed@example.com", "password": "password123"})
    assert res.status_code == 200


def test_signup_rejects_short_password(client):
    res = client.post("/auth/signup", json={"email": "a@example.com", "password": "short"})
    assert res.status_code == 400


def test_signup_rejects_bad_email(client):
    res = client.post("/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert res.status_code == 400


def test_login_success(client, make_user):
    make_user("a@example.com")
    res = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert res.status_code == 200
    assert res.get_json()["token"]


def test_login_error_does_not_reveal_whether_email_exists(client, make_user):
    make_user("real@example.com")
    wrong_password = client.post("/auth/login", json={"email": "real@example.com", "password": "nope-nope"})
    unknown_email = client.post("/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


def test_password_is_stored_hashed(client, make_user):
    make_user("h@example.com")
    with client.application.app_context():
        user = User.query.filter_by(email="h@example.com").first()
        assert user.password_hash != "password123"
        assert user.check_password("password123")
        assert not user.check_password("wrong-password")


def test_missing_token_rejected(client):
    res = client.get("/movies")
    assert res.status_code == 401
    assert res.get_json()["error"] == "missing token"


def test_garbage_token_rejected(client):
    res = client.get("/movies", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_expired_token_rejected(client):
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)},
        os.environ["SECRET_KEY"],
        algorithm="HS256",
    )
    res = client.get("/movies", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert res.get_json()["error"] == "token expired"


def test_token_signed_with_wrong_key_rejected(client):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)},
        "attacker-key-long-enough-for-hs256-signing",
        algorithm="HS256",
    )
    res = client.get("/movies", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401
