"""TrainingPeaks API client for workout and training plan management."""

import os
import json
import base64
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv


class TrainingPeaksAPIError(Exception):
    """Exception raised for TrainingPeaks API errors."""
    pass


class TrainingPeaksClient:
    """Client for interacting with TrainingPeaks API."""

    def __init__(self):
        """Initialize TrainingPeaks client with credentials from environment."""
        load_dotenv()

        self.base_url = "https://api.trainingpeaks.com"
        self.username = os.getenv("TRAININGPEAKS_USERNAME")
        self.password = os.getenv("TRAININGPEAKS_PASSWORD")
        self.api_key = os.getenv("TRAININGPEAKS_API_KEY")
        self.client_id = os.getenv("TRAININGPEAKS_CLIENT_ID")
        self.client_secret = os.getenv("TRAININGPEAKS_CLIENT_SECRET")
        self.access_token = os.getenv("TRAININGPEAKS_ACCESS_TOKEN")

        self.logger = logging.getLogger(__name__)

        # Session for connection pooling
        self._session = None

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None:
            headers = {
                "User-Agent": "strava-to-trainingpeaks-mcp/1.0",
                "Content-Type": "application/json"
            }

            # Add authentication headers
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            elif self.api_key:
                headers["X-API-Key"] = self.api_key
            elif self.username and self.password:
                # Basic auth for legacy API
                credentials = base64.b64encode(
                    f"{self.username}:{self.password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0
            )

        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to TrainingPeaks API."""
        session = await self._get_session()

        try:
            response = await session.request(method, endpoint, **kwargs)

            if response.status_code == 401:
                raise TrainingPeaksAPIError(
                    "Authentication failed. Check your credentials.")
            elif response.status_code == 403:
                raise TrainingPeaksAPIError(
                    "Access forbidden. Check your permissions.")
            elif response.status_code == 429:
                raise TrainingPeaksAPIError(
                    "Rate limit exceeded. Please try again later.")
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get(
                        "message", f"HTTP {response.status_code}")
                except:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                raise TrainingPeaksAPIError(error_message)

            return response.json() if response.content else {}

        except httpx.RequestError as e:
            raise TrainingPeaksAPIError(f"Request failed: {str(e)}")

    async def get_athlete_info(self) -> Dict[str, Any]:
        """Get athlete information."""
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("GET", "/v1/athlete")

    async def get_workouts(self, start_date: datetime = None, end_date: datetime = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get workouts from TrainingPeaks.

        Args:
            start_date: Start date for workout search
            end_date: End date for workout search  
            limit: Maximum number of workouts to return

        Returns:
            List of workout data
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "limit": limit
        }

        return await self._make_request("GET", "/v1/workouts", params=params)

    async def get_workout_detail(self, workout_id: str) -> Dict[str, Any]:
        """Get detailed workout information.

        Args:
            workout_id: TrainingPeaks workout ID

        Returns:
            Detailed workout data
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("GET", f"/v1/workouts/{workout_id}")

    async def upload_workout(self, workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a workout to TrainingPeaks.

        Args:
            workout_data: Workout data in TrainingPeaks format

        Returns:
            Upload result
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("POST", "/v1/workouts", json=workout_data)

    async def upload_tcx_file(self, tcx_content: str, workout_title: str = None) -> Dict[str, Any]:
        """Upload a TCX file to TrainingPeaks.

        Args:
            tcx_content: TCX file content as string
            workout_title: Optional title for the workout

        Returns:
            Upload result
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        # Prepare the file upload
        files = {
            "file": ("workout.tcx", tcx_content, "application/tcx+xml")
        }

        data = {}
        if workout_title:
            data["title"] = workout_title

        # For file upload, we need different headers
        session = await self._get_session()
        headers = session.headers.copy()
        if "Content-Type" in headers:
            del headers["Content-Type"]  # Let httpx set multipart headers

        try:
            response = await session.post("/v1/workouts/upload", files=files, data=data)

            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get(
                        "message", f"Upload failed with status {response.status_code}")
                except:
                    error_message = f"Upload failed with status {response.status_code}"
                raise TrainingPeaksAPIError(error_message)

            return response.json() if response.content else {"status": "uploaded"}

        except httpx.RequestError as e:
            raise TrainingPeaksAPIError(f"Upload request failed: {str(e)}")

    async def get_training_plans(self) -> List[Dict[str, Any]]:
        """Get training plans for the athlete.

        Returns:
            List of training plans
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("GET", "/v1/plans")

    async def get_training_plan_detail(self, plan_id: str) -> Dict[str, Any]:
        """Get detailed training plan information.

        Args:
            plan_id: Training plan ID

        Returns:
            Detailed training plan data
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("GET", f"/v1/plans/{plan_id}")

    async def get_planned_workouts(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get planned workouts from training plans.

        Args:
            start_date: Start date for planned workouts
            end_date: End date for planned workouts

        Returns:
            List of planned workouts
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        if start_date is None:
            start_date = datetime.now()
        if end_date is None:
            end_date = datetime.now() + timedelta(days=30)

        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }

        return await self._make_request("GET", "/v1/planned-workouts", params=params)

    async def create_planned_workout(self, workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a planned workout in TrainingPeaks.

        Args:
            workout_data: Planned workout data

        Returns:
            Created workout data
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        return await self._make_request("POST", "/v1/planned-workouts", json=workout_data)

    async def get_metrics(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get training metrics and analytics.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            Training metrics data
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d")
        }

        return await self._make_request("GET", "/v1/metrics", params=params)

    def _check_authentication(self) -> bool:
        """Check if authentication credentials are available."""
        return bool(
            self.access_token or
            self.api_key or
            (self.username and self.password)
        )

    def get_auth_info(self) -> Dict[str, Any]:
        """Get authentication status and required credentials."""
        auth_methods = []

        if self.access_token:
            auth_methods.append("OAuth Bearer Token")
        if self.api_key:
            auth_methods.append("API Key")
        if self.username and self.password:
            auth_methods.append("Basic Authentication")

        return {
            "authenticated": self._check_authentication(),
            "auth_methods": auth_methods,
            "required_env_vars": [
                "TRAININGPEAKS_ACCESS_TOKEN (preferred)",
                "TRAININGPEAKS_API_KEY (alternative)",
                "TRAININGPEAKS_USERNAME + TRAININGPEAKS_PASSWORD (legacy)"
            ]
        }

    async def sync_from_strava(self, strava_activity: Dict[str, Any], tcx_content: str = None) -> Dict[str, Any]:
        """Sync an activity from Strava to TrainingPeaks.

        Args:
            strava_activity: Strava activity data
            tcx_content: Optional TCX content for the activity

        Returns:
            Sync result
        """
        if not self._check_authentication():
            raise TrainingPeaksAPIError("Authentication required")

        try:
            # If we have TCX content, upload the file
            if tcx_content:
                result = await self.upload_tcx_file(
                    tcx_content,
                    workout_title=strava_activity.get(
                        "name", "Imported from Strava")
                )
            else:
                # Convert Strava activity to TrainingPeaks format
                workout_data = self._convert_strava_to_trainingpeaks(
                    strava_activity)
                result = await self.upload_workout(workout_data)

            return {
                "success": True,
                "strava_activity_id": strava_activity.get("id"),
                "trainingpeaks_result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "strava_activity_id": strava_activity.get("id")
            }

    def _convert_strava_to_trainingpeaks(self, strava_activity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Strava activity data to TrainingPeaks format.

        Args:
            strava_activity: Strava activity data

        Returns:
            TrainingPeaks workout data
        """
        # Map Strava activity types to TrainingPeaks workout types
        sport_mapping = {
            "Run": "run",
            "Ride": "bike",
            "Swim": "swim",
            "Hike": "run",
            "Walk": "run",
            "VirtualRide": "bike",
            "EBikeRide": "bike",
            "Workout": "strength"
        }

        workout_data = {
            "title": strava_activity.get("name", "Imported from Strava"),
            "workoutDate": strava_activity.get("start_date", datetime.now().isoformat()),
            "sport": sport_mapping.get(strava_activity.get("type"), "other"),
            # Convert to km
            "distance": strava_activity.get("distance", 0) / 1000,
            "duration": strava_activity.get("moving_time", 0),  # In seconds
            "description": strava_activity.get("description", ""),
            "source": "Strava",
            "externalId": str(strava_activity.get("id")),
        }

        # Add optional metrics if available
        if strava_activity.get("average_heartrate"):
            workout_data["avgHeartRate"] = strava_activity["average_heartrate"]
        if strava_activity.get("max_heartrate"):
            workout_data["maxHeartRate"] = strava_activity["max_heartrate"]
        if strava_activity.get("average_watts"):
            workout_data["avgPower"] = strava_activity["average_watts"]
        if strava_activity.get("weighted_average_watts"):
            workout_data["normalizedPower"] = strava_activity["weighted_average_watts"]
        if strava_activity.get("kilojoules"):
            # Convert to joules
            workout_data["energy"] = strava_activity["kilojoules"] * 1000
        if strava_activity.get("average_speed"):
            # Convert to km/h
            workout_data["avgSpeed"] = strava_activity["average_speed"] * 3.6
        if strava_activity.get("max_speed"):
            # Convert to km/h
            workout_data["maxSpeed"] = strava_activity["max_speed"] * 3.6

        return workout_data
