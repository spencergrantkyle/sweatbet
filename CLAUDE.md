# CLAUDE.md

## Project Overview

**SweatBet** is a fitness motivation platform that lets users place financial bets on fitness goals, verified automatically via the Strava API. Users link their Strava account, create bets with distance/time targets, and the system automatically verifies completion using Strava activity data and webhooks.

- **Target market:** Strava users (runners/cyclists), South Africa focused
- **Stack:** Python 3.12, FastAPI, SQLAlchemy, Jinja2 templates, SQLite (dev) / PostgreSQL (prod)
- **Deployment:** Railway via Docker

## Repository Structure

```
sweatbet/
├── backend/
│   ├── fastapi/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/v1/endpoints/    # Route handlers (auth, bet, dashboard, settings, webhook, etc.)
│   │   ├── core/                # Config, middleware, lifespan, routers
│   │   ├── crud/                # Database CRUD operations
│   │   ├── dependencies/        # DB sessions, rate limiter
│   │   ├── models/              # SQLAlchemy ORM models (User, Bet, StravaToken, etc.)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   └── services/            # Business logic (Strava API, Telegram, activity scheduler, bet validator)
│   ├── data/                    # Seed/init data
│   ├── security/                # Auth helpers
│   └── tests/                   # Pytest test suite
├── frontend/
│   ├── login/                   # Legacy login page (static + templates)
│   └── sweatbet/                # Main app UI (Jinja2 templates + CSS)
├── scripts/                     # Utility scripts (webhook management)
├── StravaDocs/                  # Strava API reference PDFs
├── Dockerfile                   # Multi-stage Docker build
├── railway.toml                 # Railway deployment config
└── requirements.txt             # Python dependencies
```

## Development Setup

### Prerequisites
- Python 3.12
- A `.env` file in the project root (see Environment Variables below)

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run in dev mode (SQLite, auto-reload)
python -m backend.fastapi.main --mode dev --host 127.0.0.1

# Run in prod mode
python -m backend.fastapi.main --mode prod --host 0.0.0.0
```

The app runs on port 5000 by default (configurable via `PORT` env var).

### Running Tests
```bash
pytest backend/tests/
```

Tests use `FastAPI.TestClient` (sync) and `httpx.AsyncClient` (async). The test suite auto-detects pytest and defaults to dev mode with SQLite.

## Architecture & Key Patterns

### App Initialization Flow
1. `main.py` creates the FastAPI app with lifespan handler
2. `core/init_settings.py` parses CLI args (`--mode dev|prod`) and creates settings
3. `core/lifespan.py` initializes DB, seeds data, starts background scheduler
4. `core/middleware.py` sets up CORS, session middleware, and docs protection
5. `core/routers.py` registers all route handlers

### Configuration
- Settings use `pydantic-settings` with `.env` file support
- `DevSettings`: SQLite (`dev.db`), localhost base URL
- `ProdSettings`: PostgreSQL via `DATABASE_URL` or individual DB params
- Access settings via `from backend.fastapi.core.init_settings import global_settings`

### Database
- **ORM:** SQLAlchemy with both sync and async session support
- **Models:** `User`, `StravaToken`, `Bet`, `BetReminder`, `ProcessedActivity`, `Message`
- **Base class:** `backend.fastapi.dependencies.database.Base`
- Dev uses SQLite; prod uses PostgreSQL with asyncpg
- DB is initialized via `init_db()` which calls `Base.metadata.create_all()`

### API Structure
- Routes are versioned under `/api/v1/` (for message CRUD)
- Main app routes use flat prefixes: `/auth`, `/bets`, `/settings`, etc.
- Templates are server-rendered via Jinja2 (not a SPA)

### Key Services
- **`services/strava.py`**: Strava OAuth token management and activity fetching
- **`services/telegram.py`**: Telegram bot notifications for bet events
- **`services/activity_scheduler.py`**: APScheduler background job that checks Strava activities and validates bets
- **`services/bet_validator.py`**: Logic to verify if Strava activities satisfy bet criteria

### Authentication
- Strava OAuth 2.0 flow (authorization code grant)
- Session-based auth via `starlette.middleware.sessions.SessionMiddleware`
- Session stores `user_id` and `strava_athlete_id` after OAuth callback
- `/docs` and `/redoc` are protected behind session authentication

## Environment Variables

Required in `.env`:
```
# Strava OAuth
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REDIRECT_URI=

# Strava Webhook
STRAVA_WEBHOOK_VERIFY_TOKEN=SWEATBET_WEBHOOK_TOKEN

# Telegram Notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Session Security
SECRET_KEY=

# Production Database (prod mode only)
DATABASE_URL=          # Full PostgreSQL URL (Railway provides this)
```

## Conventions

### Code Style
- Python with type hints on schemas and service functions
- SQLAlchemy models use UUID primary keys
- Pydantic v2 for request/response validation
- Enums for status fields (`BetStatus`, `ActivityType`)

### File Organization
- One endpoint file per feature domain in `api/v1/endpoints/`
- Matching schema, model, and service files per domain
- Templates in `frontend/sweatbet/templates/` with `base.html` layout inheritance

### Naming
- Models: PascalCase singular (`User`, `Bet`, `StravaToken`)
- Tables: snake_case plural (`users`, `bets`, `strava_tokens`)
- Endpoints: kebab-case or slash-separated paths
- Templates: snake_case HTML files

### Important Notes
- Never commit `.env` files or database files (`*.db`)
- The `Fullstack-FastAPI/` directory is an empty reference template — do not use
- `StravaDocs/` contains reference PDFs, not deployed to production
- Frontend is server-rendered Jinja2, not a JS SPA — changes go in `.html` templates and `style.css`
- The app uses `datetime.utcnow()` throughout for timestamps
