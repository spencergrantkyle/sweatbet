"""Health check endpoint for Railway deployment."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.fastapi.dependencies.database import get_sync_db

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_sync_db)):
    """Health check with DB connectivity verification."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return JSONResponse(content={
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status
    })
