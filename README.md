
# FastAPI Authentication & Billing Service

A FastAPI backend that provides login/registration, OAuth, OTP, email verification, and Stripe-based subscriptions. It runs async with PostgreSQL, Redis, and Celery so you can plug it into a SaaS dashboard or API-first product.

## Project Structure

```text
fastapi-saas-starter/
|-- .github/
|   `-- workflows/ci.yml
|-- alembic/
|   |-- env.py
|   |-- script.py.mako
|   `-- versions/
|-- src/
|   |-- admin/
|   |   |-- ai_repo.py
|   |   |-- ai_settings.py
|   |   |-- ai_utils.py
|   |   |-- ai_vars.py
|   |   |-- config.py
|   |   |-- dependencies.py
|   |   |-- emails.py
|   |   |-- models.py
|   |   |-- repository.py
|   |   |-- router.py
|   |   |-- schemas.py
|   |   |-- services.py
|   |   `-- utils.py
|   |-- auth/
|   |   |-- config.py
|   |   |-- dependencies.py
|   |   |-- emails.py
|   |   |-- models.py
|   |   |-- repository.py
|   |   |-- router.py
|   |   |-- schemas.py
|   |   |-- service.py
|   |   `-- utils.py
|   |-- billing/
|   |   |-- dependencies.py
|   |   |-- emails.py
|   |   |-- models.py
|   |   |-- repository.py
|   |   |-- router.py
|   |   |-- schemas.py
|   |   |-- service.py
|   |   |-- stripe_gateway.py
|   |   `-- tasks.py
|   |-- common/
|   |   `-- enums.py
|   |-- settings/
|   |   |-- app.py
|   |   |-- celery.py
|   |   |-- database.py
|   |   |-- mail.py
|   |   |-- redis.py
|   |   `-- stripe.py
|   |-- auth_bearer.py
|   |-- celery_app.py
|   |-- config.py
|   |-- database.py
|   |-- dependencies.py
|   |-- hashing.py
|   |-- jwt.py
|   |-- logging.py
|   |-- main.py
|   |-- models.py
|   |-- paginate.py
|   |-- rate_limiter.py
|   |-- repository.py
|   |-- tasks.py
|   `-- utils.py
|-- static/
|   `-- admin/
|-- templates/
|   `-- email/
|-- tests/
|   |-- auth/
|   |-- billing/
|   `-- conftest.py
|-- .env.example
|-- Dockerfile
|-- alembic.ini
|-- docker-compose.yml
|-- pyproject.toml
`-- uv.lock
```

## Technical Overview
- FastAPI app with per-domain routers (`src/auth/router.py`, `src/billing/router.py`, `src/admin/router.py`), CORS, structured logging, and slowapi rate limiting.
- Service/repository layers over async SQLAlchemy 2.0 + asyncpg; sync engine for Celery tasks.
- JWT access, refresh, and validation tokens with hashed refresh storage and rotation.
- Stripe Checkout + webhook handling for plans, subscriptions, renewals, and cancellations.
- SMTP email flows (verification, password reset, OTP, subscription notices) via FastAPI-Mail.
- Celery worker and beat for subscription emails and expiry sweeps.
- Admin module with AI-assisted features (audit logs, SQL/CSV export).

## Main Features
- Local auth: register/login, email verification, password reset/change.
- OTP login (email-delivered, single-use, 15-minute expiry).
- Social auth: Google and GitHub with state validation and auto-provisioning.
- Refresh token rotation with DB-backed JTI tracking and httpOnly cookies.
- Plans: create/update/soft-delete, tiering, and Stripe product/price sync.
- Subscriptions: checkout, upgrade, cancel-at-period-end, and access window enforcement.
- Stripe webhooks: checkout completion, invoice success/failure, subscription deleted.
- Payments recorded on invoice success; subscription emails dispatched via Celery.
- Admin dashboard with audit logging.
- Rate limiting (default 5/min) and request logging for observability.

