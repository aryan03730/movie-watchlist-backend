import app as app_module


def test_health_returns_ok_without_login(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"ok": True}


def test_health_only_allows_get(client):
    assert client.post("/health").status_code == 405


def test_search_blank_query_is_rejected(client, make_user):
    res = client.get("/external/search?q=%20%20", headers=make_user())
    assert res.status_code == 400


def test_search_passes_query_and_year_to_tmdb(client, make_user, monkeypatch):
    seen = {}

    def fake_search(q, year=None):
        seen["q"], seen["year"] = q, year
        return {"page": 1, "total_pages": 1, "results": []}

    monkeypatch.setattr(app_module, "tmdb_search", fake_search)
    res = client.get("/external/search?q=batman&year=1989", headers=make_user())
    assert res.status_code == 200
    assert seen == {"q": "batman", "year": 1989}


def test_search_without_year_sends_none(client, make_user, monkeypatch):
    seen = {}

    def fake_search(q, year=None):
        seen["year"] = year
        return {"page": 1, "total_pages": 1, "results": []}

    monkeypatch.setattr(app_module, "tmdb_search", fake_search)
    client.get("/external/search?q=batman", headers=make_user())
    assert seen["year"] is None


def test_search_rejects_non_numeric_year(client, make_user):
    res = client.get("/external/search?q=batman&year=abc", headers=make_user())
    assert res.status_code == 400
    assert "year" in res.get_json()["error"]
