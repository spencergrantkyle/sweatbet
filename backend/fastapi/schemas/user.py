"""Pydantic schemas for User and Strava-related data."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class StravaAthleteData(BaseModel):
    """Strava athlete data returned from OAuth token exchange."""
    id: int
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    profile: Optional[str] = None  # Profile picture URL
    profile_medium: Optional[str] = None


class StravaTokenResponse(BaseModel):
    """Response from Strava token exchange endpoint."""
    token_type: str
    expires_at: int
    expires_in: int
    refresh_token: str
    access_token: str
    athlete: StravaAthleteData


class UserBase(BaseModel):
    """Base user schema."""
    strava_athlete_id: int
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    profile_picture: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserRead(UserBase):
    """Schema for reading user data."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StravaTokenBase(BaseModel):
    """Base Strava token schema."""
    access_token: str
    refresh_token: str
    expires_at: int
    scope: Optional[str] = None


class StravaTokenCreate(StravaTokenBase):
    """Schema for creating a new Strava token."""
    user_id: UUID


class StravaTokenRead(StravaTokenBase):
    """Schema for reading Strava token data."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StravaActivity(BaseModel):
    """Schema for a Strava activity."""
    id: int
    name: str
    type: str
    distance: float  # in meters
    moving_time: int  # in seconds
    elapsed_time: int  # in seconds
    start_date_local: str
    average_speed: Optional[float] = None
    max_speed: Optional[float] = None
    total_elevation_gain: Optional[float] = None

