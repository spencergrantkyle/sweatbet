# SweatBet Development Guide

## Project Overview
SweatBet is a fitness accountability platform where users bet on their own fitness goals, verified automatically via the Strava API. Built with Python/FastAPI + Jinja2 templates.

## Tech Stack
- **Backend**: FastAPI (Python 3.12), SQLAlchemy ORM, APScheduler
- **Frontend**: Jinja2 templates, vanilla CSS (mobile-first)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **External**: Strava API (OAuth + webhooks), Telegram Bot API
- **Deploy**: Docker on Railway

## Running Locally
```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in Strava credentials
python -m backend.fastapi.main --mode dev --host 0.0.0.0
```

## Project Structure
```
backend/fastapi/
  main.py              # App initialization
  core/                # Config, middleware, routers, lifespan
  models/              # SQLAlchemy models (User, Bet, StravaToken, etc.)
  schemas/             # Pydantic schemas
  services/            # Strava client, bet validator, scheduler, telegram
  api/v1/endpoints/    # Route handlers
  dependencies/        # DB sessions, auth helpers
frontend/sweatbet/
  templates/           # Jinja2 HTML templates
  static/              # CSS
scripts/
  manage_webhook.py    # CLI for Strava webhook management
```

## Key Patterns
- Auth is session-based via Strava OAuth (no email/password)
- Common auth helpers in `dependencies/auth.py`
- Webhook handler uses background tasks with their own DB sessions
- Individual bets start as ACTIVE immediately (no PENDING step)
- Currency is ZAR (R) - South African Rand

## Strava Compliance (CRITICAL)
- Each user only sees their OWN data - never another user's
- Raw Strava data is NOT stored beyond verification needs
- App is framed as "personal accountability" NOT "competition/race"
- Must use "Powered by Strava" branding per guidelines
- Deauthorization webhook deletes all user data

## Testing
```bash
python -m pytest backend/tests/ -v
```
