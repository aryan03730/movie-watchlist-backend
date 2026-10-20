from flask import Blueprint, jsonify, g
import requests

from auth import login_required
from models import Movie
from tmdb import get_recommendations

recs_bp = Blueprint("recs", __name__)

MAX_SEEDS = 5     # how many of the user's movies we ask TMDB about (bounds latency)
MAX_RESULTS = 10  # how many recommendations we return


def rank_recommendations(per_seed, owned_ids, limit=MAX_RESULTS):
    """per_seed is a list of (seed_title, [tmdb movie dicts]).
    Score = how many of the user's movies recommend a title.
    Titles already in the user's watchlist are excluded."""
    scored = {}
    for seed_title, movies in per_seed:
        for m in movies:
            tid = m.get("tmdb_id")
            if tid is None or tid in owned_ids:
                continue
            entry = scored.setdefault(tid, {"movie": m, "score": 0, "because": []})
            entry["score"] += 1
            entry["because"].append(seed_title)
    # sorted() is stable, so ties keep the order TMDB returned them in
    ranked = sorted(scored.values(), key=lambda e: e["score"], reverse=True)
    return [
        {**e["movie"], "score": e["score"], "because": e["because"][:3]}
        for e in ranked[:limit]
    ]


@recs_bp.get("/recommendations")
@login_required
def recommendations():
    movies = (
        Movie.query
        .filter(Movie.user_id == g.user_id, Movie.tmdb_id.isnot(None))
        .order_by(Movie.created_at.desc())
        .all()
    )
    owned_ids = {m.tmdb_id for m in movies}
    seeds = movies[:MAX_SEEDS]
    if not seeds:
        return jsonify({"results": [], "based_on": 0})

    per_seed = []
    for seed in seeds:
        try:
            per_seed.append((seed.title, get_recommendations(seed.tmdb_id)))
        except (requests.RequestException, RuntimeError):
            continue  # one failed TMDB call should not sink the whole request

    if not per_seed:
        return jsonify({"error": "recommendation service unavailable"}), 502

    return jsonify({
        "results": rank_recommendations(per_seed, owned_ids),
        "based_on": len(per_seed),
    })