## Technology Stack
- Python 3.12+, FastAPI, Starlette, Pydantic v2
- Async SQLAlchemy + asyncpg (PostgreSQL), Alembic migrations
- JWT via python-jose; Argon2 hashing (passlib)
- Stripe Python SDK
- Redis broker; Celery worker and beat
- FastAPI-Mail (SMTP + Jinja templates)
- slowapi for rate limiting; loguru for logging
- [uv](https://docs.astral.sh/uv/) for dependency management

## Requirements
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+
- Redis 7+
- Stripe keys (public, secret, webhook signing) for billing features
- SMTP credentials for transactional emails
- Google and GitHub OAuth credentials for social login
- Optional: Docker and docker-compose for containerised orchestration

## Quick Start (Local Development)

1. **Install uv** (if you haven't already):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies** (creates a `.venv` automatically):
   ```bash
   uv sync
   ```

3. **Install and start PostgreSQL & Redis** (Ubuntu/Debian):
   ```bash
   sudo apt-get install -y postgresql redis-server
   sudo systemctl start postgresql redis-server
   ```

4. **Create the database and user**:
   ```bash
   sudo -u postgres psql -c "CREATE USER dev_user WITH PASSWORD 'dev_pass' CREATEDB;"
   sudo -u postgres psql -c "CREATE DATABASE fastapi_saas OWNER dev_user;"
   sudo -u postgres psql -c "CREATE DATABASE fastapi_saas_test OWNER dev_user;"
   ```

5. **Configure environment**: copy `.env.example` to `.env` and adjust values (database URLs, secrets, etc.):
   ```bash
   cp .env.example .env
   # Edit .env — at minimum set DATABASE_URL, SYNC_DATABASE_URL, TEST_DATABASE_URL
   ```

6. **Run migrations**:
   ```bash
   uv run alembic upgrade head
   ```

7. **Start the API**:
   ```bash
   uv run uvicorn src.main:app --reload
   ```

8. **Start Celery** (separate terminals, optional for email/subscription background jobs):
   ```bash
   uv run celery -A src.celery_app.celery_app worker --loglevel=info
   uv run celery -A src.celery_app.beat_app beat --loglevel=info
   ```

The API docs are at http://localhost:8000/docs once running.

## Environment Variables

All settings are loaded via pydantic-settings from `.env`. See `.env.example` for the full list.

| Group | Variables |
|-------|-----------|
| App | `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_URL` |
| Database | `DATABASE_URL` (async/asyncpg), `SYNC_DATABASE_URL` (sync/psycopg for Celery), `TEST_DATABASE_URL` |
| JWT | `ALGORITHM`, `ACCESS_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE`, `REFRESH_SECRET_KEY`, `REFRESH_TOKEN_EXPIRE`, `VALIDATION_SECRET_KEY`, `VALIDATION_TOKEN_EXPIRE` |
| Mail | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, `GOOGLE_USERINFO_URL` |
| GitHub OAuth | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_AUTHORIZE_URL`, `GITHUB_TOKEN_URL`, `GITHUB_USER_API`, `GITHUB_EMAILS` |
| Redis | `REDIS_URL` |
| Celery | `CELERY_WORKER_URL`, `CELERY_BEAT_URL` |
| Stripe | `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| AI | `AI_PROVIDER`, `GROQ_API_KEY`, `GROQ_BASE_URL`, `AI_MODEL` |

## Running with Docker Compose

```bash
docker compose up --build
```

Services: `api`, `db` (Postgres 16), `redis`, `celery`, `celery_beat`. Health checks ensure the API waits for Postgres and Redis to be ready.

## Production Notes
- Set `APP_DEBUG=False`, tighten CORS origins, and set cookie `secure=True` in the auth router.
- Provide HTTPS termination (e.g., Nginx in front of Uvicorn/Gunicorn workers).
- Run workers with process managers (systemd/supervisor) or containers.
- Validate Stripe webhook signature with `STRIPE_WEBHOOK_SECRET` and expose the webhook URL publicly.

## Tests

```bash
uv run pytest
```

- Set `TEST_DATABASE_URL` to a dedicated test database.
- Tests spin up schema automatically, disable the rate limiter, and use httpx ASGI client fixtures.
- Mock Stripe/email in new tests to avoid real calls.

## API Overview
- **Auth**: `/register`, `/login`, `/refresh-token`, `/verify`, `/request/verify`, `/forget-password`, `/new-password`, `/change-password`, `/request/login-code`, `/login/code`, `/google/login` + callback, `/github/login` + callback, `/deactivate`.
- **Billing**: `/billing/plans` (list/create), `/billing/plans/{id}` (get/update/delete), `/billing/subscriptions/me`, `/billing/subscriptions/subscribe`, `/billing/subscriptions/upgrade`, `/billing/subscriptions/cancel`, `/billing/payments/me`, `/billing/stripe/webhook`.
- **Admin**: User management, audit logs, AI-assisted SQL/CSV export.

## Contribution Guidelines
- Fork/branch, keep PRs focused, and update docs when behaviors change.
- Add/adjust tests (`uv run pytest`) for any new logic; mock external providers.
- Run `uv run alembic upgrade head` and `uv run pytest` before pushing.
- Use clear commit messages and reference relevant modules/paths.

## License
MIT-style licensing (check repository for the full text).
