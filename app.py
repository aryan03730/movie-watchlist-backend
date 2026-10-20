from flask import Flask, request, jsonify, g
from flask_cors import CORS
from config import DB_URL, DEBUG
from db import db
from models import Movie
from auth import auth_bp, login_required
from recommendations import recs_bp
from tmdb import search_movies as tmdb_search, get_movie_details as tmdb_details


def get_own_movie(movie_id):
    # Only returns the movie if it belongs to the logged-in user
    return Movie.query.filter_by(id=movie_id, user_id=g.user_id).first()


def valid_year(year):
    return year is None or (isinstance(year, int) and 1888 <= year <= 2100)


def parse_tmdb_year(value):
    # TMDB sends "" or "0000" when a release date is unknown.
    # Only keep a year the app itself considers valid; otherwise store nothing.
    if value and str(value).isdigit():
        year = int(value)
        if valid_year(year):
            return year
    return None


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(recs_bp)

    with app.app_context():
        db.create_all()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/movies")
    @login_required
    def list_movies():
        q = request.args.get("q")
        watched = request.args.get("watched")
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        query = Movie.query.filter_by(user_id=g.user_id)
        if q:
            query = query.filter(Movie.title.ilike(f"%{q}%"))
        if watched in ("true", "false"):
            query = query.filter(Movie.watched == (watched == "true"))
        items = query.order_by(Movie.created_at.desc()).limit(limit).offset(offset).all()
        return jsonify([m.to_dict() for m in items])

    @app.post("/movies")
    @login_required
    def create_movie():
        data = request.get_json(force=True, silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        year = data.get("year")
        if not valid_year(year):
            return jsonify({"error": "year must be an integer between 1888 and 2100"}), 400
        movie = Movie(user_id=g.user_id, title=title, year=year, notes=data.get("notes"))
        db.session.add(movie)
        db.session.commit()
        return jsonify(movie.to_dict()), 201

    @app.get("/movies/<int:movie_id>")
    @login_required
    def get_movie(movie_id):
        m = get_own_movie(movie_id)
        if not m:
            return jsonify({"error": "not found"}), 404
        return jsonify(m.to_dict())

    @app.put("/movies/<int:movie_id>")
    @login_required
    def put_movie(movie_id):
        m = get_own_movie(movie_id)
        if not m:
            return jsonify({"error": "not found"}), 404
        data = request.get_json(force=True, silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        year = data.get("year")
        if not valid_year(year):
            return jsonify({"error": "year must be an integer between 1888 and 2100"}), 400
        m.title = title
        m.year = year
        m.watched = bool(data.get("watched", m.watched))
        m.rating = data.get("rating")
        m.notes = data.get("notes")
        db.session.commit()
        return jsonify(m.to_dict())

    @app.patch("/movies/<int:movie_id>")
    @login_required
    def patch_movie(movie_id):
        m = get_own_movie(movie_id)
        if not m:
            return jsonify({"error": "not found"}), 404
        data = request.get_json(force=True, silent=True) or {}
        if "title" in data:
            t = (data["title"] or "").strip()
            if not t:
                return jsonify({"error": "title cannot be empty"}), 400
            m.title = t
        if "year" in data:
            if not valid_year(data["year"]):
                return jsonify({"error": "invalid year"}), 400
            m.year = data["year"]
        if "watched" in data:
            m.watched = bool(data["watched"])
        if "rating" in data:
            r = data["rating"]
            if r is not None and (not isinstance(r, int) or r < 1 or r > 10):
                return jsonify({"error": "rating must be 1..10"}), 400
            m.rating = r
        if "notes" in data:
            m.notes = data["notes"]
        db.session.commit()
        return jsonify(m.to_dict())

    @app.delete("/movies/<int:movie_id>")
    @login_required
    def delete_movie(movie_id):
        m = get_own_movie(movie_id)
        if not m:
            return jsonify({"error": "not found"}), 404
        db.session.delete(m)
        db.session.commit()
        return jsonify({"deleted": movie_id})

    @app.get("/external/search")
    @login_required
    def external_search():
        q = (request.args.get("q") or "").strip()
        if not q:
            return jsonify({"error": "q (query) is required"}), 400
        year = request.args.get("year")
        try:
            year = int(year) if year else None
        except ValueError:
            return jsonify({"error": "year must be int"}), 400
        data = tmdb_search(q, year=year)
        return jsonify(data)

    @app.post("/movies/import")
    @login_required
    def import_movie():
        body = request.get_json(force=True, silent=True) or {}
        tmdb_id = body.get("tmdb_id")
        if not isinstance(tmdb_id, int):
            return jsonify({"error": "tmdb_id (int) required"}), 400
        existing = Movie.query.filter_by(user_id=g.user_id, tmdb_id=tmdb_id).first()
        if existing:
            return jsonify(existing.to_dict()), 200
        info = tmdb_details(tmdb_id)
        movie = Movie(
            user_id=g.user_id,
            tmdb_id=info["tmdb_id"],
            title=info["title"],
            year=parse_tmdb_year(info.get("year")),
            notes=(info.get("overview") or None),
            poster_path=info.get("poster_path"),
        )
        db.session.add(movie)
        db.session.commit()
        return jsonify(movie.to_dict()), 201

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=DEBUG, host="0.0.0.0")
