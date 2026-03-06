"""Shared authentication dependency for SweatBet endpoints."""

import uuid
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User


async def get_current_user(request: Request, db: Session) -> User | None:
    """Get the current authenticated user from session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None

    user = db.query(User).filter(User.id == user_uuid).first()
    return user


def require_auth(request: Request, db: Session = Depends(get_sync_db)) -> User:
    """Dependency that requires user authentication. Raises 401 if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
