"""Pydantic schemas for Bet-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class BetStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class BetType(str, Enum):
    INDIVIDUAL = "individual"
    CHALLENGE = "challenge"
    GROUP = "group"


class StakeRecipientType(str, Enum):
    SWEATBET = "sweatbet"
    FRIEND = "friend"
    PBO = "pbo"


class ActivityType(str, Enum):
    RUN = "Run"
    RIDE = "Ride"
    WALK = "Walk"
    HIKE = "Hike"
    SWIM = "Swim"
    WORKOUT = "Workout"


class BetBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    bet_type: BetType = BetType.INDIVIDUAL
    wager_amount: float = Field(default=0.0, ge=0)
    currency: str = Field(default="ZAR", max_length=3)
    activity_type: ActivityType
    distance_km: Optional[float] = Field(None, gt=0)
    time_seconds: Optional[int] = Field(None, gt=0)
    deadline: datetime
    stake_recipient_type: Optional[StakeRecipientType] = StakeRecipientType.SWEATBET


class BetCreate(BetBase):
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
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[BetStatus] = None


class BetRead(BetBase):
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
    id: UUID
    title: str
    bet_type: BetType
    activity_type: ActivityType
    distance_km: Optional[float]
    deadline: datetime
    status: BetStatus
    wager_amount: float
    currency: str = "ZAR"

    class Config:
        from_attributes = True
