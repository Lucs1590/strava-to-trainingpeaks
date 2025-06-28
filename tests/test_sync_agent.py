import unittest

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.sync_agent import SyncAgent


class TestSyncAgent(unittest.TestCase):

    @patch('src.sync_agent.requests.get')
    def test_get_workouts_from_strava(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Workout 1"}]
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        workouts = agent.get_workouts_from_strava(
            "athlete_id", start_date, end_date)

        self.assertEqual(len(workouts), 1)
        self.assertEqual(workouts[0]["name"], "Workout 1")

    @patch('src.sync_agent.requests.get')
    def test_get_workouts_from_strava_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        agent = SyncAgent()
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        workouts = agent.get_workouts_from_strava(
            "athlete_id", start_date, end_date)

        self.assertEqual(len(workouts), 0)

    @patch('src.sync_agent.webdriver.Chrome')
    def test_push_workouts_to_trainingpeaks(self, mock_chrome):
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
