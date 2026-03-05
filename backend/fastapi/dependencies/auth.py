"""Common authentication dependencies for SweatBet endpoints."""

import uuid
import logging
from typing import Optional

from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User

logger = logging.getLogger(__name__)


async def get_current_user(request: Request, db: Session = Depends(get_sync_db)) -> Optional[User]:
    """Get the current authenticated user from session. Returns None if not logged in."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None

    user = db.query(User).filter(User.id == user_uuid).first()
    return user


async def require_auth(request: Request, db: Session = Depends(get_sync_db)) -> User:
    """Dependency that requires user authentication. Raises 401 if not logged in."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user
