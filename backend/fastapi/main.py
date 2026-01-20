import os
import uvicorn
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from backend.fastapi.core.init_settings import args, global_settings
from backend.fastapi.core.middleware import setup_cors, setup_session, add_doc_protect
from backend.fastapi.core.lifespan import lifespan
from backend.fastapi.core.routers import setup_routers

# Initiate a FastAPI App.
app = FastAPI(
    title="SweatBet",
    description="Fitness motivation platform with financial accountability",
    version="1.0.0",
    lifespan=lifespan
)

# Frontend - SweatBet templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")
app.mount("/sweatbet/static", StaticFiles(directory="frontend/sweatbet/static"), name="sweatbet-static")

# Legacy login templates (keep for compatibility)
app.mount("/static", StaticFiles(directory="frontend/login/static"), name="static")

# Set Middleware
setup_cors(app)
add_doc_protect(app)
setup_session(app)

# Setup Routers
setup_routers(app)

if __name__ == "__main__":
    uvicorn.run(
        app="backend.fastapi.main:app",
        host = args.host,
        port=int(os.getenv("PORT", 5000)),
        reload=args.mode == "dev"
    )