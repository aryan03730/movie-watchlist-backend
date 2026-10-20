import os, requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"

def _auth_params():
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY not set")
    return {"api_key": TMDB_API_KEY}

def search_movies(query, year=None, page=1):
    params = _auth_params() | {"query": query, "page": page, "include_adult": "false"}
    if year:
        params["year"] = year
    r = requests.get(f"{TMDB_BASE}/search/movie", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("results", []):
        results.append({
            "tmdb_id": m.get("id"),
            "title": m.get("title"),
            "year": (m.get("release_date") or "0000")[:4],
            "overview": m.get("overview"),
            "poster_path": f"{IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
        })
    return {"page": data.get("page", 1), "total_pages": data.get("total_pages", 1), "results": results}

def get_movie_details(tmdb_id:int):
    params = _auth_params()
    r = requests.get(f"{TMDB_BASE}/movie/{tmdb_id}", params=params, timeout=10)
    r.raise_for_status()
    m = r.json()
    return {
        "tmdb_id": m.get("id"),
        "title": m.get("title"),
        "year": (m.get("release_date") or "0000")[:4],
        "overview": m.get("overview"),
        "poster_path": f"{IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
        "imdb_id": m.get("imdb_id"),
    }


def get_recommendations(tmdb_id: int):
    params = _auth_params()
    r = requests.get(f"{TMDB_BASE}/movie/{tmdb_id}/recommendations", params=params, timeout=10)
    r.raise_for_status()
    results = []
    for m in r.json().get("results", []):
        results.append({
            "tmdb_id": m.get("id"),
            "title": m.get("title"),
            "year": (m.get("release_date") or "0000")[:4],
            "overview": m.get("overview"),
            "poster_path": f"{IMG_BASE}{m['poster_path']}" if m.get("poster_path") else None,
        })
    return results
