import datetime
from functools import wraps

import jwt
from flask import Blueprint, request, jsonify, g

from config import SECRET_KEY
from db import db
from models import User

auth_bp = Blueprint("auth", __name__)

TOKEN_HOURS = 24


def create_token(user_id):
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY not set")
    payload = {
        "sub": str(user_id),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing token"}), 401
        token = header[len("Bearer "):]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid token"}), 401
        g.user_id = int(payload["sub"])
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.post("/auth/signup")
def signup():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if "@" not in email:
        return jsonify({"error": "valid email is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"token": create_token(user.id), "user": user.to_dict()}), 201


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid email or password"}), 401
    return jsonify({"token": create_token(user.id), "user": user.to_dict()})
