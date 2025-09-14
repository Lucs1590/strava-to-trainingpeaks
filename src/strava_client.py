"""Strava API client for activity synchronization."""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv


class StravaAPIError(Exception):
    """Exception for Strava API related errors."""
    pass


class StravaClient:
    """Simple Strava API client for activity synchronization."""

    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        self.access_token = os.getenv("STRAVA_ACCESS_TOKEN")
        self.refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
        self.base_url = "https://www.strava.com/api/v3"

    async def get_activities(self, limit: int = 30, after: Optional[datetime] = None, before: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get recent activities from Strava."""
        if not self.access_token:
            raise StravaAPIError(
                "No access token available. Please authenticate first.")

        params = {"per_page": limit}
        if after:
            params["after"] = int(after.timestamp())
        if before:
            params["before"] = int(before.timestamp())

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{self.base_url}/activities", headers=headers, params=params)

            if response.status_code == 401:
                # Try to refresh token
                await self._refresh_access_token()
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = await client.get(f"{self.base_url}/activities", headers=headers, params=params)

            if response.status_code != 200:
                raise StravaAPIError(
                    f"Failed to fetch activities: {response.status_code} - {response.text}")

            return response.json()

    async def get_activity_detail(self, activity_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific activity."""
        if not self.access_token:
            raise StravaAPIError(
                "No access token available. Please authenticate first.")

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{self.base_url}/activities/{activity_id}", headers=headers)

            if response.status_code == 401:
                await self._refresh_access_token()
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = await client.get(f"{self.base_url}/activities/{activity_id}", headers=headers)

            if response.status_code != 200:
                raise StravaAPIError(
                    f"Failed to fetch activity {activity_id}: {response.status_code} - {response.text}")

            return response.json()

    async def get_activity_streams(self, activity_id: str, keys: List[str] = None) -> Dict[str, Any]:
        """Get activity stream data (GPS, heart rate, power, etc.)."""
        if not self.access_token:
            raise StravaAPIError(
                "No access token available. Please authenticate first.")

        if keys is None:
            keys = ["time", "distance", "latlng", "altitude",
                    "velocity_smooth", "heartrate", "cadence", "watts", "temp"]

        params = {"keys": ",".join(keys), "key_by_type": True}

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = await client.get(f"{self.base_url}/activities/{activity_id}/streams", headers=headers, params=params)

            if response.status_code == 401:
                await self._refresh_access_token()
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = await client.get(f"{self.base_url}/activities/{activity_id}/streams", headers=headers, params=params)

            if response.status_code != 200:
                raise StravaAPIError(
                    f"Failed to fetch streams for activity {activity_id}: {response.status_code} - {response.text}")

            return response.json()

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise StravaAPIError(
                "Missing refresh token or client credentials for token refresh")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post("https://www.strava.com/oauth/token", data=data)

            if response.status_code != 200:
                raise StravaAPIError(
                    f"Failed to refresh token: {response.status_code} - {response.text}")

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]

            # Update .env file with new tokens
            self._update_env_tokens()

    def _update_env_tokens(self) -> None:
        """Update .env file with new tokens."""
        env_path = ".env"
        env_vars = {}

        # Read existing .env file
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value

        # Update tokens
        env_vars["STRAVA_ACCESS_TOKEN"] = self.access_token
        env_vars["STRAVA_REFRESH_TOKEN"] = self.refresh_token

        # Write back to .env file
        with open(env_path, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")

    def get_authorization_url(self, redirect_uri: str = "http://localhost:8000/auth", scope: str = "read,activity:read_all") -> str:
        """Get the authorization URL for OAuth flow."""
        if not self.client_id:
            raise StravaAPIError("Client ID not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope
        }

        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://www.strava.com/oauth/authorize?{param_string}"

    async def exchange_code_for_token(self, code: str, redirect_uri: str = "http://localhost:8000/auth") -> Dict[str, str]:
        """Exchange authorization code for access tokens."""
        if not self.client_id or not self.client_secret:
            raise StravaAPIError("Client ID and secret must be configured")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post("https://www.strava.com/oauth/token", data=data)

            if response.status_code != 200:
                raise StravaAPIError(
                    f"Failed to exchange code for token: {response.status_code} - {response.text}")

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]

            # Update .env file with new tokens
            self._update_env_tokens()

            return token_data
