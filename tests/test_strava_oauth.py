# pylint: disable=protected-access
import unittest
import json
import time
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, mock_open, MagicMock
from http.server import HTTPServer

from src.strava_oauth import (
    AthleteToken,
    StravaOAuthConfig,
    TokenStorage,
    OAuthCallbackHandler,
    StravaOAuthClient,
    StravaAPIClient,
    DEFAULT_REDIRECT_URI,
    DEFAULT_SCOPES,
    DEFAULT_TOKEN_FILE,
    STRAVA_AUTH_URL,
    STRAVA_TOKEN_URL,
    STRAVA_API_BASE
)


class TestAthleteToken(unittest.TestCase):
    """Tests for AthleteToken dataclass."""

    def test_athlete_token_creation(self):
        """Test creating an athlete token."""
        token = AthleteToken(
            athlete_id=12345,
            athlete_name="John Doe",
            access_token="access123",
            refresh_token="refresh123",
            expires_at=int(time.time()) + 3600
        )
        self.assertEqual(token.athlete_id, 12345)
        self.assertEqual(token.athlete_name, "John Doe")
        self.assertEqual(token.access_token, "access123")
        self.assertEqual(token.token_type, "Bearer")

    def test_token_is_not_expired(self):
        """Test that a future token is not expired."""
        token = AthleteToken(
            athlete_id=1,
            athlete_name="Test",
            access_token="test",
            refresh_token="test",
            expires_at=int(time.time()) + 3600
        )
        self.assertFalse(token.is_expired())

    def test_token_is_expired(self):
        """Test that a past token is expired."""
        token = AthleteToken(
            athlete_id=1,
            athlete_name="Test",
            access_token="test",
            refresh_token="test",
            expires_at=int(time.time()) - 3600
        )
        self.assertTrue(token.is_expired())

    def test_token_expiring_within_buffer(self):
        """Test that a token expiring within 5 minutes is considered expired."""
        token = AthleteToken(
            athlete_id=1,
            athlete_name="Test",
            access_token="test",
            refresh_token="test",
            expires_at=int(time.time()) + 60  # 1 minute from now
        )
        self.assertTrue(token.is_expired())


class TestTokenStorage(unittest.TestCase):
    """Tests for TokenStorage class."""

    def setUp(self):
        # Use tempfile for cross-platform compatibility
        self.temp_fd, self.test_file = tempfile.mkstemp(suffix='.json')
        os.close(self.temp_fd)
        os.remove(self.test_file)  # Remove so we start with no file
        self.storage = TokenStorage(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_load_tokens_empty_file(self):
        """Test loading tokens when file doesn't exist."""
        tokens = self.storage.load_tokens()
        self.assertEqual(tokens, {})

    def test_save_and_load_token(self):
        """Test saving and loading a token."""
        token = AthleteToken(
            athlete_id=12345,
            athlete_name="John Doe",
            access_token="access123",
            refresh_token="refresh123",
            expires_at=int(time.time()) + 3600
        )
        self.storage.save_token(token)

        tokens = self.storage.load_tokens()
        self.assertIn(12345, tokens)
        self.assertEqual(tokens[12345].athlete_name, "John Doe")

    def test_get_token(self):
        """Test getting a specific token."""
        token = AthleteToken(
            athlete_id=12345,
            athlete_name="John Doe",
            access_token="access123",
            refresh_token="refresh123",
            expires_at=int(time.time()) + 3600
        )
        self.storage.save_token(token)

        retrieved = self.storage.get_token(12345)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.athlete_id, 12345)

        missing = self.storage.get_token(99999)
        self.assertIsNone(missing)

    def test_delete_token(self):
        """Test deleting a token."""
        token = AthleteToken(
            athlete_id=12345,
            athlete_name="John Doe",
            access_token="access123",
            refresh_token="refresh123",
            expires_at=int(time.time()) + 3600
        )
        self.storage.save_token(token)

        result = self.storage.delete_token(12345)
        self.assertTrue(result)
        self.assertIsNone(self.storage.get_token(12345))

        result = self.storage.delete_token(99999)
        self.assertFalse(result)

    def test_list_athletes(self):
        """Test listing all athletes."""
        token1 = AthleteToken(
            athlete_id=1, athlete_name="Alice",
            access_token="a", refresh_token="r", expires_at=9999999999
        )
        token2 = AthleteToken(
            athlete_id=2, athlete_name="Bob",
            access_token="b", refresh_token="r", expires_at=9999999999
        )
        self.storage.save_token(token1)
        self.storage.save_token(token2)

        athletes = self.storage.list_athletes()
        self.assertEqual(len(athletes), 2)
        self.assertEqual(athletes[1], "Alice")
        self.assertEqual(athletes[2], "Bob")

    def test_load_corrupted_json(self):
        """Test handling corrupted JSON file."""
        with open(self.test_file, 'w') as f:
            f.write("not valid json")

        tokens = self.storage.load_tokens()
        self.assertEqual(tokens, {})


