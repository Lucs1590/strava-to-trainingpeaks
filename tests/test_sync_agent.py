import unittest
import time
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.sync_agent import SyncAgent


class TestSyncAgent(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures with mocked environment variables."""
        self.env_patcher = patch.dict('os.environ', {
            'STRAVA_API_KEY': 'test_strava_key',
            'TRAININGPEAKS_USERNAME': 'test_username',
            'TRAININGPEAKS_PASSWORD': 'test_password',
            'OPENAI_API_KEY': 'test_openai_key'
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()

    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_sync_agent_initialization(self, mock_load_dotenv, mock_chat_openai, mock_create_agent):
        """Test that SyncAgent initializes correctly with proper configuration."""
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent

        agent = SyncAgent()

        self.assertEqual(agent.strava_api_key, 'test_strava_key')
        self.assertEqual(agent.trainingpeaks_username, 'test_username')
        self.assertEqual(agent.trainingpeaks_password, 'test_password')
        self.assertEqual(agent.base_strava_url,
                         "https://www.strava.com/api/v3")
        self.assertIsNotNone(agent.logger)
        mock_load_dotenv.assert_called_once()
        mock_create_agent.assert_called_once()

    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_get_workouts_from_strava_success(self, mock_load_dotenv, mock_chat_openai, mock_create_agent, mock_get):
        """Test successful retrieval of workouts from Strava API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Morning Run", "type": "Run"},
            {"id": 2, "name": "Evening Bike", "type": "Ride"}
        ]
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        workouts = agent.get_workouts_from_strava(start_date, end_date)

        self.assertEqual(len(workouts), 2)
        self.assertEqual(workouts[0]["name"], "Morning Run")
        self.assertEqual(workouts[1]["name"], "Evening Bike")

        # Verify API call was made with correct parameters
        expected_url = f"{agent.base_strava_url}/athlete/activities"
        expected_headers = {"Authorization": f"Bearer {agent.strava_api_key}"}
        expected_params = {
            "before": int(end_date.timestamp()),
            "after": int(start_date.timestamp()),
            "per_page": 200
        }
        mock_get.assert_called_once_with(
            expected_url, headers=expected_headers, params=expected_params)

    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_get_workouts_from_strava_error(self, mock_load_dotenv, mock_chat_openai, mock_create_agent, mock_get):
        """Test error handling when Strava API returns an error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        workouts = agent.get_workouts_from_strava(start_date, end_date)

        self.assertEqual(len(workouts), 0)

    @patch('src.sync_agent.webdriver.Chrome')
    @patch('src.sync_agent.ChromeService')
    @patch('src.sync_agent.ChromeDriverManager')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_push_workouts_to_trainingpeaks(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                            mock_driver_manager, mock_service, mock_chrome):
        """Test pushing workouts to TrainingPeaks via Selenium."""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element

        agent = SyncAgent()
        workouts = [
            {"id": 1, "tcx_file_path": "path/to/workout1.tcx"},
            {"id": 2, "tcx_file_path": "path/to/workout2.tcx"}
        ]

        agent.push_workouts_to_trainingpeaks(workouts)

        # Verify WebDriver operations
        mock_driver.get.assert_any_call("https://home.trainingpeaks.com/login")
        mock_driver.get.assert_any_call(
            "https://app.trainingpeaks.com/#calendar")
        self.assertTrue(mock_driver.find_element.called)
        mock_driver.quit.assert_called_once()

    @patch('src.sync_agent.SyncAgent.get_workouts_from_strava')
    @patch('src.sync_agent.SyncAgent.push_workouts_to_trainingpeaks')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_sync_workouts_for_week_with_workouts(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                                  mock_push, mock_get):
        """Test weekly sync when workouts are available."""
        mock_workouts = [{"id": 1, "name": "Test Workout"}]
        mock_get.return_value = mock_workouts

        agent = SyncAgent()
        agent.sync_workouts_for_week()

        mock_get.assert_called_once()
        mock_push.assert_called_once_with(mock_workouts)

    @patch('src.sync_agent.SyncAgent.get_workouts_from_strava')
    @patch('src.sync_agent.SyncAgent.push_workouts_to_trainingpeaks')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_sync_workouts_for_week_no_workouts(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                                mock_push, mock_get):
        """Test weekly sync when no workouts are available."""
        mock_get.return_value = []

        agent = SyncAgent()
        agent.sync_workouts_for_week()

        mock_get.assert_called_once()
        mock_push.assert_not_called()

    @patch('src.sync_agent.time.sleep')
    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_handle_api_rate_limits_success_on_retry(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                                     mock_get, mock_sleep):
        """Test rate limit handling with successful retry."""
        # First call fails, second succeeds
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [{"id": 1}]

        mock_get.side_effect = [
            Exception("Rate limit exceeded"),
            mock_response_success
        ]

        agent = SyncAgent()

        def mock_func():
            return agent.get_workouts_from_strava(datetime.now(), datetime.now())

        result = agent.handle_api_rate_limits(mock_func)

        self.assertIsNotNone(result)
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1

    @patch('src.sync_agent.time.sleep')
    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_handle_api_rate_limits_max_retries_exceeded(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                                         mock_get, mock_sleep):
        """Test rate limit handling when max retries are exceeded."""
        mock_get.side_effect = Exception("Persistent error")

        agent = SyncAgent()

        def mock_func():
            return agent.get_workouts_from_strava(datetime.now(), datetime.now())

        result = agent.handle_api_rate_limits(mock_func)

        self.assertIsNone(result)
        # Should have slept 4 times: 2^0, 2^1, 2^2, 2^3
        expected_calls = [unittest.mock.call(1), unittest.mock.call(
            2), unittest.mock.call(4), unittest.mock.call(8)]
        mock_sleep.assert_has_calls(expected_calls)

    @patch('src.sync_agent.time.sleep')
    @patch('src.sync_agent.schedule.run_pending')
    @patch('src.sync_agent.schedule.every')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_schedule_weekly_sync(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                  mock_every, mock_run_pending, mock_sleep):
        """Test scheduling of weekly sync with early termination."""
        mock_week = MagicMock()
        mock_every.return_value.week = mock_week

        # Mock sleep to break the infinite loop after a few iterations
        mock_sleep.side_effect = [None, None, KeyboardInterrupt()]

        agent = SyncAgent()

        with self.assertRaises(KeyboardInterrupt):
            agent.schedule_weekly_sync()

        mock_every.assert_called_once()
        mock_week.do.assert_called_once_with(agent.sync_workouts_for_week)
        self.assertTrue(mock_run_pending.called)

    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_sync_agent_initialization_missing_env_vars(self, mock_load_dotenv, mock_chat_openai, mock_create_agent):
        """Test SyncAgent initialization with missing environment variables."""
        with patch.dict('os.environ', {}, clear=True):
            agent = SyncAgent()

            self.assertIsNone(agent.strava_api_key)
            self.assertIsNone(agent.trainingpeaks_username)
            self.assertIsNone(agent.trainingpeaks_password)

    @patch('src.sync_agent.webdriver.Chrome')
    @patch('src.sync_agent.ChromeService')
    @patch('src.sync_agent.ChromeDriverManager')
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    @patch('src.sync_agent.load_dotenv')
    def test_push_workouts_to_trainingpeaks_empty_list(self, mock_load_dotenv, mock_chat_openai, mock_create_agent,
                                                       mock_driver_manager, mock_service, mock_chrome):
        """Test pushing empty workout list to TrainingPeaks."""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        agent = SyncAgent()
        workouts = [{"id": 1, "tcx_file_path": "path/to/file.tcx"}]
        agent.push_workouts_to_trainingpeaks(workouts)

        self.assertTrue(mock_driver.get.called)
        self.assertTrue(mock_driver.find_element.called)

    @patch('src.sync_agent.requests.get')
    def test_handle_api_rate_limits(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Workout 1"}]
        mock_get.return_value = mock_response

        agent = SyncAgent()
        result = agent.handle_api_rate_limits(
            agent.get_workouts_from_strava, "athlete_id", datetime.now(), datetime.now())

        self.assertIsNotNone(result)
        self.assertEqual(result[0]["name"], "Workout 1")


if __name__ == '__main__':
    unittest.main()
