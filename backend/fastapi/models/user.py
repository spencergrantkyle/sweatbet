import uuid
from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from backend.fastapi.dependencies.database import Base


class User(Base):
    """User model representing a SweatBet user linked to Strava."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strava_athlete_id = Column(BigInteger, unique=True, index=True, nullable=False)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to tokens
    tokens = relationship("StravaToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, strava_athlete_id={self.strava_athlete_id}, name={self.firstname} {self.lastname})>"

    @property
    def full_name(self):
        return f"{self.firstname or ''} {self.lastname or ''}".strip()


class StravaToken(Base):
    """Strava OAuth tokens for a user."""
    __tablename__ = "strava_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(BigInteger, nullable=False)  # Unix timestamp
    scope = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to user
    user = relationship("User", back_populates="tokens")

    def __repr__(self):
        return f"<StravaToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"

    @property
    def is_expired(self) -> bool:
        """Check if the access token has expired."""
        import time
        return time.time() >= self.expires_at

