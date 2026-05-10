# Krine

Krine is a thought experiment about what an anonymous social platform could look like. It aims to empower users to share thoughts freely while leveraging local AI for content safety and organization.

## Features

- **Anonymous Posting** — no account registration, ever.
- **AI Moderation** — every post is analyzed for safety (filtering harmful content) and tagged with emotional/topical labels.
- **Community Interaction** — session-based likes and anonymous comments.
- **Smart Discovery** — sort by Newest, Popular, or Most Commented; filter by post type or time window.

## Tech Stack

- **Backend**: Django 5+
- **Frontend**: HTML, vanilla CSS, vanilla JavaScript
- **AI/ML**: PyTorch + HuggingFace Transformers (zero-shot classification)
- **Database**: SQLite by default; PostgreSQL supported via `DATABASE_URL`
- **Cache (optional)**: Redis
- **Object storage (optional)**: any S3-compatible service

## AI Note

The project was created using a lot of help from Antigravity.

---

## Quick start (local, no Docker)

Requires Python 3.10+.

```bash
git clone <your-fork-url> krine
cd krine

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set SECRET_KEY (or leave it empty with DEBUG=True)

python manage.py migrate
python manage.py runserver
```

Open http://localhost:8000.

The first request that triggers AI moderation will download the
`valhalla/distilbart-mnli-12-3` model (~500 MB). Set `USE_AI_API=True` and
provide a `HUGGINGFACE_API_KEY` to call HuggingFace's hosted inference
instead — useful on RAM-limited machines.

## Quick start (Docker)

Requires Docker and Docker Compose.

```bash
git clone <your-fork-url> krine
cd krine

cp .env.example .env
# edit .env — set SECRET_KEY, POSTGRES_PASSWORD, ALLOWED_HOSTS, etc.

docker compose up --build
```

The stack runs four services: `web` (Django + Gunicorn), `db` (Postgres 15),
`redis`, and `nginx` on port 80. The `nginx` service serves `/static/` and
`/media/` directly and proxies everything else to `web`.

The Postgres container provisions itself from `POSTGRES_DB`, `POSTGRES_USER`,
and `POSTGRES_PASSWORD` in `.env` on first start. `DATABASE_URL` should match
those credentials, e.g.
`postgres://krine:CHANGE_ME@db:5432/krine`.

Static files are not collected automatically. Run once after the stack is up:

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py migrate
```

## AI moderation

Every new post is analyzed in a background thread before it becomes visible
in the public feed. The pipeline is two stages:

1. **Regex pre-check** — emails and phone numbers are flagged immediately.
2. **Zero-shot classification** against two label sets:
   - **Safety**: Safe, Hate Speech, Violence, Harassment, Personal Information
   - **Vibes** (top 3 are stored as tags): Nostalgic, Hopeful, Melancholy,
     Venting, Confession, Lonely, Healing, etc.

Posts trip the safety filter when:

- the `Safe` score collapses below 3%, or
- `Harassment` exceeds `Safe` by 3× and is itself above 0.10 (catches
  targeted attacks while letting general venting through), or
- `Violence`, `Hate Speech`, or `Personal Information` cross fixed
  thresholds.

### Local mode vs API mode

Toggled by `USE_AI_API` in `.env`:

- **`USE_AI_API=False` (default)** — the model loads in-process via
  `transformers.pipeline`. ~500 MB download on first run, then ~1.5 GB
  resident. Fine for a workstation; tight on a 1 GB VPS.
- **`USE_AI_API=True`** — calls `api-inference.huggingface.co` instead.
  Requires `HUGGINGFACE_API_KEY`. No local RAM cost.

If the model fails to load (or the API errors out), the analyzer falls back
to a tiny keyword blocklist. Posts are never silently published — failed
analysis still marks the post `is_analyzed=True` so it leaves the pending
state.

## Environment variables

All configuration lives in `.env`. See [`.env.example`](.env.example) for the
full list with inline comments. Highlights:

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes (when `DEBUG=False`) | Django cryptographic key |
| `DEBUG` | No | `True` for local dev, `False` in production |
| `ALLOWED_HOSTS` | Yes (when `DEBUG=False`) | Comma-separated hostnames Django will serve |
| `CSRF_TRUSTED_ORIGINS` | Yes (when serving over HTTPS) | Comma-separated origins including scheme |
| `BEHIND_PROXY` | No | Set `True` only when terminating TLS at an upstream proxy |
| `DATABASE_URL` | No | Postgres URL; falls back to local SQLite if unset |
| `REDIS_URL` | No | Enables Redis cache backend when set |
| `USE_AI_API` | No | `True` to use HuggingFace Inference API instead of local model |
| `HUGGINGFACE_API_KEY` | If `USE_AI_API=True` | API token from huggingface.co |
| `SENTRY_DSN` | No | Enables Sentry error tracking when set |
| `GOOGLE_ANALYTICS_ID` | No | GA measurement ID; tag is omitted if empty |
| `USE_S3` | No | `True` to serve static/media from S3-compatible storage |

## Tests

```bash
python manage.py test core
```

The test suite in `core/tests.py` mocks the HuggingFace pipeline, so it runs
without downloading the model and without network access.

## Deployment notes

This repo ships a working `Dockerfile` and `docker-compose.yml`, but it
intentionally doesn't pin you to any specific host. A typical deployment:

1. Provision a Linux server with Docker and a public IP.
2. Point a DNS record at it. Decide whether you want a CDN/proxy
   (Cloudflare, etc.) in front — if yes, set `BEHIND_PROXY=True`.
3. Clone the repo, copy `.env.example` to `.env`, and fill in:
   - a fresh `SECRET_KEY` (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - a strong `POSTGRES_PASSWORD` (and matching `DATABASE_URL`)
   - your hostnames in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
   - `DEBUG=False`
4. `docker compose up -d --build`
5. `docker compose exec web python manage.py migrate`
6. `docker compose exec web python manage.py collectstatic --noinput`
7. `docker compose exec web python manage.py createsuperuser` (for the admin)

For TLS, terminate at your proxy (Cloudflare, Caddy, or a separate nginx with
Let's Encrypt) and forward to the `nginx` container's port 80. The bundled
`nginx/default.conf` is HTTP-only by design.

For object storage, set `USE_S3=True` and the `AWS_*` variables. This works
with AWS S3, DigitalOcean Spaces, Backblaze B2, MinIO, or any S3-compatible
endpoint.

## Contributing

Pull requests are welcome. To keep things sane:

- Run `python manage.py test core` before opening a PR.
- For UI changes, please test the create/list/detail flows in a browser.
- Don't commit `.env`, the SQLite database, or the HuggingFace model cache.
- Keep new dependencies minimal and justify them in the PR description.

Found a bug or have a feature idea? Open an issue first if it's a
larger change, so we can agree on the approach before you write code.

## License

Krine is released under the [MIT License](LICENSE).
