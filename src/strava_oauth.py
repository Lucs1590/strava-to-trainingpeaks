"""
Strava OAuth 2.0 client for runner-side authorization.

This module implements the OAuth 2.0 Authorization Code flow for Strava,
allowing coaches to manage multiple athletes' tokens and sync their activities.
"""

import json
import logging
import os
import time
import webbrowser
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Optional, Dict
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv


# Strava API endpoints
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"

# Default configuration
DEFAULT_REDIRECT_URI = "http://localhost:8089/callback"
DEFAULT_SCOPES = "activity:read_all"
DEFAULT_TOKEN_FILE = ".strava_tokens.json"


def setup_logging() -> logging.Logger:
    """Setup logging for the OAuth module."""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
        handler = logging.FileHandler('strava_oauth.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


@dataclass
class AthleteToken:
    """Represents an athlete's OAuth tokens."""
    athlete_id: int
    athlete_name: str
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = "Bearer"
    scopes: str = DEFAULT_SCOPES

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        # Add a 5-minute buffer
        return time.time() >= (self.expires_at - 300)


@dataclass
class StravaOAuthConfig:
    """Configuration for Strava OAuth."""
    client_id: str
    client_secret: str
    redirect_uri: str = DEFAULT_REDIRECT_URI
    scopes: str = DEFAULT_SCOPES
    token_file: str = DEFAULT_TOKEN_FILE


class TokenStorage:
    """Handles secure storage and retrieval of athlete tokens."""

    def __init__(self, token_file: str = DEFAULT_TOKEN_FILE):
        self.token_file = Path(token_file)
        self.logger = setup_logging()

    def load_tokens(self) -> Dict[int, AthleteToken]:
        """Load all athlete tokens from storage."""
        if not self.token_file.exists():
            return {}

        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tokens = {}
                for athlete_id_str, token_data in data.items():
                    tokens[int(athlete_id_str)] = AthleteToken(**token_data)
                return tokens
        except (json.JSONDecodeError, KeyError) as err:
            self.logger.error("Failed to load tokens: %s", str(err))
            return {}

    def save_token(self, token: AthleteToken) -> None:
        """Save an athlete token to storage."""
        tokens = self.load_tokens()
        tokens[token.athlete_id] = token
        self._write_tokens(tokens)
        self.logger.info(
            "Saved token for athlete %s (ID: %d)",
            token.athlete_name, token.athlete_id
        )

    def get_token(self, athlete_id: int) -> Optional[AthleteToken]:
        """Get a specific athlete's token."""
        tokens = self.load_tokens()
        return tokens.get(athlete_id)

    def delete_token(self, athlete_id: int) -> bool:
        """Delete an athlete's token."""
        tokens = self.load_tokens()
        if athlete_id in tokens:
            del tokens[athlete_id]
            self._write_tokens(tokens)
            self.logger.info("Deleted token for athlete ID: %d", athlete_id)
            return True
        return False

    def list_athletes(self) -> Dict[int, str]:
        """List all registered athletes."""
        tokens = self.load_tokens()
        return {
            athlete_id: token.athlete_name
            for athlete_id, token in tokens.items()
        }

    def _write_tokens(self, tokens: Dict[int, AthleteToken]) -> None:
        """Write tokens to storage file."""
        data = {
            str(athlete_id): asdict(token)
            for athlete_id, token in tokens.items()
        }
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    authorization_code: Optional[str] = None
    error: Optional[str] = None

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass

    def do_GET(self):
        """Handle GET request for OAuth callback."""
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)

            if 'code' in params:
                OAuthCallbackHandler.authorization_code = params['code'][0]
                self._send_success_response()
            elif 'error' in params:
                OAuthCallbackHandler.error = params.get(
                    'error', ['unknown'])[0]
                self._send_error_response()
            else:
                self._send_error_response()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_success_response(self):
        """Send success response to browser."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Successful</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #FC4C02;">✓ Authorization Successful!</h1>
            <p>You have successfully authorized the Strava to TrainingPeaks app.</p>
            <p>You can close this window and return to the application.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self):
        """Send error response to browser."""
        self.send_response(400)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Authorization Failed</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #D32F2F;">✗ Authorization Failed</h1>
            <p>There was an error during authorization.</p>
            <p>Please try again or contact support.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())


class StravaOAuthClient:
    """Strava OAuth 2.0 client for managing athlete authorization."""

    def __init__(self, config: Optional[StravaOAuthConfig] = None):
        load_dotenv()
        self.logger = setup_logging()

        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()

        self.storage = TokenStorage(self.config.token_file)

    def _load_config_from_env(self) -> StravaOAuthConfig:
        """Load OAuth configuration from environment variables."""
        client_id = os.getenv("STRAVA_CLIENT_ID")
        client_secret = os.getenv("STRAVA_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError(
                "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables are required. "
                "Please see docs/coach_mode.md for setup instructions."
            )

        return StravaOAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=os.getenv("STRAVA_REDIRECT_URI",
                                   DEFAULT_REDIRECT_URI),
            scopes=os.getenv("STRAVA_SCOPES", DEFAULT_SCOPES),
            token_file=os.getenv("STRAVA_TOKEN_FILE", DEFAULT_TOKEN_FILE)
        )

    def get_authorization_url(self) -> str:
        """Generate the Strava authorization URL."""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": self.config.scopes,
            "approval_prompt": "auto"
        }
        return f"{STRAVA_AUTH_URL}?{urlencode(params)}"

    def authorize_athlete(self, timeout: int = 120) -> Optional[AthleteToken]:
        """
        Start the OAuth flow to authorize a new athlete.

        Opens a browser for the user to authorize and waits for the callback.

        Args:
            timeout: Maximum time to wait for authorization in seconds.

        Returns:
            AthleteToken if successful, None otherwise.
        """
        # Reset handler state
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None

        # Parse port from redirect URI
        parsed = urlparse(self.config.redirect_uri)
        port = parsed.port or 8089

        # Start callback server
        server = HTTPServer(('localhost', port), OAuthCallbackHandler)
        server.timeout = timeout

        server_thread = Thread(target=self._run_server, args=(server, timeout))
        server_thread.daemon = True
        server_thread.start()

        # Open browser for authorization
        auth_url = self.get_authorization_url()
        self.logger.info("Opening browser for Strava authorization...")
        self.logger.info("Authorization URL: %s", auth_url)

        try:
            webbrowser.open(auth_url)
        except Exception as err:
            self.logger.warning(
                "Could not open browser automatically. "
                "Please manually navigate to: %s", auth_url
            )

        print(f"\nPlease authorize the application in your browser.")
        print(f"If the browser doesn't open, visit: {auth_url}")
        print(f"Waiting for authorization (timeout: {timeout}s)...\n")

        # Wait for callback
        server_thread.join(timeout=timeout + 5)
        server.shutdown()

        if OAuthCallbackHandler.authorization_code:
            return self._exchange_code_for_token(
                OAuthCallbackHandler.authorization_code
            )
        elif OAuthCallbackHandler.error:
            self.logger.error(
                "Authorization failed: %s", OAuthCallbackHandler.error
            )
        else:
            self.logger.error("Authorization timed out")

        return None

    def _run_server(self, server: HTTPServer, timeout: int) -> None:
        """Run the OAuth callback server."""
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            server.handle_request()
            if OAuthCallbackHandler.authorization_code or OAuthCallbackHandler.error:
                break

    def _exchange_code_for_token(self, code: str) -> Optional[AthleteToken]:
        """Exchange authorization code for access token."""
        try:
            response = requests.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code"
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            athlete = data.get("athlete", {})
            token = AthleteToken(
                athlete_id=athlete.get("id"),
                athlete_name=f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip(
                ),
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=data["expires_at"],
                token_type=data.get("token_type", "Bearer"),
                scopes=self.config.scopes
            )

            self.storage.save_token(token)
            self.logger.info(
                "Successfully authorized athlete: %s (ID: %d)",
                token.athlete_name, token.athlete_id
            )
            return token

        except requests.RequestException as err:
            self.logger.error(
                "Failed to exchange code for token: %s", str(err))
            return None

    def refresh_token(self, athlete_id: int) -> Optional[AthleteToken]:
        """Refresh an expired access token."""
        token = self.storage.get_token(athlete_id)
        if not token:
            self.logger.error("No token found for athlete ID: %d", athlete_id)
            return None

        try:
            response = requests.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            updated_token = AthleteToken(
                athlete_id=token.athlete_id,
                athlete_name=token.athlete_name,
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", token.refresh_token),
                expires_at=data["expires_at"],
                token_type=data.get("token_type", "Bearer"),
                scopes=token.scopes
            )

            self.storage.save_token(updated_token)
            self.logger.info(
                "Refreshed token for athlete: %s (ID: %d)",
                updated_token.athlete_name, updated_token.athlete_id
            )
            return updated_token

        except requests.RequestException as err:
            self.logger.error(
                "Failed to refresh token for athlete %d: %s",
                athlete_id, str(err)
            )
            return None

    def get_valid_token(self, athlete_id: int) -> Optional[AthleteToken]:
        """Get a valid (non-expired) token for an athlete, refreshing if needed."""
        token = self.storage.get_token(athlete_id)
        if not token:
            return None

        if token.is_expired():
            self.logger.info(
                "Token expired for athlete %d, refreshing...",
                athlete_id
            )
            token = self.refresh_token(athlete_id)

        return token

    def list_athletes(self) -> Dict[int, str]:
        """List all registered athletes."""
        return self.storage.list_athletes()

    def remove_athlete(self, athlete_id: int) -> bool:
        """Remove an athlete's authorization."""
        return self.storage.delete_token(athlete_id)