class TestOAuthCallbackHandler(unittest.TestCase):
    """Tests for OAuthCallbackHandler class."""

    def setUp(self):
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None

    def test_handler_extracts_code(self):
        """Test that handler extracts authorization code."""
        handler = Mock(spec=OAuthCallbackHandler)
        handler.path = "/callback?code=test_code_123&scope=activity:read"

        # Simulate parsing
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)

        self.assertEqual(params['code'][0], 'test_code_123')

    def test_handler_handles_error(self):
        """Test that handler handles errors."""
        handler = Mock(spec=OAuthCallbackHandler)
        handler.path = "/callback?error=access_denied"

        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)

        self.assertEqual(params['error'][0], 'access_denied')


class TestStravaOAuthClient(unittest.TestCase):
    """Tests for StravaOAuthClient class."""

    def test_get_authorization_url(self):
        """Test generating authorization URL."""
        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123",
            redirect_uri="http://localhost:8089/callback",
            scopes="activity:read_all"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)
            url = client.get_authorization_url()

            self.assertIn(STRAVA_AUTH_URL, url)
            self.assertIn("client_id=12345", url)
            self.assertIn("response_type=code", url)
            self.assertIn("scope=activity%3Aread_all", url)

    def test_load_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "env_id",
            "STRAVA_CLIENT_SECRET": "env_secret"
        }):
            client = StravaOAuthClient()
            self.assertEqual(client.config.client_id, "env_id")
            self.assertEqual(client.config.client_secret, "env_secret")

    def test_missing_env_vars_raises_error(self):
        """Test that missing env vars raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                StravaOAuthClient()
            self.assertIn("STRAVA_CLIENT_ID", str(context.exception))

    @patch('src.strava_oauth.requests.post')
    def test_exchange_code_for_token(self, mock_post):
        """Test exchanging code for token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "access123",
            "refresh_token": "refresh123",
            "expires_at": int(time.time()) + 3600,
            "token_type": "Bearer",
            "athlete": {
                "id": 12345,
                "firstname": "John",
                "lastname": "Doe"
            }
        }
        mock_post.return_value = mock_response

        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)
            client.storage = Mock()
            client.storage.save_token = Mock()

            token = client._exchange_code_for_token("auth_code")

            self.assertIsNotNone(token)
            self.assertEqual(token.athlete_id, 12345)
            self.assertEqual(token.athlete_name, "John Doe")
            self.assertEqual(token.access_token, "access123")
            client.storage.save_token.assert_called_once()

    @patch('src.strava_oauth.requests.post')
    def test_refresh_token(self, mock_post):
        """Test refreshing an expired token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access123",
            "refresh_token": "new_refresh123",
            "expires_at": int(time.time()) + 3600,
            "token_type": "Bearer"
        }
        mock_post.return_value = mock_response

        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)
            old_token = AthleteToken(
                athlete_id=12345,
                athlete_name="John Doe",
                access_token="old_access",
                refresh_token="old_refresh",
                expires_at=int(time.time()) - 3600
            )
            client.storage = Mock()
            client.storage.get_token = Mock(return_value=old_token)
            client.storage.save_token = Mock()

            new_token = client.refresh_token(12345)

            self.assertIsNotNone(new_token)
            self.assertEqual(new_token.access_token, "new_access123")
            client.storage.save_token.assert_called_once()

    def test_get_valid_token_refreshes_if_expired(self):
        """Test that get_valid_token refreshes expired tokens."""
        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)

            expired_token = AthleteToken(
                athlete_id=12345,
                athlete_name="John",
                access_token="old",
                refresh_token="refresh",
                expires_at=int(time.time()) - 3600
            )
            fresh_token = AthleteToken(
                athlete_id=12345,
                athlete_name="John",
                access_token="new",
                refresh_token="refresh",
                expires_at=int(time.time()) + 3600
            )

            client.storage = Mock()
            client.storage.get_token = Mock(return_value=expired_token)
            client.refresh_token = Mock(return_value=fresh_token)

            token = client.get_valid_token(12345)

            client.refresh_token.assert_called_once_with(12345)
            self.assertEqual(token.access_token, "new")

    def test_list_athletes(self):
        """Test listing athletes."""
        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)
            client.storage = Mock()
            client.storage.list_athletes = Mock(return_value={1: "Alice", 2: "Bob"})

            athletes = client.list_athletes()

            self.assertEqual(len(athletes), 2)
            client.storage.list_athletes.assert_called_once()

    def test_remove_athlete(self):
        """Test removing an athlete."""
        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            client = StravaOAuthClient(config)
            client.storage = Mock()
            client.storage.delete_token = Mock(return_value=True)

            result = client.remove_athlete(12345)

            self.assertTrue(result)
            client.storage.delete_token.assert_called_once_with(12345)


class TestStravaAPIClient(unittest.TestCase):
    """Tests for StravaAPIClient class."""

    def setUp(self):
        config = StravaOAuthConfig(
            client_id="12345",
            client_secret="secret123"
        )
        with patch.dict(os.environ, {
            "STRAVA_CLIENT_ID": "12345",
            "STRAVA_CLIENT_SECRET": "secret123"
        }):
            self.oauth_client = StravaOAuthClient(config)
            self.api_client = StravaAPIClient(self.oauth_client)

        self.valid_token = AthleteToken(
            athlete_id=12345,
            athlete_name="John",
            access_token="valid_token",
            refresh_token="refresh",
            expires_at=int(time.time()) + 3600
        )

    @patch('src.strava_oauth.requests.get')
    def test_get_activity(self, mock_get):
        """Test getting activity details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 9876543,
            "name": "Morning Run",
            "type": "Run"
        }
        mock_get.return_value = mock_response

        self.oauth_client.get_valid_token = Mock(return_value=self.valid_token)

        activity = self.api_client.get_activity(12345, 9876543)

        self.assertIsNotNone(activity)
        self.assertEqual(activity["id"], 9876543)
        mock_get.assert_called_once()

    @patch('src.strava_oauth.requests.get')
    def test_list_activities(self, mock_get):
        """Test listing activities."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Run 1"},
            {"id": 2, "name": "Run 2"}
        ]
        mock_get.return_value = mock_response

        self.oauth_client.get_valid_token = Mock(return_value=self.valid_token)

        activities = self.api_client.list_activities(12345)

        self.assertIsNotNone(activities)
        self.assertEqual(len(activities), 2)

    def test_get_activity_no_token(self):
        """Test that get_activity returns None without valid token."""
        self.oauth_client.get_valid_token = Mock(return_value=None)

        activity = self.api_client.get_activity(12345, 9876543)

        self.assertIsNone(activity)

    def test_generate_tcx_from_streams(self):
        """Test TCX generation from stream data."""
        activity = {
            "type": "Run",
            "start_date": "2024-01-15T10:00:00Z",
            "elapsed_time": 3600,
            "distance": 10000,
            "calories": 500
        }
        streams = {
            "time": {"data": [0, 60, 120]},
            "distance": {"data": [0, 100, 200]},
            "latlng": {"data": [[40.7, -74.0], [40.71, -74.01], [40.72, -74.02]]},
            "altitude": {"data": [10, 15, 12]},
            "heartrate": {"data": [120, 140, 150]}
        }

        tcx = self.api_client._generate_tcx_from_streams(activity, streams)

        self.assertIsNotNone(tcx)
        self.assertIn('<?xml version="1.0"', tcx)
        self.assertIn('<Activity Sport="Running">', tcx)
        self.assertIn('<Trackpoint>', tcx)
        self.assertIn('<HeartRateBpm>', tcx)
        self.assertIn('<DistanceMeters>', tcx)


class TestStravaOAuthConfig(unittest.TestCase):
    """Tests for StravaOAuthConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = StravaOAuthConfig(
            client_id="test",
            client_secret="secret"
        )
        self.assertEqual(config.redirect_uri, DEFAULT_REDIRECT_URI)
        self.assertEqual(config.scopes, DEFAULT_SCOPES)
        self.assertEqual(config.token_file, DEFAULT_TOKEN_FILE)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = StravaOAuthConfig(
            client_id="test",
            client_secret="secret",
            redirect_uri="http://custom:9000/cb",
            scopes="read_all",
            token_file="custom_tokens.json"
        )
        self.assertEqual(config.redirect_uri, "http://custom:9000/cb")
        self.assertEqual(config.scopes, "read_all")
        self.assertEqual(config.token_file, "custom_tokens.json")


if __name__ == '__main__':
    unittest.main()
