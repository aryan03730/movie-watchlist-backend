from datetime import datetime
from db import db

class Movie(db.Model):
    __tablename__ = "movies"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    watched = db.Column(db.Boolean, default=False, nullable=False)
    rating = db.Column(db.Integer)  # 1..10
    notes = db.Column(db.Text)
    tmdb_id = db.Column(db.Integer, unique=True)
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
