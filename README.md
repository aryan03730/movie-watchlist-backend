# Movie Watchlist: Backend

A REST API for a personal movie watchlist. Users sign up, search TMDB for movies, save them to their own watchlist, mark them as watched, and get recommendations based on what they have saved.

- Frontend repo: https://github.com/aryan03730/movie-watchlist-frontend
- Live app: https://movie-watchlist-frontend-six.vercel.app (hosted on free tiers, so the first request can take up to ~50 seconds while the backend wakes up)

## Features

- Sign up and log in with email and password (passwords are hashed, login tokens are JWTs that expire after 24 hours)
- Every user only sees and changes their own movies
- Search TMDB and import a movie into your watchlist
- Create, read, update, and delete movies (title, year, watched, rating 1-10, notes)
- Recommendations: asks TMDB for movies similar to your 5 most recent additions and ranks them by how many of your movies recommend each one
- Automated tests, run by GitHub Actions on every push and pull request

## Tech stack

Python 3.11, Flask, Flask-SQLAlchemy, PostgreSQL, PyJWT, Docker and Docker Compose, pytest, GitHub Actions. Deployed on Render.

## Run it locally (Docker)

You need Docker (Docker Desktop on Mac or Windows) and a free TMDB API key from https://www.themoviedb.org/settings/api.

1. Clone the repo and go into it:

```
git clone https://github.com/aryan03730/movie-watchlist-backend.git
cd movie-watchlist-backend
```

2. Create your `.env` file from the template:

```
cp .env.example .env
```

3. Open `.env` and set `SECRET_KEY` and `TMDB_API_KEY`. To generate a secret key:

```
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

4. Start the app and a Postgres database:

```
docker compose up --build
```

5. In another terminal, check that it is running:

```
curl http://localhost:5050/health
```

You should see `{"ok":true}`. The API is now at http://localhost:5050.

To stop it, press Ctrl+C, then run `docker compose down`. To also delete the stored database data, run `docker compose down -v`.

## Run the tests

The tests need no Docker, database, or API keys. They use an in-memory SQLite database and fake TMDB responses.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

## Configuration

Set these in `.env` (see `.env.example`):

| Variable | Required | What it does |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Signs login tokens. Use a long random string. |
| `TMDB_API_KEY` | Yes | Lets the app search TMDB and fetch movie details. |
| `DATABASE_URL` | No | PostgreSQL connection string. Docker Compose sets this for you. |
| `DEBUG` | No | `1` turns on Flask debug mode (default `1`). |

## API

All endpoints return JSON. Errors look like `{"error": "message"}`. Endpoints marked "Yes" under Auth need the header `Authorization: Bearer <token>`, where the token comes from signup or login.

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | No | Health check. Returns `{"ok": true}`. |
| POST | `/auth/signup` | No | Body: `email`, `password` (at least 8 characters). Returns `201` with `token` and `user`. `409` if the email is taken. |
| POST | `/auth/login` | No | Body: `email`, `password`. Returns `token` and `user`, or `401` for a wrong email or password. |
| GET | `/movies` | Yes | Your watchlist. Optional query params: `q` (title contains), `watched` (`true` or `false`), `limit` (default 50), `offset`. |
| POST | `/movies` | Yes | Body: `title`, optional `year` (1888-2100), `notes`. Returns `201`. |
| GET | `/movies/<id>` | Yes | One of your movies. `404` if it does not exist or is not yours. |
| PUT | `/movies/<id>` | Yes | Replaces a movie. `title` is required. A missing `rating` or `notes` is cleared. |
| PATCH | `/movies/<id>` | Yes | Updates only the fields you send: `title`, `year`, `watched`, `rating` (1-10), `notes`. |
| DELETE | `/movies/<id>` | Yes | Deletes one of your movies. Returns `{"deleted": <id>}`. |
| GET | `/external/search` | Yes | Searches TMDB. Params: `q` (required), `year` (optional). |
| POST | `/movies/import` | Yes | Body: `tmdb_id` (integer). Saves that TMDB movie to your watchlist. `201` if added, `200` if you already had it. |
| GET | `/recommendations` | Yes | Returns `results` (up to 10 movies, each with a `score` and a `because` list) and `based_on`. `502` if TMDB is unavailable. |

### Example

```
# Sign up and keep the token
TOKEN=$(curl -s -X POST http://localhost:5050/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"password123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# Search TMDB
curl -s "http://localhost:5050/external/search?q=inception" -H "Authorization: Bearer $TOKEN"

# Add a movie by hand, then list your watchlist
curl -s -X POST http://localhost:5050/movies \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Inception","year":2010}'
curl -s http://localhost:5050/movies -H "Authorization: Bearer $TOKEN"
```

## Project layout

```
app.py              Flask app factory and the movie and search routes
auth.py             signup, login, JWT creation, and the login_required decorator
recommendations.py  the /recommendations route and the ranking logic
tmdb.py             small client for the TMDB API
models.py           User and Movie database models
config.py           reads settings from environment variables
db.py               shared SQLAlchemy instance
tests/              pytest suite (auth, movies, search, health, recommendations)
Dockerfile, docker-compose.yml   the app and a Postgres database for local runs
.github/workflows/ci.yml         runs the tests on every push and pull request
```

## Known limitations

- CORS is open to any origin and the app runs on Flask's built-in server. For production I would restrict CORS to the frontend's domain and serve with Gunicorn.
- Database tables are created with `db.create_all()`. A migration tool such as Alembic would be the next step for schema changes.
- The login token is stored in the browser's localStorage by the frontend, which is simple but exposed to XSS. HttpOnly cookies would be safer.
