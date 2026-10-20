import pytest
import requests

import app as app_module
import recommendations as recs_module


def tm(tmdb_id, title):
    """A movie dict shaped like what tmdb.get_recommendations returns."""
    return {"tmdb_id": tmdb_id, "title": title, "year": "2010", "overview": "", "poster_path": None}


def add_movie(client, headers, monkeypatch, tmdb_id, title):
    # Import a movie into the user's watchlist without calling the real TMDB.
    monkeypatch.setattr(app_module, "tmdb_details", lambda tid: tm(tid, title))
    res = client.post("/movies/import", json={"tmdb_id": tmdb_id}, headers=headers)
    assert res.status_code == 201


def test_recommendations_require_login(client):
    assert client.get("/recommendations").status_code == 401


def test_empty_watchlist_gives_empty_recommendations(client, make_user):
    h = make_user()
    body = client.get("/recommendations", headers=h).get_json()
    assert body == {"results": [], "based_on": 0}


def test_ranks_by_overlap_and_excludes_owned(client, make_user, monkeypatch):
    h = make_user()
    add_movie(client, h, monkeypatch, 1, "Inception")
    add_movie(client, h, monkeypatch, 2, "Interstellar")

    fake = {
        1: [tm(3, "Tenet"), tm(2, "Interstellar"), tm(4, "Memento")],
        2: [tm(3, "Tenet"), tm(5, "Gravity")],
    }
    monkeypatch.setattr(recs_module, "get_recommendations", lambda tid: fake[tid])

    body = client.get("/recommendations", headers=h).get_json()
    ids = [r["tmdb_id"] for r in body["results"]]

    assert body["based_on"] == 2
    assert ids[0] == 3                      # recommended by both movies, so it ranks first
    assert set(ids) == {3, 4, 5}            # movies already in the watchlist are excluded
    assert body["results"][0]["score"] == 2
    assert set(body["results"][0]["because"]) == {"Inception", "Interstellar"}


def test_recommendations_are_per_user(client, make_user, monkeypatch):
    a = make_user("a@example.com")
    b = make_user("b@example.com")
    add_movie(client, a, monkeypatch, 1, "Inception")
    monkeypatch.setattr(recs_module, "get_recommendations", lambda tid: [tm(9, "Other")])

    assert client.get("/recommendations", headers=a).get_json()["based_on"] == 1
    assert client.get("/recommendations", headers=b).get_json() == {"results": [], "based_on": 0}


def test_one_failing_tmdb_call_is_skipped(client, make_user, monkeypatch):
    h = make_user()
    add_movie(client, h, monkeypatch, 1, "Inception")
    add_movie(client, h, monkeypatch, 2, "Interstellar")

    def flaky(tid):
        if tid == 1:
            raise requests.ConnectionError("down")
        return [tm(5, "Gravity")]

    monkeypatch.setattr(recs_module, "get_recommendations", flaky)
    res = client.get("/recommendations", headers=h)
    assert res.status_code == 200
    assert res.get_json()["based_on"] == 1
    assert [r["tmdb_id"] for r in res.get_json()["results"]] == [5]


def test_all_tmdb_calls_failing_returns_502(client, make_user, monkeypatch):
    h = make_user()
    add_movie(client, h, monkeypatch, 1, "Inception")

    def boom(tid):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(recs_module, "get_recommendations", boom)
    assert client.get("/recommendations", headers=h).status_code == 502


def test_rank_respects_limit_and_ties_keep_tmdb_order():
    per_seed = [("X", [tm(1, "A"), tm(2, "B"), tm(3, "C")])]
    out = recs_module.rank_recommendations(per_seed, owned_ids=set(), limit=2)
    assert [r["tmdb_id"] for r in out] == [1, 2]
