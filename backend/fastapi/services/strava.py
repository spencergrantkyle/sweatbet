"""
Strava OAuth and API client for SweatBet.

Handles:
- OAuth authorization URL generation
- Token exchange (authorization code -> access/refresh tokens)
- Token refresh (when access token expires)
- Fetching athlete activities
"""

import time
from urllib.parse import urlencode
from typing import Optional
import httpx

from backend.fastapi.core.init_settings import global_settings as settings


class StravaClient:
    """Client for interacting with Strava OAuth and API."""
    
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
    API_BASE = "https://www.strava.com/api/v3"
    
    REQUEST_TIMEOUT = 15.0  # seconds

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: str = None
    ):
        self.client_id = client_id or settings.STRAVA_CLIENT_ID
        self.client_secret = client_secret or settings.STRAVA_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.STRAVA_REDIRECT_URI
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate the Strava OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Full authorization URL to redirect the user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": "activity:read_all,read"
        }
        
        if state:
            params["state"] = state
            
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Strava callback
            
        Returns:
            Dict containing:
            - token_type: "Bearer"
            - expires_at: Unix timestamp when access token expires
            - expires_in: Seconds until expiry
            - refresh_token: Token to refresh access
            - access_token: Token for API calls
            - athlete: Summary of athlete information
        """
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token for the user
            
        Returns:
            Dict containing new access_token, refresh_token, and expires_at
        """
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_athlete(self, access_token: str) -> dict:
        """
        Get the authenticated athlete's profile.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Athlete profile data
        """
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.get(
                f"{self.API_BASE}/athlete",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_athlete_activities(
        self,
        access_token: str,
        page: int = 1,
        per_page: int = 30,
        before: Optional[int] = None,
        after: Optional[int] = None
    ) -> list:
        """
        Fetch the authenticated athlete's activities.
        
        Args:
            access_token: Valid access token
            page: Page number (default 1)
            per_page: Number of activities per page (default 30, max 200)
            before: Unix timestamp to filter activities before
            after: Unix timestamp to filter activities after
            
        Returns:
            List of activity summaries
        """
        params = {
            "page": page,
            "per_page": per_page
        }
        
        if before:
            params["before"] = before
        if after:
            params["after"] = after
            
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.get(
                f"{self.API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def get_activity(self, access_token: str, activity_id: int) -> dict:
        """
        Get detailed information about a specific activity.
        
        Args:
            access_token: Valid access token
            activity_id: Strava activity ID
            
        Returns:
            Detailed activity data
        """
        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
            response = await client.get(
                f"{self.API_BASE}/activities/{activity_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def ensure_valid_token(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: int
    ) -> tuple[str, str, int, bool]:
        """
        Ensure we have a valid access token, refreshing if necessary.
        
        Args:
            access_token: Current access token
            refresh_token: Current refresh token
            expires_at: Unix timestamp when access token expires
            
        Returns:
            Tuple of (access_token, refresh_token, expires_at, was_refreshed)
        """
        # Add 5 minute buffer before expiry
        if time.time() >= (expires_at - 300):
            new_tokens = await self.refresh_access_token(refresh_token)
            return (
                new_tokens["access_token"],
                new_tokens["refresh_token"],
                new_tokens["expires_at"],
                True
            )
        return (access_token, refresh_token, expires_at, False)


# Global instance for convenience
strava_client = StravaClient()