class StravaAPIClient:
    """Client for making authenticated Strava API requests."""

    def __init__(self, oauth_client: StravaOAuthClient):
        self.oauth_client = oauth_client
        self.logger = setup_logging()

    def _get_headers(self, token: AthleteToken) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"{token.token_type} {token.access_token}"
        }

    def get_activity(self, athlete_id: int, activity_id: int) -> Optional[dict]:
        """Get activity details."""
        token = self.oauth_client.get_valid_token(athlete_id)
        if not token:
            self.logger.error("No valid token for athlete %d", athlete_id)
            return None

        try:
            response = requests.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}",
                headers=self._get_headers(token),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as err:
            self.logger.error("Failed to get activity: %s", str(err))
            return None

    def list_activities(
        self, athlete_id: int, page: int = 1, per_page: int = 30
    ) -> Optional[list]:
        """List athlete's recent activities."""
        token = self.oauth_client.get_valid_token(athlete_id)
        if not token:
            self.logger.error("No valid token for athlete %d", athlete_id)
            return None

        try:
            response = requests.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers=self._get_headers(token),
                params={"page": page, "per_page": per_page},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as err:
            self.logger.error("Failed to list activities: %s", str(err))
            return None

    def download_tcx(
        self, athlete_id: int, activity_id: int, output_path: str
    ) -> Optional[str]:
        """
        Download activity as TCX file.

        Note: Strava API doesn't directly provide TCX export.
        This uses the web export endpoint which requires the user to be logged in.
        For API-based export, consider using the streams endpoint to build TCX.
        """
        token = self.oauth_client.get_valid_token(athlete_id)
        if not token:
            self.logger.error("No valid token for athlete %d", athlete_id)
            return None

        # Get activity details to determine sport type
        activity = self.get_activity(athlete_id, activity_id)
        if not activity:
            return None

        # Use streams endpoint for data export
        try:
            response = requests.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
                headers=self._get_headers(token),
                params={
                    "keys": "time,distance,latlng,altitude,heartrate,cadence,watts,temp",
                    "key_by_type": "true"
                },
                timeout=30
            )
            response.raise_for_status()
            streams = response.json()

            # Generate TCX from streams
            tcx_content = self._generate_tcx_from_streams(activity, streams)
            if tcx_content:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(tcx_content)
                self.logger.info("Downloaded TCX to: %s", output_path)
                return output_path

        except requests.RequestException as err:
            self.logger.error("Failed to download activity data: %s", str(err))

        return None

    def _generate_tcx_from_streams(
        self, activity: dict, streams: dict
    ) -> Optional[str]:
        """Generate TCX content from Strava streams data."""
        sport_mapping = {
            "Run": "Running",
            "Ride": "Biking",
            "Swim": "Other",
            "Walk": "Running",
            "Hike": "Running",
            "VirtualRide": "Biking",
            "VirtualRun": "Running"
        }

        activity_type = activity.get("type", "Other")
        sport = sport_mapping.get(activity_type, "Other")

        start_time_str = activity.get(
            "start_date", datetime.now(timezone.utc).isoformat())
        try:
            start_time = datetime.fromisoformat(
                start_time_str.replace('Z', '+00:00'))
        except ValueError:
            start_time = datetime.now(timezone.utc)

        # Build trackpoints
        trackpoints = []
        time_stream = streams.get("time", {}).get("data", [])
        distance_stream = streams.get("distance", {}).get("data", [])
        latlng_stream = streams.get("latlng", {}).get("data", [])
        altitude_stream = streams.get("altitude", {}).get("data", [])
        heartrate_stream = streams.get("heartrate", {}).get("data", [])
        cadence_stream = streams.get("cadence", {}).get("data", [])

        for i, elapsed in enumerate(time_stream):
            point_time = start_time + timedelta(seconds=elapsed)
            tp = f'        <Trackpoint>\n'
            tp += f'          <Time>{point_time.strftime("%Y-%m-%dT%H:%M:%SZ")}</Time>\n'

            if i < len(latlng_stream) and latlng_stream[i]:
                lat, lng = latlng_stream[i]
                tp += f'          <Position>\n'
                tp += f'            <LatitudeDegrees>{lat}</LatitudeDegrees>\n'
                tp += f'            <LongitudeDegrees>{lng}</LongitudeDegrees>\n'
                tp += f'          </Position>\n'

            if i < len(altitude_stream):
                tp += f'          <AltitudeMeters>{altitude_stream[i]}</AltitudeMeters>\n'

            if i < len(distance_stream):
                tp += f'          <DistanceMeters>{distance_stream[i]}</DistanceMeters>\n'

            if i < len(heartrate_stream):
                tp += f'          <HeartRateBpm>\n'
                tp += f'            <Value>{heartrate_stream[i]}</Value>\n'
                tp += f'          </HeartRateBpm>\n'

            if i < len(cadence_stream):
                tp += f'          <Cadence>{cadence_stream[i]}</Cadence>\n'

            tp += f'        </Trackpoint>\n'
            trackpoints.append(tp)

        # Build TCX structure
        tcx = f'''<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">
  <Activities>
    <Activity Sport="{sport}">
      <Id>{start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}</Id>
      <Lap StartTime="{start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}">
        <TotalTimeSeconds>{activity.get("elapsed_time", 0)}</TotalTimeSeconds>
        <DistanceMeters>{activity.get("distance", 0)}</DistanceMeters>
        <Calories>{activity.get("calories", 0)}</Calories>
        <Track>
{"".join(trackpoints)}        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>'''

        return tcx
