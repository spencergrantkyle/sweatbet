# SweatBet Development Guide with Railway Deployment

> **A comprehensive guide for junior developers to understand, develop, and deploy the SweatBet application**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Directory Structure](#3-directory-structure)
4. [Core Components Deep Dive](#4-core-components-deep-dive)
5. [Development Environment Setup](#5-development-environment-setup)
6. [Railway Deployment Guide](#6-railway-deployment-guide)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [Database Configuration](#8-database-configuration)
9. [Strava OAuth Integration](#9-strava-oauth-integration)
10. [Testing](#10-testing)
11. [Development Workflow](#11-development-workflow)
12. [MVP Feature Roadmap](#12-mvp-feature-roadmap)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Project Overview

### What is SweatBet?

SweatBet is a **fitness motivation platform** that enables users to place financial bets on their fitness goals. Activities are automatically verified via the **Strava API**, creating real financial stakes to drive accountability and commitment to fitness.

### The Problem We're Solving

People struggle with fitness motivation and accountability. SweatBet addresses this by combining:
- **Financial stakes** (you put money on the line)
- **Automatic verification** (Strava tracks your activities)
- **Social accountability** (challenge friends in 1v1 bets)

### Target Users

- **Primary**: Strava users (120M+ athletes) - runners and cyclists
- **Secondary Focus**: South African market (1M+ ParkRun participants, 400K+ race participants)
- **Tertiary**: Anyone seeking fitness motivation through financial accountability

### Core User Flow

```
Sign Up → Link Strava → Create Bet → Accept Challenge → Activity Deadline → Auto-Verify → Settle
```

---

## 2. Architecture & Tech Stack

### Backend Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern async Python web framework |
| **SQLAlchemy** | ORM for database operations (sync + async) |
| **PostgreSQL** | Production database (via Railway) |
| **SQLite** | Local development database |
| **Pydantic** | Data validation and settings management |
| **Uvicorn** | ASGI server for running FastAPI |
| **HTTPX** | Async HTTP client for Strava API calls |

### Frontend Stack

| Technology | Purpose |
|------------|---------|
| **Jinja2** | Server-side template engine |
| **HTML/CSS** | UI markup and styling |
| **Outfit Font** | Modern typography (Google Fonts) |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization for deployment |
| **Railway** | Cloud platform for hosting (PaaS) |
| **Strava API** | Activity data and OAuth authentication |

### Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Browser)                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   Routers    │→ │  Endpoints   │→ │  Services (Strava API)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│         │                 │                      │                  │
│         ▼                 ▼                      ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Middleware  │  │    CRUD      │  │     External APIs        │  │
│  │  (CORS,      │  │  Operations  │  │     (Strava OAuth)       │  │
│  │   Session)   │  └──────────────┘  └──────────────────────────┘  │
│  └──────────────┘         │                                         │
│                           ▼                                         │
│                    ┌──────────────┐                                 │
│                    │   Models     │                                 │
│                    │ (SQLAlchemy) │                                 │
│                    └──────────────┘                                 │
│                           │                                         │
└───────────────────────────│─────────────────────────────────────────┘
                            ▼
                 ┌──────────────────────┐
                 │      Database        │
                 │  (SQLite / PostgreSQL)│
                 └──────────────────────┘
```

---

## 3. Directory Structure

```
SweatBet/
├── DevelopSweatBetWithRailway.md  # This guide!
├── SweatBetPRD.md                 # Product Requirements Document
│
├── Fullstack-FastAPI/             # Main application directory
│   ├── Dockerfile                 # Container configuration
│   ├── requirements.txt           # Python dependencies
│   ├── README.md                  # Quick start guide
│   ├── pytest.ini                 # Test configuration
│   ├── dev.db                     # SQLite database (local dev)
│   ├── zeabur_fastapi.yaml        # Alternative deployment config
│   │
│   ├── backend/                   # Backend application code
│   │   ├── __init__.py
│   │   │
│   │   ├── data/                  # Initial/seed data
│   │   │   ├── __init__.py
│   │   │   └── init_data.py       # Seed data definitions
│   │   │
│   │   ├── fastapi/               # FastAPI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # Application entry point ⭐
│   │   │   │
│   │   │   ├── api/               # API layer
│   │   │   │   └── v1/
│   │   │   │       └── endpoints/ # Route handlers
│   │   │   │           ├── auth.py       # Strava OAuth ⭐
│   │   │   │           ├── dashboard.py  # User dashboard ⭐
│   │   │   │           ├── landing.py    # Landing page ⭐
│   │   │   │           ├── base.py       # Base routes
│   │   │   │           ├── doc.py        # API docs routes
│   │   │   │           └── message.py    # Example CRUD API
│   │   │   │
│   │   │   ├── core/              # Core configuration
│   │   │   │   ├── config.py      # Environment settings ⭐
│   │   │   │   ├── constants.py   # Application constants
│   │   │   │   ├── init_settings.py # Settings initialization
│   │   │   │   ├── lifespan.py    # App startup/shutdown
│   │   │   │   ├── middleware.py  # CORS, sessions, etc.
│   │   │   │   └── routers.py     # Route registration
│   │   │   │
│   │   │   ├── crud/              # Database operations
│   │   │   │   └── message.py     # Example CRUD service
│   │   │   │
│   │   │   ├── dependencies/      # FastAPI dependencies
│   │   │   │   ├── database.py    # DB session management ⭐
│   │   │   │   └── rate_limiter.py
│   │   │   │
│   │   │   ├── models/            # SQLAlchemy models
│   │   │   │   ├── message.py     # Example model
│   │   │   │   └── user.py        # User & StravaToken ⭐
│   │   │   │
│   │   │   ├── schemas/           # Pydantic schemas
│   │   │   │   ├── message.py     # Message validation
│   │   │   │   └── user.py        # User/Strava schemas ⭐
│   │   │   │
│   │   │   └── services/          # External service integrations
│   │   │       └── strava.py      # Strava API client ⭐
│   │   │
│   │   ├── security/              # Auth/authorization
│   │   │   ├── authentication.py
│   │   │   └── authorization.py
│   │   │
│   │   └── tests/                 # Test suite
│   │       ├── test_api_async.py
│   │       ├── test_api_sync.py
│   │       └── test_speed.py
│   │
│   └── frontend/                  # Frontend templates & assets
│       ├── assets/
│       │   └── favicon.ico
│       │
│       ├── login/                 # Legacy login templates
│       │   ├── static/
│       │   └── templates/
│       │
│       └── sweatbet/              # Main SweatBet UI ⭐
│           ├── static/
│           │   └── style.css      # Main stylesheet
│           └── templates/
│               ├── base.html      # Base template
│               ├── landing.html   # Home page
│               └── dashboard.html # User dashboard
│
└── StravaDocs/                    # Strava API reference docs
    ├── Strava Developers_1.pdf
    ├── Strava Developers_API Ref.pdf
    ├── Strava Developers_Authentication.pdf
    └── Strava Developers_How to create a webhook.pdf
```

> ⭐ = Key files you'll work with most often

---

## 4. Core Components Deep Dive

### 4.1 Application Entry Point (`main.py`)

The application starts in `backend/fastapi/main.py`. Here's what happens:

```python
# Creates FastAPI app with lifespan management
app = FastAPI(
    title="SweatBet",
    description="Fitness motivation platform with financial accountability",
    version="1.0.0",
    lifespan=lifespan  # Handles startup/shutdown
)

# Mounts static files for CSS/JS
app.mount("/sweatbet/static", StaticFiles(...), name="sweatbet-static")

# Sets up middleware (CORS, sessions, doc protection)
setup_cors(app)
setup_session(app)

# Registers all route handlers
setup_routers(app)
```

**How to run locally:**
```bash
python -m backend.fastapi.main --mode dev --host 127.0.0.1
```

### 4.2 Configuration System (`core/config.py`)

SweatBet uses a dual-mode configuration system:

- **DevSettings**: SQLite database, localhost URLs
- **ProdSettings**: PostgreSQL database, Railway-provided URLs

```python
class DevSettings(Settings):
    ENV_MODE: str = 'dev'
    DEV_DB_URL: str = "sqlite:///./dev.db"

class ProdSettings(Settings):
    ENV_MODE: str = 'prod'
    DATABASE_URL: str = ''  # Provided by Railway
    HOST_URL: str = ''      # Your Railway domain
```

**Key Properties:**
- `DB_URL`: Returns the appropriate database URL
- `ASYNC_DB_URL`: Returns async-compatible database URL
- `API_BASE_URL`: Returns the base URL for API calls

### 4.3 Database Layer (`dependencies/database.py`)

The database layer supports both synchronous and asynchronous operations:

```python
# Synchronous (for simple queries)
def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Asynchronous (for better performance)
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
```

**Usage in endpoints:**
```python
@router.get("/dashboard")
async def dashboard(db: Session = Depends(get_sync_db)):
    # db is now available for queries
    pass
```

### 4.4 User Model (`models/user.py`)

Two main models for user data:

```python
class User(Base):
    """SweatBet user linked to Strava"""
    id = Column(UUID, primary_key=True)
    strava_athlete_id = Column(BigInteger, unique=True)
    firstname = Column(String)
    lastname = Column(String)
    profile_picture = Column(String)  # Strava profile URL
    
class StravaToken(Base):
    """OAuth tokens for Strava API access"""
    user_id = Column(UUID, ForeignKey("users.id"))
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(BigInteger)  # Unix timestamp
```

### 4.5 Strava Service (`services/strava.py`)

The Strava client handles all OAuth and API interactions:

```python
class StravaClient:
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
    API_BASE = "https://www.strava.com/api/v3"
    
    def get_authorization_url(self, state): ...
    async def exchange_code(self, code): ...
    async def refresh_access_token(self, refresh_token): ...
    async def get_athlete_activities(self, access_token): ...
    async def ensure_valid_token(self, access_token, refresh_token, expires_at): ...
```

**Key methods:**
- `get_authorization_url()`: Generates Strava OAuth URL
- `exchange_code()`: Trades auth code for tokens
- `ensure_valid_token()`: Auto-refreshes expired tokens

### 4.6 OAuth Flow (`api/v1/endpoints/auth.py`)

The complete Strava OAuth flow:

```
1. User clicks "Connect with Strava"
   ↓
2. GET /auth/strava
   - Generate state token (CSRF protection)
   - Store state in session
   - Redirect to Strava authorization page
   ↓
3. User authorizes on Strava
   ↓
4. GET /auth/callback?code=...&state=...
   - Verify state token matches
   - Exchange code for tokens
   - Create/update User in database
   - Store tokens in StravaToken table
   - Set session (user_id, strava_athlete_id)
   - Redirect to /dashboard
```

### 4.7 Middleware (`core/middleware.py`)

Three middleware components:

1. **CORS Middleware**: Allows cross-origin requests
2. **Session Middleware**: Manages user sessions (24-hour expiry)
3. **Doc Protection**: Requires login to access /docs and /redoc

---

## 5. Development Environment Setup

### Prerequisites

- **Python 3.9+** (preferably 3.12)
- **Git** for version control
- **Strava Developer Account** for API access

### Step-by-Step Setup

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd SweatBet/Fullstack-FastAPI
```

#### 2. Create Virtual Environment

```bash
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Create Environment File

Create a `.env` file in the `Fullstack-FastAPI` directory:

```env
# Application
APP_NAME=SweatBet
APP_VERSION=1.0.0

# Strava OAuth (get these from https://www.strava.com/settings/api)
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:5000/auth/callback

# Security
SECRET_KEY=generate-a-secure-random-string-here

# Optional: API doc protection
USER_NAME=admin
PASSWORD=your_secure_password
```

#### 5. Register Strava Application

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application
3. Set **Authorization Callback Domain** to `localhost`
4. Copy Client ID and Client Secret to your `.env`

#### 6. Run the Development Server

```bash
# From the Fullstack-FastAPI directory
python -m backend.fastapi.main --mode dev --host 127.0.0.1
```

The app will be available at `http://localhost:5000`

#### 7. Access the Application

- **Landing Page**: http://localhost:5000
- **API Docs** (after login): http://localhost:5000/docs
- **Dashboard** (after Strava auth): http://localhost:5000/dashboard

---

## 6. Railway Deployment Guide

### What is Railway?

Railway is a modern **Platform as a Service (PaaS)** that makes deploying applications simple. It provides:
- **Automatic Docker builds** from your Dockerfile
- **Managed PostgreSQL** databases
- **Environment variable management**
- **Automatic HTTPS**
- **Deploy previews** for pull requests

### Deployment Architecture on Railway

```
┌─────────────────────────────────────────────────────┐
│                   Railway Project                    │
│                                                     │
│  ┌─────────────────┐    ┌─────────────────────┐    │
│  │   PostgreSQL    │◄───│   FastAPI Service   │    │
│  │    (Database)   │    │   (from Dockerfile) │    │
│  │                 │    │                     │    │
│  │ DATABASE_URL    │    │ Uses DATABASE_URL   │    │
│  │ auto-generated  │    │ env variable        │    │
│  └─────────────────┘    └─────────────────────┘    │
│                                │                    │
│                                ▼                    │
│                         ┌──────────────┐           │
│                         │ Custom Domain │           │
│                         │ or Railway   │           │
│                         │   subdomain  │           │
│                         └──────────────┘           │
└─────────────────────────────────────────────────────┘
```

### Step-by-Step Railway Deployment

#### Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended for automatic deployments)

#### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Select your SweatBet repository
4. Railway will detect the Dockerfile automatically

#### Step 3: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database" → "Add PostgreSQL"**
3. Railway automatically provisions a PostgreSQL instance
4. The `DATABASE_URL` variable is automatically created

#### Step 4: Configure Environment Variables

In your Railway FastAPI service, add these variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | *Auto-linked from PostgreSQL* | Database connection string |
| `HOST_URL` | `https://your-app.railway.app` | Your Railway domain |
| `STRAVA_CLIENT_ID` | Your Strava Client ID | From Strava API settings |
| `STRAVA_CLIENT_SECRET` | Your Strava Client Secret | From Strava API settings |
| `STRAVA_REDIRECT_URI` | `https://your-app.railway.app/auth/callback` | OAuth callback URL |
| `SECRET_KEY` | Generate secure random string | Session encryption key |
| `USER_NAME` | Your admin username | For API docs access |
| `PASSWORD` | Your admin password | For API docs access |

**To generate a secure SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 5: Update Strava Application Settings

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Update **Authorization Callback Domain** to your Railway domain (without https://)
   - Example: `your-app.railway.app`

#### Step 6: Deploy

Railway automatically deploys when you push to your connected branch:

```bash
git add .
git commit -m "Configure for Railway deployment"
git push origin main
```

Monitor deployment in the Railway dashboard.

#### Step 7: Configure Custom Domain (Optional)

1. In Railway, go to your service settings
2. Click **"Settings" → "Domains"**
3. Add a custom domain
4. Update DNS records as instructed
5. Railway provides automatic HTTPS

### Understanding the Dockerfile

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.9-slim as builder

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies in virtual environment
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Second stage: Runtime image ---
FROM python:3.9-slim

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . /app

# Start the application in production mode
CMD ["python", "-m", "backend.fastapi.main", "--mode", "prod", "--host", "0.0.0.0"]
```

**Key points:**
- Multi-stage build reduces image size
- `--mode prod` activates production settings
- `--host 0.0.0.0` allows external connections
- Railway automatically sets the `PORT` environment variable

### Railway CLI (Alternative)

Install Railway CLI for local development:

```bash
# Install (macOS)
brew install railway

# Login
railway login

# Link project
railway link

# Run locally with Railway environment
railway run python -m backend.fastapi.main --mode prod

# Deploy manually
railway up
```

### Continuous Deployment

Railway automatically deploys on every push to your connected branch. For team workflows:

1. **main branch** → Production deployment
2. **Pull Requests** → Preview deployments (if enabled)

Configure in Railway: **Settings → Deploy → Autodeploys**

---

## 7. Environment Variables Reference

### Complete Variable List

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **Application** ||||
| `APP_NAME` | No | `SweatBet` | Application display name |
| `APP_VERSION` | No | `1.0.0` | Application version |
| **Database** ||||
| `DATABASE_URL` | Prod | - | Full PostgreSQL connection string |
| `DB_ENGINE` | Prod* | - | `postgresql` |
| `DB_USERNAME` | Prod* | - | Database username |
| `DB_PASS` | Prod* | - | Database password |
| `DB_HOST` | Prod* | - | Database host |
| `DB_PORT` | Prod* | - | Database port |
| `DB_NAME` | Prod* | - | Database name |
| **Strava OAuth** ||||
| `STRAVA_CLIENT_ID` | Yes | - | Strava API client ID |
| `STRAVA_CLIENT_SECRET` | Yes | - | Strava API client secret |
| `STRAVA_REDIRECT_URI` | Yes | - | OAuth callback URL |
| **Strava Webhooks** ||||
| `STRAVA_WEBHOOK_VERIFY_TOKEN` | No | `SWEATBET_WEBHOOK_TOKEN` | Token for webhook verification |
| `STRAVA_WEBHOOK_CALLBACK_URL` | Webhook | - | Public webhook URL (e.g., `https://your-app.railway.app/webhooks/strava`) |
| **Security** ||||
| `SECRET_KEY` | Yes | `dev-secret...` | Session encryption key |
| `USER_NAME` | No | - | API docs username |
| `PASSWORD` | No | - | API docs password |
| **Hosting** ||||
| `HOST_URL` | Prod | - | Production base URL |
| `PORT` | No | `5000` | Server port (Railway sets this) |

*Prod = Required in production if `DATABASE_URL` not provided

### Strava Webhook Setup

After deploying to Railway, you need to register your webhook with Strava:

1. **Add environment variables to Railway:**
   - `STRAVA_WEBHOOK_VERIFY_TOKEN`: A secret token you create (default: `SWEATBET_WEBHOOK_TOKEN`)
   - `STRAVA_WEBHOOK_CALLBACK_URL`: Your webhook URL (e.g., `https://your-app.railway.app/webhooks/strava`)

2. **Run the webhook management script:**
   ```bash
   python scripts/manage_webhook.py create
   ```

3. **Verify the subscription was created:**
   ```bash
   python scripts/manage_webhook.py view
   ```

4. **Test by completing a Strava activity** - check Railway logs for webhook events

### Environment Configuration Logic

```python
@property
def DB_URL(self):
    if self.ENV_MODE == "dev":
        return "sqlite:///./dev.db"  # Local SQLite
    else:
        if self.DATABASE_URL:
            return self.DATABASE_URL  # Railway provides this
        else:
            # Build from individual components
            return f'{DB_ENGINE}://{DB_USERNAME}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
```

---

## 8. Database Configuration

### Development: SQLite

SQLite is used for local development - zero configuration required:

```python
DEV_DB_URL: str = "sqlite:///./dev.db"
```

The database file `dev.db` is created automatically on first run.

### Production: PostgreSQL

On Railway, PostgreSQL is the production database:

```python
# Railway provides DATABASE_URL like:
# postgresql://username:password@host:port/database
```

### Database Migrations (Future)

Currently, the app uses `create_all()` which auto-creates tables:

```python
def init_db():
    Base.metadata.create_all(bind=sync_engine)
```

For future development, consider adding **Alembic** for proper migrations:

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Database Models Summary

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | SweatBet users linked to Strava |
| `StravaToken` | `strava_tokens` | OAuth tokens for API access |
| `Message` | `messages` | Example CRUD model (can be removed) |

---

## 9. Strava OAuth Integration

### OAuth 2.0 Flow Explained

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Browser   │         │  SweatBet   │         │   Strava    │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │  1. Click "Connect"   │                       │
       │──────────────────────>│                       │
       │                       │                       │
       │  2. Redirect to Strava│                       │
       │<──────────────────────│                       │
       │                       │                       │
       │  3. User authorizes   │                       │
       │──────────────────────────────────────────────>│
       │                       │                       │
       │  4. Redirect back with code                   │
       │<──────────────────────────────────────────────│
       │                       │                       │
       │  5. Send code         │                       │
       │──────────────────────>│                       │
       │                       │                       │
       │                       │  6. Exchange for tokens
       │                       │──────────────────────>│
       │                       │                       │
       │                       │  7. Access + Refresh  │
       │                       │<──────────────────────│
       │                       │                       │
       │  8. Redirect to dashboard                     │
       │<──────────────────────│                       │
       │                       │                       │
```

### Strava API Rate Limits

| Limit | Value |
|-------|-------|
| 15-minute limit | 200 requests |
| Daily limit | 2,000 requests |

**Best practices:**
- Cache activity data when possible
- Use webhooks for real-time updates (future feature)
- Batch API calls where possible

### Token Refresh Logic

Access tokens expire after 6 hours. The `ensure_valid_token` method handles refresh:

```python
async def ensure_valid_token(self, access_token, refresh_token, expires_at):
    # Add 5 minute buffer before expiry
    if time.time() >= (expires_at - 300):
        new_tokens = await self.refresh_access_token(refresh_token)
        return (new_tokens["access_token"], new_tokens["refresh_token"], 
                new_tokens["expires_at"], True)
    return (access_token, refresh_token, expires_at, False)
```

### Required Strava Scopes

```python
scope = "activity:read_all,read"
```

- `activity:read_all`: Access to all activities (including private)
- `read`: Basic profile access

---

## 10. Testing

### Running Tests

```bash
# From Fullstack-FastAPI directory
pytest

# With verbose output
pytest -v

# Run specific test file
pytest backend/tests/test_api_sync.py
```

### Test Configuration (`pytest.ini`)

```ini
[pytest]
testpaths = backend/tests
```

### Writing New Tests

Example test structure:

```python
# backend/tests/test_strava.py
import pytest
from backend.fastapi.services.strava import strava_client

def test_authorization_url():
    """Test that authorization URL is generated correctly"""
    url = strava_client.get_authorization_url(state="test123")
    assert "strava.com/oauth/authorize" in url
    assert "client_id=" in url
    assert "state=test123" in url

@pytest.mark.asyncio
async def test_token_refresh():
    """Test token refresh logic"""
    # Mock the token refresh
    pass
```

---

## 11. Development Workflow

### Git Branching Strategy

```
main (production)
  │
  ├── develop (integration branch)
  │     │
  │     ├── feature/bet-creation
  │     ├── feature/bet-settlement
  │     └── fix/strava-token-refresh
```

### Typical Feature Development Flow

1. **Create feature branch**
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/bet-creation
   ```

2. **Develop locally**
   ```bash
   python -m backend.fastapi.main --mode dev
   # Make changes, test in browser
   ```

3. **Write tests**
   ```bash
   pytest -v
   ```

4. **Commit with clear messages**
   ```bash
   git add .
   git commit -m "feat: add bet creation endpoint with validation"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/bet-creation
   # Create Pull Request on GitHub
   ```

6. **Deploy to Railway** (automatic on merge to main)

### Code Style Guidelines

- Use **type hints** for function signatures
- Follow **PEP 8** style guide
- Document endpoints with docstrings
- Keep endpoints focused and small
- Use dependency injection for database sessions

---

## 12. MVP Feature Roadmap

### Currently Implemented ✅

- [x] Strava OAuth integration
- [x] User registration via Strava
- [x] Token storage and refresh
- [x] Dashboard with activity display
- [x] Landing page with "Connect with Strava" CTA
- [x] Session management
- [x] Docker containerization
- [x] Railway deployment ready

### MVP Features To Build 🚧

#### Phase 1: Core Betting (Priority)

| Feature | Description | Endpoints Needed |
|---------|-------------|------------------|
| **Bet Model** | Database model for bets | - |
| **Create Bet** | Set distance, deadline, amount | `POST /bets` |
| **View Bets** | List user's active/past bets | `GET /bets` |
| **Bet Details** | Single bet view | `GET /bets/{id}` |

**Bet Model (Suggested)**:
```python
class Bet(Base):
    __tablename__ = "bets"
    
    id = Column(UUID, primary_key=True)
    creator_id = Column(UUID, ForeignKey("users.id"))
    bet_type = Column(String)  # "solo", "1v1"
    activity_type = Column(String)  # "Run", "Ride"
    distance_km = Column(Float)
    wager_amount = Column(Float)
    deadline = Column(DateTime)
    status = Column(String)  # "pending", "active", "won", "lost"
    created_at = Column(DateTime)
```

#### Phase 2: Verification Engine

| Feature | Description |
|---------|-------------|
| **Activity Matcher** | Match Strava activities to bet requirements |
| **Auto-Verification** | Check if bet conditions are met |
| **Settlement Logic** | Update bet status on deadline |

#### Phase 3: Social Features

| Feature | Description |
|---------|-------------|
| **Friend Challenges** | Invite friends to 1v1 bets |
| **Notifications** | Email/push for bet reminders |
| **Bet History** | View past bets and outcomes |

### Out of Scope (Post-MVP)

- ❌ Group bets with pool logic
- ❌ Real-time payment processing
- ❌ Mobile native apps
- ❌ Time-based bet verification
- ❌ Charitable donation integration
- ❌ Leaderboards and social feeds

---

## 13. Troubleshooting

### Common Issues

#### 1. "Module not found" errors

**Cause**: Running from wrong directory or venv not activated

**Solution**:
```bash
cd Fullstack-FastAPI
source venv/bin/activate
python -m backend.fastapi.main --mode dev
```

#### 2. Strava OAuth Error: "invalid_state"

**Cause**: State token mismatch (session expired or CSRF attack)

**Solution**: Clear browser cookies and try again

#### 3. Database "table already exists" warnings

**Cause**: `create_all()` runs on every startup

**Solution**: This is normal for development. Consider Alembic for production.

#### 4. Railway: "Build failed"

**Cause**: Missing dependency or Dockerfile error

**Solution**: 
- Check Railway build logs
- Test Docker build locally:
  ```bash
  docker build -t sweatbet .
  docker run -p 5000:5000 sweatbet
  ```

#### 5. "STRAVA_CLIENT_ID is empty"

**Cause**: Environment variables not loaded

**Solution**:
- Ensure `.env` file exists in `Fullstack-FastAPI/`
- Check variable names match exactly
- Restart the server

#### 6. Token refresh failing

**Cause**: Strava refresh token expired or revoked

**Solution**: 
- User needs to re-authenticate
- Clear their session and redirect to `/auth/strava`

### Debugging Tips

1. **Enable SQL echo**:
   ```python
   # In database.py
   async_engine = create_async_engine(url, echo=True)  # Logs all SQL
   ```

2. **Check session data**:
   ```python
   @router.get("/debug-session")
   async def debug_session(request: Request):
       return dict(request.session)
   ```

3. **Railway logs**:
   ```bash
   railway logs
   # Or view in Railway dashboard
   ```

4. **Local production mode test**:
   ```bash
   # Temporarily set env vars and run in prod mode
   export DATABASE_URL="sqlite:///./test.db"
   python -m backend.fastapi.main --mode prod --host 127.0.0.1
   ```

---

## Quick Reference Commands

```bash
# Start development server
python -m backend.fastapi.main --mode dev --host 127.0.0.1

# Run tests
pytest -v

# Build Docker image
docker build -t sweatbet .

# Run Docker container
docker run -p 5000:5000 --env-file .env sweatbet

# Railway CLI
railway login
railway link
railway up
railway logs

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Check installed packages
pip list

# Update requirements
pip freeze > requirements.txt
```

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Strava API Documentation](https://developers.strava.com/)
- [Railway Documentation](https://docs.railway.app/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/)

---

*Last updated: January 2026*
*SweatBet MVP v1.0.0*

