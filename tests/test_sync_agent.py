import unittest
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
        workouts = agent.get_workouts_from_strava("athlete_id", "start_date", "end_date")

        self.assertEqual(len(workouts), 1)
        self.assertEqual(workouts[0]["name"], "Workout 1")

    @patch('src.sync_agent.requests.post')
    def test_push_workouts_to_trainingpeaks(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        agent = SyncAgent()
        workouts = [{"id": 1, "name": "Workout 1"}]
        agent.push_workouts_to_trainingpeaks(workouts)

        self.assertEqual(mock_post.call_count, 1)

    @patch('src.sync_agent.requests.get')
    @patch('src.sync_agent.requests.post')
    def test_sync_workouts_for_week(self, mock_post, mock_get):
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = [{"id": 1, "name": "Workout 1"}]
        mock_get.return_value = mock_get_response

        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post.return_value = mock_post_response

        agent = SyncAgent()
        agent.sync_workouts_for_week("athlete_id")

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_post.call_count, 1)

    @patch('src.sync_agent.requests.get')
    def test_handle_api_rate_limits(self, mock_get):
        mock_get.side_effect = [requests.exceptions.RequestException("Error"), MagicMock(status_code=200, json=lambda: [{"id": 1, "name": "Workout 1"}])]

        agent = SyncAgent()
        result = agent.handle_api_rate_limits(agent.get_workouts_from_strava, "athlete_id", "start_date", "end_date")

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Workout 1")

    @patch('src.sync_agent.schedule.every')
    def test_schedule_weekly_sync(self, mock_every):
        mock_job = MagicMock()
        mock_every.return_value.week.do.return_value = mock_job

        agent = SyncAgent()
        agent.schedule_weekly_sync("athlete_id")

        self.assertTrue(mock_every.called)
        self.assertTrue(mock_every.return_value.week.do.called)

if __name__ == '__main__':
    unittest.main()
