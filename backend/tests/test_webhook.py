"""Tests for Strava webhook endpoint."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from backend.fastapi.main import app

client = TestClient(app)


class TestWebhookVerification:
    """Tests for GET /webhooks/strava - subscription verification."""

    def test_valid_verification(self):
        response = client.get(
            "/webhooks/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test_challenge_123",
                "hub.verify_token": "SWEATBET_WEBHOOK_TOKEN",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["hub.challenge"] == "test_challenge_123"

    def test_invalid_mode(self):
        response = client.get(
            "/webhooks/strava",
            params={
                "hub.mode": "unsubscribe",
                "hub.challenge": "test",
                "hub.verify_token": "SWEATBET_WEBHOOK_TOKEN",
            }
        )
        assert response.status_code == 400

    def test_missing_challenge(self):
        response = client.get(
            "/webhooks/strava",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "SWEATBET_WEBHOOK_TOKEN",
            }
        )
        assert response.status_code == 400

    def test_wrong_verify_token(self):
        response = client.get(
            "/webhooks/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "test",
                "hub.verify_token": "wrong_token",
            }
        )
        assert response.status_code == 403


class TestWebhookEvents:
    """Tests for POST /webhooks/strava - event handling."""

    def test_activity_create_event(self):
        response = client.post(
            "/webhooks/strava",
            json={
                "object_type": "activity",
                "object_id": 12345678,
                "aspect_type": "create",
                "owner_id": 99999,
                "subscription_id": 1,
                "event_time": 1234567890,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["action"] == "activity_create"

    def test_activity_update_event(self):
        response = client.post(
            "/webhooks/strava",
            json={
                "object_type": "activity",
                "object_id": 12345678,
                "aspect_type": "update",
                "owner_id": 99999,
                "subscription_id": 1,
                "event_time": 1234567890,
                "updates": {"title": "New Title"},
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "activity_update"

    def test_activity_delete_event(self):
        response = client.post(
            "/webhooks/strava",
            json={
                "object_type": "activity",
                "object_id": 12345678,
                "aspect_type": "delete",
                "owner_id": 99999,
                "subscription_id": 1,
                "event_time": 1234567890,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "activity_delete"

    def test_deauthorization_event(self):
        response = client.post(
            "/webhooks/strava",
            json={
                "object_type": "athlete",
                "object_id": 99999,
                "aspect_type": "update",
                "owner_id": 99999,
                "subscription_id": 1,
                "event_time": 1234567890,
                "updates": {"authorized": "false"},
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "deauthorization"

    def test_unknown_event(self):
        response = client.post(
            "/webhooks/strava",
            json={
                "object_type": "unknown",
                "object_id": 12345,
                "aspect_type": "create",
                "owner_id": 99999,
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_invalid_json(self):
        response = client.post(
            "/webhooks/strava",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400


class TestLandingPage:
    """Tests for the landing page."""

    def test_landing_page_loads(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "SweatBet" in response.text

    def test_landing_has_strava_connect(self):
        response = client.get("/")
        assert "Connect with Strava" in response.text


class TestUnauthenticatedAccess:
    """Tests that protected routes redirect unauthenticated users."""

    def test_dashboard_redirects(self):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code in (302, 307)

    def test_bets_create_redirects(self):
        response = client.get("/bets/create", follow_redirects=False)
        assert response.status_code in (302, 307)

    def test_bets_list_redirects(self):
        response = client.get("/bets", follow_redirects=False)
        assert response.status_code in (302, 307)

    def test_settings_redirects(self):
        response = client.get("/settings", follow_redirects=False)
        assert response.status_code in (302, 307)
