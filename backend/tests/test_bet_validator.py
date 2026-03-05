"""Tests for bet validation logic."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from backend.fastapi.models.bet import Bet, BetStatus, BetType, ActivityType, StakeRecipientType
from backend.fastapi.services.bet_validator import validate_activity_for_bet


def make_bet(**kwargs):
    """Create a mock Bet with sensible defaults."""
    defaults = {
        "title": "Test Bet",
        "activity_type": ActivityType.RUN,
        "distance_km": 5.0,
        "time_seconds": None,
        "deadline": datetime.utcnow() + timedelta(days=7),
        "status": BetStatus.ACTIVE,
        "wager_amount": 100.0,
        "currency": "ZAR",
    }
    defaults.update(kwargs)
    bet = MagicMock(spec=Bet)
    for k, v in defaults.items():
        setattr(bet, k, v)
    return bet


def make_activity(**kwargs):
    """Create a mock Strava activity dict."""
    defaults = {
        "id": 12345678,
        "type": "Run",
        "distance": 6000,  # meters
        "moving_time": 1800,  # 30 minutes
        "name": "Morning Run",
        "start_date": (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    defaults.update(kwargs)
    return defaults


class TestActivityTypeMatching:
    """Tests for activity type validation."""

    def test_matching_run(self):
        bet = make_bet(activity_type=ActivityType.RUN)
        activity = make_activity(type="Run")
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_matching_ride(self):
        bet = make_bet(activity_type=ActivityType.RIDE)
        activity = make_activity(type="Ride", distance=20000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_wrong_activity_type(self):
        bet = make_bet(activity_type=ActivityType.RUN)
        activity = make_activity(type="Ride")
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False
        assert "type" in result.reason.lower()

    def test_walk_type(self):
        bet = make_bet(activity_type=ActivityType.WALK, distance_km=2.0)
        activity = make_activity(type="Walk", distance=3000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_swim_type(self):
        bet = make_bet(activity_type=ActivityType.SWIM, distance_km=1.0)
        activity = make_activity(type="Swim", distance=2000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True


class TestDistanceValidation:
    """Tests for distance requirement validation."""

    def test_distance_exceeds_requirement(self):
        bet = make_bet(distance_km=5.0)
        activity = make_activity(distance=6000)  # 6km > 5km
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_distance_exactly_meets_requirement(self):
        bet = make_bet(distance_km=5.0)
        activity = make_activity(distance=5000)  # 5km == 5km
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_distance_below_requirement(self):
        bet = make_bet(distance_km=10.0)
        activity = make_activity(distance=8000)  # 8km < 10km
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False
        assert "distance" in result.reason.lower()

    def test_no_distance_requirement(self):
        bet = make_bet(distance_km=None)
        activity = make_activity(distance=100)  # Any distance should pass
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_zero_distance_requirement(self):
        bet = make_bet(distance_km=0)
        activity = make_activity(distance=1000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_very_short_distance(self):
        bet = make_bet(distance_km=0.5)
        activity = make_activity(distance=600)  # 0.6km > 0.5km
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_marathon_distance(self):
        bet = make_bet(distance_km=42.195)
        activity = make_activity(distance=42200)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True


class TestTimeValidation:
    """Tests for time limit validation."""

    def test_within_time_limit(self):
        bet = make_bet(time_seconds=3600)  # 1 hour
        activity = make_activity(moving_time=2400)  # 40 minutes
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_exceeds_time_limit(self):
        bet = make_bet(time_seconds=1800)  # 30 minutes
        activity = make_activity(moving_time=2400)  # 40 minutes
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False
        assert "time" in result.reason.lower()

    def test_no_time_limit(self):
        bet = make_bet(time_seconds=None)
        activity = make_activity(moving_time=36000)  # 10 hours
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_exactly_at_time_limit(self):
        bet = make_bet(time_seconds=1800)
        activity = make_activity(moving_time=1800)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True


class TestDeadlineValidation:
    """Tests for deadline validation."""

    def test_activity_before_deadline(self):
        bet = make_bet(deadline=datetime.utcnow() + timedelta(days=7))
        activity = make_activity(
            start_date=(datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_activity_after_deadline(self):
        bet = make_bet(deadline=datetime.utcnow() - timedelta(days=1))
        activity = make_activity(
            start_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False
        assert "deadline" in result.reason.lower()

    def test_missing_start_date(self):
        """Activity without start_date should still validate other criteria."""
        bet = make_bet(deadline=datetime.utcnow() + timedelta(days=7))
        activity = make_activity()
        del activity["start_date"]
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True


class TestCombinedValidation:
    """Tests for multiple criteria validation."""

    def test_all_criteria_pass(self):
        bet = make_bet(
            activity_type=ActivityType.RUN,
            distance_km=5.0,
            time_seconds=3600,
            deadline=datetime.utcnow() + timedelta(days=7),
        )
        activity = make_activity(
            type="Run",
            distance=6000,
            moving_time=1800,
        )
        result = validate_activity_for_bet(activity, bet)
        assert result.success is True

    def test_right_type_wrong_distance(self):
        bet = make_bet(activity_type=ActivityType.RUN, distance_km=10.0)
        activity = make_activity(type="Run", distance=5000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False

    def test_right_distance_wrong_type(self):
        bet = make_bet(activity_type=ActivityType.RUN, distance_km=5.0)
        activity = make_activity(type="Ride", distance=10000)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False

    def test_right_type_distance_but_over_time(self):
        bet = make_bet(
            activity_type=ActivityType.RUN,
            distance_km=5.0,
            time_seconds=1200,  # 20 minutes
        )
        activity = make_activity(type="Run", distance=6000, moving_time=1500)
        result = validate_activity_for_bet(activity, bet)
        assert result.success is False


class TestBetModel:
    """Tests for Bet model properties."""

    def test_time_remaining_display_days(self):
        bet = Bet()
        bet.deadline = datetime.utcnow() + timedelta(days=3, hours=5)
        assert "3d" in bet.time_remaining_display

    def test_time_remaining_display_hours(self):
        bet = Bet()
        bet.deadline = datetime.utcnow() + timedelta(hours=5, minutes=30)
        assert "5h" in bet.time_remaining_display

    def test_time_remaining_display_expired(self):
        bet = Bet()
        bet.deadline = datetime.utcnow() - timedelta(hours=1)
        assert bet.time_remaining_display == "Expired"

    def test_currency_symbol_zar(self):
        bet = Bet()
        bet.currency = "ZAR"
        assert bet.currency_symbol == "R"

    def test_wager_display_with_amount(self):
        bet = Bet()
        bet.currency = "ZAR"
        bet.wager_amount = 100
        assert bet.wager_display == "R100"

    def test_wager_display_no_amount(self):
        bet = Bet()
        bet.currency = "ZAR"
        bet.wager_amount = 0
        assert bet.wager_display == "No wager"

    def test_distance_display(self):
        bet = Bet()
        bet.distance_km = 5.0
        assert bet.distance_display == "5.0 km"

    def test_distance_display_none(self):
        bet = Bet()
        bet.distance_km = None
        assert bet.distance_display == "Any distance"

    def test_is_expired_true(self):
        bet = Bet()
        bet.deadline = datetime.utcnow() - timedelta(hours=1)
        assert bet.is_expired is True

    def test_is_expired_false(self):
        bet = Bet()
        bet.deadline = datetime.utcnow() + timedelta(hours=1)
        assert bet.is_expired is False
