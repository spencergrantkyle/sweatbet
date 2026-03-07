"""
Seed script for the Wazzax bet.

Creates:
- Spencer user (if not exists)
- Warren "Wazzax" user (if not exists)
- 1 bet: 15km/week x 4 weeks walking challenge (PENDING)
- Stores opponent_id in bet description as JSON

Run via: railway run python scripts/seed_wazzax_bet.py
"""

import json
import os
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    create_engine, Column, String, Float, Integer, BigInteger,
    DateTime, ForeignKey, Enum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


# Minimal model copies (just enough columns for the seed)

class BetStatus(str, PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class ActivityType(str, PyEnum):
    RUN = "Run"
    RIDE = "Ride"
    WALK = "Walk"
    HIKE = "Hike"
    SWIM = "Swim"
    WORKOUT = "Workout"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strava_athlete_id = Column(BigInteger, unique=True, index=True, nullable=False)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bet(Base):
    __tablename__ = "bets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    wager_amount = Column(Float, nullable=False, default=0.0)
    activity_type = Column(Enum(ActivityType), nullable=False)
    distance_km = Column(Float, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    deadline = Column(DateTime, nullable=False)
    status = Column(Enum(BetStatus), nullable=False, default=BetStatus.PENDING)
    verified_activity_id = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Config
SPENCER_STRAVA_ID = 12345678
WARREN_STRAVA_ID = 99999901
BET_START = datetime(2026, 3, 7)
BET_END = datetime(2026, 4, 4)
WEEKLY_TARGET_KM = 15.0


def get_db_url():
    """Use DATABASE_PUBLIC_URL > DATABASE_URL > local SQLite."""
    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if url and "railway.internal" in url:
        print("WARNING: DATABASE_URL uses Railway internal DNS (not reachable locally).")
        print("Falling back to local SQLite. To seed Railway, use 'railway proxy' + DATABASE_PUBLIC_URL.")
        return "sqlite:///./dev.db"
    if url:
        return url
    return "sqlite:///./dev.db"


def seed():
    engine = create_engine(get_db_url())
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Upsert Spencer
        spencer = db.query(User).filter(User.strava_athlete_id == SPENCER_STRAVA_ID).first()
        if not spencer:
            spencer = User(
                strava_athlete_id=SPENCER_STRAVA_ID,
                firstname="Spencer",
                lastname="Kyle",
            )
            db.add(spencer)
            db.flush()
            print(f"Created Spencer (id={spencer.id})")
        else:
            print(f"Spencer already exists (id={spencer.id})")

        # Upsert Warren
        warren = db.query(User).filter(User.strava_athlete_id == WARREN_STRAVA_ID).first()
        if not warren:
            warren = User(
                strava_athlete_id=WARREN_STRAVA_ID,
                firstname="Warren",
                lastname="Wazzax",
            )
            db.add(warren)
            db.flush()
            print(f"Created Warren (id={warren.id})")
        else:
            print(f"Warren already exists (id={warren.id})")

        # Check if bet already exists
        existing_bet = (
            db.query(Bet)
            .filter(Bet.creator_id == spencer.id, Bet.title == "15km per week x 4 weeks")
            .first()
        )
        if existing_bet:
            print(f"\nBet already exists (id={existing_bet.id})")
            print(f"URL: /bet/{existing_bet.id}/confirm")
            return

        # Create the bet
        bet = Bet(
            creator_id=spencer.id,
            title="15km per week x 4 weeks",
            description=json.dumps({"opponent_id": str(warren.id)}),
            wager_amount=2500.0,
            activity_type=ActivityType.WALK,
            distance_km=WEEKLY_TARGET_KM,
            deadline=BET_END,
            status=BetStatus.PENDING,
            created_at=BET_START,
        )
        db.add(bet)
        db.commit()

        print(f"\nBet created (id={bet.id})")
        print(f"  Title: {bet.title}")
        print(f"  Activity: Walk | Target: {WEEKLY_TARGET_KM}km/week ({WEEKLY_TARGET_KM * 4}km total)")
        print(f"  Dates: {BET_START.strftime('%d %b %Y')} -> {BET_END.strftime('%d %b %Y')}")
        print(f"  Stake: R2,500 ZAR")
        print(f"  Spencer (Creator, Confirmed) VS Warren (Challenger, Pending)")
        print(f"\nConfirmation URL: /bet/{bet.id}/confirm")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
