# pylint: disable=protected-access
import unittest
import os
import tempfile
from unittest.mock import patch, Mock

from src.coach_sync import (
    CoachSyncManager,
    coach_mode_main,
    setup_logging
)
from src.strava_oauth import AthleteToken


class TestCoachSyncManager(unittest.TestCase):
    """Tests for CoachSyncManager class."""

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    def test_manager_initialization_with_oauth(self):
        """Test manager initialization with OAuth configured."""
        manager = CoachSyncManager()
        self.assertIsNotNone(manager.oauth_client)
        self.assertIsNotNone(manager.api_client)

    @patch.dict(os.environ, {}, clear=True)
    def test_manager_initialization_without_oauth(self):
        """Test manager initialization without OAuth configured."""
        manager = CoachSyncManager()
        self.assertIsNone(manager.oauth_client)
        self.assertIsNone(manager.api_client)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    def test_list_athletes_empty(self):
        """Test listing athletes when none registered."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(return_value={})

        with patch('builtins.print') as mock_print:
            manager._list_athletes()
            mock_print.assert_any_call("\n📋 No athletes registered yet.")

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    def test_list_athletes_with_data(self):
        """Test listing athletes with registered athletes."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(return_value={
            1: "Alice",
            2: "Bob"
        })

        valid_token = AthleteToken(
            athlete_id=1,
            athlete_name="Alice",
            access_token="token",
            refresh_token="refresh",
            expires_at=9999999999
        )
        expired_token = AthleteToken(
            athlete_id=2,
            athlete_name="Bob",
            access_token="token",
            refresh_token="refresh",
            expires_at=0
        )

        def mock_get_token(athlete_id):
            if athlete_id == 1:
                return valid_token
            return expired_token

        manager.oauth_client.storage = Mock()
        manager.oauth_client.storage.get_token = mock_get_token

        with patch('builtins.print') as mock_print:
            manager._list_athletes()
            mock_print.assert_any_call("\n📋 Registered Athletes:")

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    def test_select_athlete_no_athletes(self):
        """Test selecting athlete when none registered."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(return_value={})

        with patch('builtins.print'):
            result = manager._select_athlete()
            self.assertIsNone(result)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    def test_select_athlete_cancel(self, mock_select):
        """Test selecting athlete and cancelling."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(return_value={1: "Alice"})

        mock_select.return_value.ask.return_value = "Cancel"

        result = manager._select_athlete()
        self.assertIsNone(result)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    def test_select_athlete_success(self, mock_select):
        """Test successfully selecting an athlete."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"

        result = manager._select_athlete()
        self.assertEqual(result, 12345)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.confirm')
    def test_add_athlete_cancel(self, mock_confirm):
        """Test cancelling athlete addition."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()

        mock_confirm.return_value.ask.return_value = False

        with patch('builtins.print'):
            manager._add_athlete()
            manager.oauth_client.authorize_athlete.assert_not_called()

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.confirm')
    def test_add_athlete_success(self, mock_confirm):
        """Test successfully adding an athlete."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()

        mock_token = AthleteToken(
            athlete_id=12345,
            athlete_name="John Doe",
            access_token="token",
            refresh_token="refresh",
            expires_at=9999999999
        )
        manager.oauth_client.authorize_athlete = Mock(return_value=mock_token)
        mock_confirm.return_value.ask.return_value = True

        with patch('builtins.print') as mock_print:
            manager._add_athlete()
            manager.oauth_client.authorize_athlete.assert_called_once()
            success_calls = [
                call for call in mock_print.call_args_list
                if "Successfully added athlete" in str(call)
            ]
            self.assertEqual(len(success_calls), 1)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.confirm')
    def test_add_athlete_failure(self, mock_confirm):
        """Test failed athlete addition."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.authorize_athlete = Mock(return_value=None)
        mock_confirm.return_value.ask.return_value = True

        with patch('builtins.print') as mock_print:
            manager._add_athlete()
            failure_calls = [
                call for call in mock_print.call_args_list
                if "Failed to add athlete" in str(call)
            ]
            self.assertEqual(len(failure_calls), 1)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    @patch('src.coach_sync.questionary.confirm')
    def test_remove_athlete_confirm(self, mock_confirm, mock_select):
        """Test confirming athlete removal."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})
        manager.oauth_client.remove_athlete = Mock(return_value=True)

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"
        mock_confirm.return_value.ask.return_value = True

        with patch('builtins.print'):
            manager._remove_athlete()
            manager.oauth_client.remove_athlete.assert_called_once_with(12345)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    @patch('src.coach_sync.questionary.confirm')
    def test_remove_athlete_cancel(self, mock_confirm, mock_select):
        """Test cancelling athlete removal."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"
        mock_confirm.return_value.ask.return_value = False

        manager._remove_athlete()
        manager.oauth_client.remove_athlete.assert_not_called()

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    @patch('src.coach_sync.questionary.text')
    @patch('src.coach_sync.questionary.confirm')
    def test_sync_activity_success(self, mock_confirm, mock_text, mock_select):
        """Test successfully syncing an activity."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})
        manager.api_client = Mock()
        with tempfile.NamedTemporaryFile(
            prefix="activity_",
            suffix=".tcx",
            delete=False
        ) as tmpfile:
            tmpfile_path = tmpfile.name
        manager.api_client.download_tcx = Mock(return_value=tmpfile_path)

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"
        mock_text.return_value.ask.return_value = "987654321"
        mock_confirm.return_value.ask.return_value = False

        with patch('builtins.print'):
            manager._sync_activity()
            manager.api_client.download_tcx.assert_called_once()

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    @patch('src.coach_sync.questionary.text')
    def test_sync_activity_invalid_id(self, mock_text, mock_select):
        """Test syncing activity with invalid ID."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"
        mock_text.return_value.ask.return_value = "not_a_number"

        with patch('builtins.print') as mock_print:
            manager._sync_activity()
            error_calls = [
                call for call in mock_print.call_args_list
                if "Invalid activity ID" in str(call)
            ]
            self.assertEqual(len(error_calls), 1)

    @patch.dict(os.environ, {
        "STRAVA_CLIENT_ID": "test_id",
        "STRAVA_CLIENT_SECRET": "test_secret"
    })
    @patch('src.coach_sync.questionary.select')
    def test_list_activities(self, mock_select):
        """Test listing athlete activities."""
        manager = CoachSyncManager()
        manager.oauth_client = Mock()
        manager.oauth_client.list_athletes = Mock(
            return_value={12345: "Alice"})
        manager.api_client = Mock()
        manager.api_client.list_activities = Mock(return_value=[
            {
                "id": 1,
                "name": "Morning Run",
                "type": "Run",
                "distance": 5000,
                "start_date_local": "2024-01-15T10:00:00Z"
            }
        ])

        mock_select.return_value.ask.return_value = "Alice (ID: 12345)"

        with patch('builtins.print'):
            manager._list_activities()
            manager.api_client.list_activities.assert_called_once_with(
                12345,
                per_page=10
            )


class TestCoachModeMain(unittest.TestCase):
    """Tests for coach_mode_main function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_coach_mode_main_no_config(self):
        """Test coach mode main without OAuth config."""
        with patch('builtins.print') as mock_print:
            coach_mode_main()
            warning_calls = [
                call for call in mock_print.call_args_list
                if "not configured" in str(call)
            ]
            self.assertGreaterEqual(len(warning_calls), 1)


class TestSetupLogging(unittest.TestCase):
    """Tests for setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger."""
        logger = setup_logging()
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "src.coach_sync")


if __name__ == '__main__':
    unittest.main()
