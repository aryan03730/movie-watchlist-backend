import pytest

import app as app_module


def test_create_and_list_movie(client, make_user):
    h = make_user()
    res = client.post("/movies", json={"title": "Inception", "year": 2010}, headers=h)
    assert res.status_code == 201
    titles = [m["title"] for m in client.get("/movies", headers=h).get_json()]
    assert titles == ["Inception"]


def test_users_cannot_see_or_change_each_others_movies(client, make_user):
    a = make_user("a@example.com")
    b = make_user("b@example.com")
    movie_id = client.post("/movies", json={"title": "Private"}, headers=a).get_json()["id"]

    assert client.get("/movies", headers=b).get_json() == []
    assert client.get(f"/movies/{movie_id}", headers=b).status_code == 404
    assert client.patch(f"/movies/{movie_id}", json={"watched": True}, headers=b).status_code == 404
    assert client.delete(f"/movies/{movie_id}", headers=b).status_code == 404

    mine = client.get(f"/movies/{movie_id}", headers=a)
    assert mine.status_code == 200
    assert mine.get_json()["watched"] is False


def test_toggle_watched(client, make_user):
    h = make_user()
    movie_id = client.post("/movies", json={"title": "Heat"}, headers=h).get_json()["id"]
    on = client.patch(f"/movies/{movie_id}", json={"watched": True}, headers=h)
    assert on.get_json()["watched"] is True
    off = client.patch(f"/movies/{movie_id}", json={"watched": False}, headers=h)
    assert off.get_json()["watched"] is False


def test_delete_removes_movie(client, make_user):
    h = make_user()
    movie_id = client.post("/movies", json={"title": "Gone"}, headers=h).get_json()["id"]
    assert client.delete(f"/movies/{movie_id}", headers=h).status_code == 200
    assert client.get(f"/movies/{movie_id}", headers=h).status_code == 404


@pytest.mark.parametrize("payload", [
    {"title": ""},
    {"title": "   "},
    {"title": "X", "year": 1500},
    {"title": "X", "year": 3000},
    {"title": "X", "year": "2010"},
])
def test_create_rejects_bad_input(client, make_user, payload):
    res = client.post("/movies", json=payload, headers=make_user())
    assert res.status_code == 400


@pytest.mark.parametrize("rating", [0, 11, "5"])
def test_patch_rejects_bad_rating(client, make_user, rating):
    h = make_user()
    movie_id = client.post("/movies", json={"title": "Rated"}, headers=h).get_json()["id"]
    res = client.patch(f"/movies/{movie_id}", json={"rating": rating}, headers=h)
    assert res.status_code == 400


def test_patch_accepts_valid_rating(client, make_user):
    h = make_user()
    movie_id = client.post("/movies", json={"title": "Rated"}, headers=h).get_json()["id"]
    res = client.patch(f"/movies/{movie_id}", json={"rating": 8}, headers=h)
    assert res.status_code == 200
    assert res.get_json()["rating"] == 8


FAKE_MOVIE = {
    "tmdb_id": 27205,
    "title": "Inception",
    "year": "2010",
    "overview": "Dreams within dreams.",
    "poster_path": "https://example.com/poster.jpg",
}


def test_import_creates_movie_then_does_not_duplicate(client, make_user, monkeypatch):
    monkeypatch.setattr(app_module, "tmdb_details", lambda tmdb_id: FAKE_MOVIE)
    h = make_user()
    first = client.post("/movies/import", json={"tmdb_id": 27205}, headers=h)
    second = client.post("/movies/import", json={"tmdb_id": 27205}, headers=h)
    assert first.status_code == 201
    assert second.status_code == 200
    assert len(client.get("/movies", headers=h).get_json()) == 1


def test_two_users_can_import_the_same_movie(client, make_user, monkeypatch):
    monkeypatch.setattr(app_module, "tmdb_details", lambda tmdb_id: FAKE_MOVIE)
    a = make_user("a@example.com")
    b = make_user("b@example.com")
    assert client.post("/movies/import", json={"tmdb_id": 27205}, headers=a).status_code == 201
    assert client.post("/movies/import", json={"tmdb_id": 27205}, headers=b).status_code == 201


def test_import_with_unknown_release_year_stores_no_year(client, make_user, monkeypatch):
    undated = {**FAKE_MOVIE, "tmdb_id": 99, "title": "Mystery Film", "year": "0000"}
    monkeypatch.setattr(app_module, "tmdb_details", lambda tmdb_id: undated)
    res = client.post("/movies/import", json={"tmdb_id": 99}, headers=make_user())
    assert res.status_code == 201
    assert res.get_json()["year"] is None


def test_import_requires_integer_tmdb_id(client, make_user):
    res = client.post("/movies/import", json={"tmdb_id": "abc"}, headers=make_user())
    assert res.status_code == 400


def test_search_requires_login(client):
    assert client.get("/external/search?q=batman").status_code == 401


def test_search_requires_query(client, make_user):
    assert client.get("/external/search", headers=make_user()).status_code == 400


def test_search_returns_results(client, make_user, monkeypatch):
    fake = {"page": 1, "total_pages": 1, "results": [{"tmdb_id": 1, "title": "Batman"}]}
    monkeypatch.setattr(app_module, "tmdb_search", lambda q, year=None: fake)
    res = client.get("/external/search?q=batman", headers=make_user())
    assert res.status_code == 200
    assert res.get_json()["results"][0]["title"] == "Batman"
