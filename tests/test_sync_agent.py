import unittest
import os
import time
import logging

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call

import requests
from src.sync_agent import SyncAgent


class TestSyncAgent(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_env_vars = {
            'STRAVA_API_KEY': 'test_strava_key',
            'TRAININGPEAKS_USERNAME': 'test_username',
            'TRAININGPEAKS_PASSWORD': 'test_password',
            'OPENAI_API_KEY': 'test_openai_key'
        }

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    def test_init_with_all_env_vars(self, mock_chat_openai, mock_create_agent, mock_file_handler, mock_getenv):
        """Test SyncAgent initialization with all environment variables present."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        agent = SyncAgent()

        self.assertEqual(agent.strava_api_key, 'test_strava_key')
        self.assertEqual(agent.trainingpeaks_username, 'test_username')
        self.assertEqual(agent.trainingpeaks_password, 'test_password')
        self.assertEqual(agent.openai_api_key, 'test_openai_key')
        self.assertEqual(agent.strava_base_url,
                         "https://www.strava.com/api/v3")
        self.assertIsNotNone(agent.langchain_agent)
        mock_create_agent.assert_called_once()

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    def test_init_without_openai_key(self, mock_file_handler, mock_getenv):
        """Test SyncAgent initialization without OpenAI API key."""
        env_vars = self.test_env_vars.copy()
        env_vars['OPENAI_API_KEY'] = None
        mock_getenv.side_effect = lambda key: env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        agent = SyncAgent()

        self.assertIsNone(agent.langchain_agent)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.create_openai_functions_agent')
    def test_init_langchain_agent_exception(self, mock_create_agent, mock_file_handler, mock_getenv):
        """Test SyncAgent initialization when LangChain agent creation fails."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler
        mock_create_agent.side_effect = Exception(
            "LangChain initialization failed")

        agent = SyncAgent()

        self.assertIsNone(agent.langchain_agent)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.requests.get')
    def test_get_workouts_from_strava_success(self, mock_get, mock_file_handler, mock_getenv):
        """Test successful retrieval of workouts from Strava API."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Morning Run", "type": "Run"},
            {"id": 2, "name": "Evening Bike", "type": "Ride"}
        ]
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)
        workouts = agent.get_workouts_from_strava(
            "athlete_123", start_date, end_date)

        self.assertEqual(len(workouts), 2)
        self.assertEqual(workouts[0]["name"], "Morning Run")
        self.assertEqual(workouts[1]["name"], "Evening Bike")

        expected_url = "https://www.strava.com/api/v3/athlete/athlete_123/activities"
        expected_params = {
            "after": int(start_date.timestamp()),
            "before": int(end_date.timestamp()),
        }
        mock_get.assert_called_once_with(expected_url, params=expected_params)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.requests.get')
    def test_get_workouts_from_strava_error(self, mock_get, mock_file_handler, mock_getenv):
        """Test error handling when Strava API returns non-200 status."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)
        workouts = agent.get_workouts_from_strava(
            "athlete_123", start_date, end_date)

        self.assertEqual(len(workouts), 0)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.webdriver.Chrome')
    @patch('src.sync_agent.ChromeDriverManager')
    @patch('src.sync_agent.time.sleep')
    def test_push_workouts_to_trainingpeaks(self, mock_sleep, mock_driver_manager, mock_chrome, mock_file_handler, mock_getenv):
        """Test pushing workouts to TrainingPeaks using Selenium."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_driver_manager.return_value.install.return_value = "/path/to/chromedriver"

        # Mock DOM elements
        mock_username_element = MagicMock()
        mock_password_element = MagicMock()
        mock_login_button = MagicMock()
        mock_upload_element = MagicMock()

        mock_driver.find_element.side_effect = [
            mock_username_element,  # username field
            mock_password_element,  # password field
            mock_login_button,      # login button
            mock_upload_element,    # upload button (first workout)
            mock_upload_element     # upload button (second workout)
        ]

        agent = SyncAgent()
        workouts = [
            {"id": 1, "tcx_file_path": "/path/to/workout1.tcx"},
            {"id": 2, "tcx_file_path": "/path/to/workout2.tcx"}
        ]
        agent.push_workouts_to_trainingpeaks(workouts)

        # Verify login process
        mock_username_element.send_keys.assert_called_once_with(
            'test_username')
        mock_password_element.send_keys.assert_called_once_with(
            'test_password')
        mock_login_button.click.assert_called_once()

        # Verify upload process for each workout
        expected_upload_calls = [
            call("/path/to/workout1.tcx"),
            call("/path/to/workout2.tcx")
        ]
        mock_upload_element.send_keys.assert_has_calls(expected_upload_calls)

        # Verify driver cleanup
        mock_driver.quit.assert_called_once()

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.datetime')
    def test_sync_workouts_for_week(self, mock_datetime, mock_file_handler, mock_getenv):
        """Test weekly workout synchronization."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        # Mock datetime.now()
        mock_now = datetime(2023, 1, 8, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(
            *args, **kwargs)

        agent = SyncAgent()

        # Mock the methods that sync_workouts_for_week calls
        with patch.object(agent, 'get_workouts_from_strava') as mock_get_workouts, \
                patch.object(agent, 'push_workouts_to_trainingpeaks') as mock_push_workouts:

            mock_workouts = [{"id": 1, "name": "Test Workout"}]
            mock_get_workouts.return_value = mock_workouts

            agent.sync_workouts_for_week("athlete_123")

            expected_start_date = mock_now - timedelta(days=7)
            expected_end_date = mock_now

            mock_get_workouts.assert_called_once_with(
                "athlete_123", expected_start_date, expected_end_date)
            mock_push_workouts.assert_called_once_with(mock_workouts)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.time.sleep')
    def test_handle_api_rate_limits_success(self, mock_sleep, mock_file_handler, mock_getenv):
        """Test successful API call with rate limit handling."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        agent = SyncAgent()

        # Mock function that succeeds on first try
        mock_func = MagicMock(return_value="success")

        result = agent.handle_api_rate_limits(
            mock_func, "arg1", kwarg1="value1")

        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        mock_sleep.assert_not_called()

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.time.sleep')
    def test_handle_api_rate_limits_retry_then_success(self, mock_sleep, mock_file_handler, mock_getenv):
        """Test API call that fails initially but succeeds on retry."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        agent = SyncAgent()

        # Mock function that fails twice, then succeeds
        mock_func = MagicMock(side_effect=[
            requests.exceptions.RequestException("Rate limited"),
            requests.exceptions.RequestException("Still rate limited"),
            "success"
        ])

        result = agent.handle_api_rate_limits(mock_func, "arg1")

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        # Called after first two failures
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.time.sleep')
    def test_handle_api_rate_limits_max_retries_exceeded(self, mock_sleep, mock_file_handler, mock_getenv):
        """Test API call that fails and exceeds maximum retries."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        agent = SyncAgent()

        # Mock function that always fails
        mock_func = MagicMock(
            side_effect=requests.exceptions.RequestException("Always fails"))

        result = agent.handle_api_rate_limits(mock_func, "arg1")

        self.assertIsNone(result)
        self.assertEqual(mock_func.call_count, 5)  # max_retries = 5
        # Called after first 4 failures
        self.assertEqual(mock_sleep.call_count, 4)

    @patch('src.sync_agent.os.getenv')
    @patch('src.sync_agent.logging.FileHandler')
    @patch('src.sync_agent.schedule.every')
    @patch('src.sync_agent.schedule.run_pending')
    @patch('src.sync_agent.time.sleep')
    def test_schedule_weekly_sync(self, mock_sleep, mock_run_pending, mock_every, mock_file_handler, mock_getenv):
        """Test scheduling of weekly synchronization."""
        mock_getenv.side_effect = lambda key: self.test_env_vars.get(key)
        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        # Mock the schedule chain
        mock_schedule_job = MagicMock()
        mock_week = MagicMock()
        mock_week.do.return_value = mock_schedule_job
        mock_every.return_value.week = mock_week

        # Mock to break the infinite loop after 2 iterations
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        agent = SyncAgent()

        with self.assertRaises(KeyboardInterrupt):
            agent.schedule_weekly_sync("athlete_123")

        # Verify scheduling setup
        mock_every.assert_called_once()
        mock_week.do.assert_called_once_with(
            agent.sync_workouts_for_week, "athlete_123")

        # Verify the loop ran
        self.assertEqual(mock_run_pending.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()
