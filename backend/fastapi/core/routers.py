from fastapi import FastAPI
from backend.fastapi.api.v1.endpoints import base, doc, message, auth, dashboard, landing, bet, legal, settings, webhook

def setup_routers(app: FastAPI):
    # SweatBet routes
    app.include_router(landing.router, prefix="", tags=["landing"])
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(dashboard.router, prefix="", tags=["dashboard"])
    app.include_router(bet.router, prefix="", tags=["bets"])
    app.include_router(legal.router, prefix="", tags=["legal"])
    app.include_router(settings.router, prefix="", tags=["settings"])
    app.include_router(webhook.router, prefix="", tags=["webhook"])
    
    # Original template routes
    app.include_router(doc.router, prefix="", tags=["doc"])
    app.include_router(message.router, prefix="/api/v1", tags=["message"])
