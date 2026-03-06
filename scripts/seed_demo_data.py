"""
Seed script for SweatBet demo data.

Creates:
- 1 demo user (Spencer Kyle, strava_athlete_id=12345678)
- 1 Strava token for the demo user
- 3 demo bets in different states (active, won, lost)
- 1 processed activity for the won bet
"""

import sys
import time
import uuid
from datetime import datetime, timedelta

# Ensure we can import from the project root
sys.path.insert(0, ".")

from backend.fastapi.dependencies.database import init_db, SyncSessionLocal
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.models.bet import Bet, BetStatus, ActivityType
from backend.fastapi.models.processed_activity import ProcessedActivity


def seed():
    init_db()
    db = SyncSessionLocal()

    try:
        # Check if demo user already exists
        existing = db.query(User).filter(User.strava_athlete_id == 12345678).first()
        if existing:
            print(f"Demo user already exists (id={existing.id}). Clearing and re-seeding...")
            # Delete existing bets, processed activities, tokens
            db.query(Bet).filter(Bet.creator_id == existing.id).delete()
            db.query(ProcessedActivity).filter(ProcessedActivity.user_id == existing.id).delete()
            db.query(StravaToken).filter(StravaToken.user_id == existing.id).delete()
            db.delete(existing)
            db.commit()

        # Create demo user
        user = User(
            strava_athlete_id=12345678,
            firstname="Spencer",
            lastname="Kyle",
            profile_picture=None,
        )
        db.add(user)
        db.flush()
        print(f"Created demo user: Spencer Kyle (id={user.id})")

        # Create Strava token
        token = StravaToken(
            user_id=user.id,
            access_token="demo_access_token",
            refresh_token="demo_refresh_token",
            expires_at=int(time.time()) + 86400,
            scope="activity:read_all,read",
        )
        db.add(token)
        print("Created demo Strava token")

        now = datetime.utcnow()

        # Bet 1: Active - Morning 5K
        bet1 = Bet(
            creator_id=user.id,
            title="Morning 5K",
            description="Complete a 5km run before the deadline",
            wager_amount=100.0,
            activity_type=ActivityType.RUN,
            distance_km=5.0,
            time_seconds=None,
            deadline=now + timedelta(days=1),
            status=BetStatus.ACTIVE,
        )
        db.add(bet1)
        print("Created bet: Morning 5K (active, R100, deadline tomorrow)")

        # Bet 2: Won - Weekend Long Run
        bet2 = Bet(
            creator_id=user.id,
            title="Weekend Long Run",
            description="Complete a 10km run over the weekend",
            wager_amount=200.0,
            activity_type=ActivityType.RUN,
            distance_km=10.0,
            time_seconds=None,
            deadline=now - timedelta(days=1),
            status=BetStatus.WON,
            verified_activity_id="9876543210",
            verified_at=now - timedelta(days=1, hours=3),
        )
        db.add(bet2)
        db.flush()
        print("Created bet: Weekend Long Run (won, R200)")

        # Processed activity for the won bet
        processed = ProcessedActivity(
            strava_activity_id=9876543210,
            user_id=user.id,
            bet_id=bet2.id,
            validation_result=True,
            validation_details="Activity matched: Run, 10.5km >= 10.0km required",
        )
        db.add(processed)
        print("Created processed activity for won bet")

        # Bet 3: Lost - StrideStreak Challenge
        bet3 = Bet(
            creator_id=user.id,
            title="StrideStreak Challenge",
            description="Complete a 3km run - missed the deadline!",
            wager_amount=50.0,
            activity_type=ActivityType.RUN,
            distance_km=3.0,
            time_seconds=None,
            deadline=now - timedelta(days=2),
            status=BetStatus.LOST,
        )
        db.add(bet3)
        print("Created bet: StrideStreak Challenge (lost, R50)")

        db.commit()
        print("\nDemo data seeded successfully!")
        print(f"Demo user ID: {user.id}")
        print("Login via: http://localhost:5000/auth/demo-login")

    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
