"""Bet model for SweatBet wagers."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.fastapi.dependencies.database import Base


class BetStatus(str, PyEnum):
    """Status of a bet."""
    PENDING = "pending"      # Bet created, waiting for deadline
    ACTIVE = "active"        # Bet is in progress
    WON = "won"             # User completed the challenge
    LOST = "lost"           # User failed to complete
    CANCELLED = "cancelled"  # Bet was cancelled


class ActivityType(str, PyEnum):
    """Supported Strava activity types for bets."""
    RUN = "Run"
    RIDE = "Ride"
    WALK = "Walk"
    HIKE = "Hike"
    SWIM = "Swim"
    WORKOUT = "Workout"


class Bet(Base):
    """Bet model representing a fitness wager."""
    __tablename__ = "bets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Creator relationship
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Bet details
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    wager_amount = Column(Float, nullable=False, default=0.0)
    
    # Challenge requirements
    activity_type = Column(Enum(ActivityType), nullable=False)
    distance_km = Column(Float, nullable=True)  # Required distance in kilometers
    time_seconds = Column(Integer, nullable=True)  # Optional time limit in seconds
    
    # Timeline
    deadline = Column(DateTime, nullable=False)
    
    # Status tracking
    status = Column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    
    # Verification
    verified_activity_id = Column(String, nullable=True)  # Strava activity ID that verified this bet
    verified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to creator
    creator = relationship("User", backref="bets")

    def __repr__(self):
        return f"<Bet(id={self.id}, title='{self.title}', status={self.status}, creator_id={self.creator_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the bet deadline has passed."""
        return datetime.utcnow() > self.deadline

    @property
    def time_remaining(self) -> int:
        """Get seconds remaining until deadline. Returns 0 if expired."""
        if self.is_expired:
            return 0
        delta = self.deadline - datetime.utcnow()
        return int(delta.total_seconds())

    @property
    def distance_display(self) -> str:
        """Format distance for display."""
        if self.distance_km:
            return f"{self.distance_km:.1f} km"
        return "Any distance"

    @property
    def time_display(self) -> str:
        """Format time limit for display."""
        if self.time_seconds:
            hours, remainder = divmod(self.time_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "No time limit"

