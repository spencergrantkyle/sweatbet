"""Pydantic schemas for Bet-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BetStatus(str, Enum):
    """Status of a bet."""
    PENDING = "pending"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class ActivityType(str, Enum):
    """Supported Strava activity types for bets."""
    RUN = "Run"
    RIDE = "Ride"
    WALK = "Walk"
    HIKE = "Hike"
    SWIM = "Swim"
    WORKOUT = "Workout"


class BetBase(BaseModel):
    """Base bet schema."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    wager_amount: float = Field(default=0.0, ge=0)
    activity_type: ActivityType
    distance_km: Optional[float] = Field(None, gt=0)
    time_seconds: Optional[int] = Field(None, gt=0)
    deadline: datetime


class BetCreate(BetBase):
    """Schema for creating a new bet."""
    
    @field_validator('deadline')
    @classmethod
    def deadline_must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.utcnow():
            raise ValueError('Deadline must be in the future')
        return v

    @field_validator('distance_km')
    @classmethod
    def distance_must_be_reasonable(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v > 1000:
            raise ValueError('Distance cannot exceed 1000 km')
        return v


class BetUpdate(BaseModel):
    """Schema for updating a bet."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[BetStatus] = None


class BetRead(BetBase):
    """Schema for reading bet data."""
    id: UUID
    creator_id: UUID
    status: BetStatus
    verified_activity_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BetSummary(BaseModel):
    """Summary view of a bet for lists."""
    id: UUID
    title: str
    activity_type: ActivityType
    distance_km: Optional[float]
    deadline: datetime
    status: BetStatus
    wager_amount: float

    class Config:
        from_attributes = True

