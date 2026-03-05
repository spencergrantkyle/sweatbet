"""
P0 Critical Path Tests for SweatBet.

Tests the most critical user flows:
- Bet creation validation
- Auth requirement enforcement
- OAuth callback validation
- Bet detail/list authorization
- Settings endpoint auth
- Legal pages accessibility
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from backend.fastapi.main import app

client = TestClient(app)


class TestBetCreationValidation:
    """Bet creation requires authentication."""

    def test_create_bet_requires_auth(self):
        response = client.post(
            "/bets/create",
            data={
                "title": "Test Bet",
                "activity_type": "Run",
                "distance_km": "5",
                "deadline": "2099-12-31T23:59",
                "wager_amount": "50",
            },
            follow_redirects=False,
        )
        # Should redirect to login or return 401
        assert response.status_code in (302, 303, 307, 401, 403)

    def test_create_bet_page_requires_auth(self):
        response = client.get("/bets/create", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)


class TestBetAuthorization:
    """API endpoints enforce authentication."""

    def test_api_bets_list_requires_auth(self):
        response = client.get("/api/v1/bets", follow_redirects=False)
        assert response.status_code in (401, 403)

    def test_api_bet_detail_requires_auth(self):
        response = client.get(
            "/api/v1/bets/00000000-0000-0000-0000-000000000000",
            follow_redirects=False,
        )
        assert response.status_code in (401, 403)

    def test_bet_detail_page_requires_auth(self):
        response = client.get(
            "/bets/00000000-0000-0000-0000-000000000000",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307, 401, 403)

    def test_bets_list_page_requires_auth(self):
        response = client.get("/bets", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)


class TestOAuthCallbackValidation:
    """OAuth callback handles error cases gracefully."""

    def test_callback_with_error_param_redirects(self):
        response = client.get(
            "/auth/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307)

    def test_callback_missing_code_redirects(self):
        response = client.get("/auth/callback", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 400)

    def test_callback_invalid_state_redirects(self):
        response = client.get(
            "/auth/callback",
            params={"code": "fake_code", "state": "invalid_state"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307, 400)


class TestBetCancellation:
    """Bet cancellation requires auth."""

    def test_cancel_bet_requires_auth(self):
        response = client.post(
            "/bets/00000000-0000-0000-0000-000000000000/cancel",
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 401, 403, 404, 405)


class TestSettingsEndpoints:
    """Settings endpoints require authentication."""

    def test_settings_page_requires_auth(self):
        response = client.get("/settings", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)

    def test_export_requires_auth(self):
        response = client.get("/settings/export", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)

    def test_disconnect_requires_auth(self):
        response = client.post("/settings/disconnect", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)

    def test_delete_account_requires_auth(self):
        response = client.post("/settings/delete", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)


class TestDashboard:
    """Dashboard requires auth."""

    def test_dashboard_requires_auth(self):
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code in (302, 303, 307, 401, 403)


class TestLegalPages:
    """Legal/public pages should be accessible without auth."""

    def test_landing_page_loads(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_privacy_page_loads(self):
        response = client.get("/privacy")
        assert response.status_code == 200

    def test_terms_page_loads(self):
        response = client.get("/terms")
        assert response.status_code == 200
