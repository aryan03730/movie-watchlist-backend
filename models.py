from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from db import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    movies = db.relationship("Movie", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {"id": self.id, "email": self.email}


class Movie(db.Model):
    __tablename__ = "movies"
    __table_args__ = (
        db.UniqueConstraint("user_id", "tmdb_id", name="uq_user_tmdb"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    watched = db.Column(db.Boolean, default=False, nullable=False)
    rating = db.Column(db.Integer)  # 1..10
    notes = db.Column(db.Text)
    tmdb_id = db.Column(db.Integer)
    poster_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "watched": self.watched,
            "rating": self.rating,
            "notes": self.notes,
            "tmdb_id": self.tmdb_id,
            "poster_path": self.poster_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
