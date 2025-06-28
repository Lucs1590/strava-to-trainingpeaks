import unittest
import os
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open

from src.sync_agent import SyncAgent


class TestSyncAgent(unittest.TestCase):

    @patch.dict(os.environ, {
        'STRAVA_API_KEY': 'test_strava_key',
        'TRAININGPEAKS_USERNAME': 'test_username',
        'TRAININGPEAKS_PASSWORD': 'test_password',
        'OPENAI_API_KEY': 'test_openai_key'
    })
    @patch('src.sync_agent.create_openai_functions_agent')
    @patch('src.sync_agent.ChatOpenAI')
    def test_sync_agent_initialization(self, mock_chat_openai, mock_create_agent):
        """Test that SyncAgent initializes correctly with environment variables."""
        mock_chat_openai.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()
        
        agent = SyncAgent()
        
        self.assertEqual(agent.strava_api_key, 'test_strava_key')
        self.assertEqual(agent.trainingpeaks_username, 'test_username')
        self.assertEqual(agent.trainingpeaks_password, 'test_password')
        self.assertEqual(agent.base_strava_url, "https://www.strava.com/api/v3")
        self.assertIsNotNone(agent.logger)
        self.assertTrue(mock_create_agent.called)

    @patch('src.sync_agent.requests.get')
    @patch.dict(os.environ, {'STRAVA_API_KEY': 'test_key'})
    def test_get_workouts_from_strava_success(self, mock_get):
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
        
        workouts = agent.get_workouts_from_strava("athlete_123", start_date, end_date)

        self.assertEqual(len(workouts), 2)
        self.assertEqual(workouts[0]["name"], "Morning Run")
        self.assertEqual(workouts[1]["name"], "Evening Bike")
        
        # Verify API call was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("Authorization", call_args[1]["headers"])
        self.assertEqual(call_args[1]["headers"]["Authorization"], "Bearer test_key")

    @patch('src.sync_agent.requests.get')
    @patch.dict(os.environ, {'STRAVA_API_KEY': 'test_key'})
    def test_get_workouts_from_strava_error(self, mock_get):
        """Test error handling when Strava API returns error status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        workouts = agent.get_workouts_from_strava("athlete_123", start_date, end_date)

        self.assertEqual(len(workouts), 0)

    @patch('src.sync_agent.webdriver.Chrome')
    @patch('src.sync_agent.ChromeService')
    @patch('src.sync_agent.ChromeDriverManager')
    @patch('src.sync_agent.time.sleep')
    @patch.dict(os.environ, {
        'TRAININGPEAKS_USERNAME': 'test_user',
        'TRAININGPEAKS_PASSWORD': 'test_pass'
    })
    def test_push_workouts_to_trainingpeaks(self, mock_sleep, mock_driver_manager, 
                                          mock_service, mock_chrome):
        """Test pushing workouts to TrainingPeaks using Selenium."""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_element = MagicMock()
        mock_driver.find_element.return_value = mock_element
        
        agent = SyncAgent()
        workouts = [
            {"id": 1, "tcx_file_path": "/path/to/workout1.tcx"},
            {"id": 2, "tcx_file_path": "/path/to/workout2.tcx"}
        ]
        
        agent.push_workouts_to_trainingpeaks(workouts)
        
        # Verify driver interactions
        self.assertTrue(mock_driver.get.called)
        self.assertTrue(mock_driver.find_element.called)
        self.assertTrue(mock_driver.quit.called)
        
        # Verify login process
        mock_element.send_keys.assert_any_call('test_user')
        mock_element.send_keys.assert_any_call('test_pass')

    @patch('src.sync_agent.SyncAgent.get_workouts_from_strava')
    @patch('src.sync_agent.SyncAgent.push_workouts_to_trainingpeaks')
    def test_sync_workouts_for_week_with_workouts(self, mock_push, mock_get):
        """Test weekly sync when workouts are available."""
        mock_get.return_value = [
            {"id": 1, "name": "Test Workout", "tcx_file_path": "/path/to/test.tcx"}
        ]
        
        agent = SyncAgent()
        agent.sync_workouts_for_week("athlete_123")
        
        mock_get.assert_called_once()
        mock_push.assert_called_once()
        
        # Verify date range calculation
        call_args = mock_get.call_args[0]
        self.assertEqual(call_args[0], "athlete_123")  # athlete_id
        # Verify the date range is approximately 7 days
        start_date, end_date = call_args[1], call_args[2]
        self.assertAlmostEqual((end_date - start_date).days, 7, delta=1)

    @patch('src.sync_agent.SyncAgent.get_workouts_from_strava')
    @patch('src.sync_agent.SyncAgent.push_workouts_to_trainingpeaks')
    def test_sync_workouts_for_week_no_workouts(self, mock_push, mock_get):
        """Test weekly sync when no workouts are available."""
        mock_get.return_value = []
        
        agent = SyncAgent()
        agent.sync_workouts_for_week("athlete_123")
        
        mock_get.assert_called_once()
        mock_push.assert_not_called()

    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.time.sleep')
    def test_handle_api_rate_limits_success_on_first_try(self, mock_sleep, mock_get):
        """Test rate limit handling when request succeeds on first try."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Test Workout"}]
        mock_get.return_value = mock_response
        
        agent = SyncAgent()
        result = agent.handle_api_rate_limits(
            agent.get_workouts_from_strava, 
            "athlete_123", 
            datetime.now(), 
            datetime.now()
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        mock_sleep.assert_not_called()

    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.time.sleep')
    def test_handle_api_rate_limits_max_retries_exceeded(self, mock_sleep, mock_get):
        """Test rate limit handling when max retries are exceeded."""
        mock_get.side_effect = Exception("API Error")
        
        agent = SyncAgent()
        result = agent.handle_api_rate_limits(
            agent.get_workouts_from_strava,
            "athlete_123",
            datetime.now(),
            datetime.now()
        )
        
        self.assertIsNone(result)
        self.assertEqual(mock_sleep.call_count, 4)  # 5 attempts - 1 = 4 sleeps

    @patch('src.sync_agent.schedule.every')
    @patch('src.sync_agent.schedule.run_pending')
    @patch('src.sync_agent.time.sleep')
    def test_schedule_weekly_sync(self, mock_sleep, mock_run_pending, mock_every):
        """Test scheduling of weekly sync (limited iterations to avoid infinite loop)."""
        mock_week = MagicMock()
        mock_every.return_value.week = mock_week
        
        # Mock sleep to break the infinite loop after a few iterations
        mock_sleep.side_effect = [None, None, KeyboardInterrupt()]
        
        agent = SyncAgent()
        
        with self.assertRaises(KeyboardInterrupt):
            agent.schedule_weekly_sync("athlete_123")
        
        mock_week.do.assert_called_once()
        self.assertTrue(mock_run_pending.called)
        self.assertTrue(mock_sleep.called)


if __name__ == '__main__':
    unittest.main()