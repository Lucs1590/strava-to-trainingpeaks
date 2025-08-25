"""Tests for TrainingPeaks integration."""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import sys
from pathlib import Path

# Add the src directory to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trainingpeaks_client import TrainingPeaksClient, TrainingPeaksAPIError
from mcp_server import StravaActivityMCP


class TestTrainingPeaksClient(unittest.TestCase):
    """Test cases for TrainingPeaksClient."""

    def setUp(self):
        self.client = TrainingPeaksClient()

    @patch.dict('os.environ', {})
    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        client = TrainingPeaksClient()
        self.assertIsNone(client.access_token)
        self.assertIsNone(client.api_key)
        self.assertIsNone(client.username)
        self.assertIsNone(client.password)

    @patch.dict('os.environ', {
        'TRAININGPEAKS_ACCESS_TOKEN': 'test_token',
        'TRAININGPEAKS_API_KEY': 'test_key'
    })
    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        client = TrainingPeaksClient()
        self.assertEqual(client.access_token, 'test_token')
        self.assertEqual(client.api_key, 'test_key')

    def test_check_authentication_no_credentials(self):
        """Test authentication check without credentials."""
        self.assertFalse(self.client._check_authentication())

    @patch.dict('os.environ', {'TRAININGPEAKS_ACCESS_TOKEN': 'test_token'})
    def test_check_authentication_with_token(self):
        """Test authentication check with access token."""
        client = TrainingPeaksClient()
        self.assertTrue(client._check_authentication())

    def test_get_auth_info_no_credentials(self):
        """Test getting auth info without credentials."""
        auth_info = self.client.get_auth_info()
        self.assertFalse(auth_info['authenticated'])
        self.assertEqual(auth_info['auth_methods'], [])
        self.assertIn('TRAININGPEAKS_ACCESS_TOKEN', auth_info['required_env_vars'][0])

    @patch.dict('os.environ', {'TRAININGPEAKS_ACCESS_TOKEN': 'test_token'})
    def test_get_auth_info_with_token(self):
        """Test getting auth info with access token."""
        client = TrainingPeaksClient()
        auth_info = client.get_auth_info()
        self.assertTrue(auth_info['authenticated'])
        self.assertIn('OAuth Bearer Token', auth_info['auth_methods'])

    async def test_get_athlete_info_no_auth(self):
        """Test getting athlete info without authentication."""
        with self.assertRaises(TrainingPeaksAPIError):
            await self.client.get_athlete_info()

    async def test_get_workouts_no_auth(self):
        """Test getting workouts without authentication."""
        with self.assertRaises(TrainingPeaksAPIError):
            await self.client.get_workouts()

    def test_convert_strava_to_trainingpeaks(self):
        """Test conversion of Strava activity to TrainingPeaks format."""
        strava_activity = {
            "id": 12345,
            "name": "Morning Run",
            "type": "Run",
            "start_date": "2024-01-01T08:00:00Z",
            "distance": 5000,  # meters
            "moving_time": 1800,  # seconds
            "average_heartrate": 145,
            "average_speed": 2.78,  # m/s
            "description": "Great run!"
        }
        
        result = self.client._convert_strava_to_trainingpeaks(strava_activity)
        
        self.assertEqual(result["title"], "Morning Run")
        self.assertEqual(result["sport"], "run")
        self.assertEqual(result["distance"], 5.0)  # converted to km
        self.assertEqual(result["duration"], 1800)
        self.assertEqual(result["avgHeartRate"], 145)
        self.assertEqual(result["avgSpeed"], 10.008)  # converted to km/h
        self.assertEqual(result["source"], "Strava")
        self.assertEqual(result["externalId"], "12345")


class TestTrainingPeaksMCP(unittest.TestCase):
    """Test cases for TrainingPeaks MCP integration."""

    def setUp(self):
        self.mcp_server = StravaActivityMCP()

    def test_trainingpeaks_tools_in_available_tools(self):
        """Test that TrainingPeaks tools are included in available tools."""
        tools = self.mcp_server.get_available_tools()
        tool_names = [tool["name"] for tool in tools]
        
        # Check that TrainingPeaks tools are present
        expected_tp_tools = [
            "get_trainingpeaks_auth_info",
            "get_trainingpeaks_athlete",
            "list_trainingpeaks_workouts",
            "get_trainingpeaks_workout_detail",
            "upload_workout_to_trainingpeaks",
            "sync_strava_to_trainingpeaks",
            "bulk_sync_strava_to_trainingpeaks",
            "get_training_plans",
            "get_planned_workouts",
            "get_training_metrics"
        ]
        
        for tool_name in expected_tp_tools:
            self.assertIn(tool_name, tool_names, f"Tool {tool_name} not found in available tools")

    async def test_get_trainingpeaks_auth_info(self):
        """Test getting TrainingPeaks auth info."""
        result = await self.mcp_server.handle_tool_call("get_trainingpeaks_auth_info", {})
        
        self.assertTrue(result["success"])
        self.assertIn("auth_info", result)
        auth_info = result["auth_info"]
        self.assertIn("authenticated", auth_info)
        self.assertIn("auth_methods", auth_info)
        self.assertIn("required_env_vars", auth_info)

    async def test_get_trainingpeaks_athlete_no_auth(self):
        """Test getting TrainingPeaks athlete without authentication."""
        result = await self.mcp_server.handle_tool_call("get_trainingpeaks_athlete", {})
        
        self.assertIn("error", result)
        self.assertIn("Authentication required", result["error"])

    async def test_list_trainingpeaks_workouts_no_auth(self):
        """Test listing TrainingPeaks workouts without authentication."""
        result = await self.mcp_server.handle_tool_call("list_trainingpeaks_workouts", {
            "days_back": 30,
            "limit": 10
        })
        
        self.assertIn("error", result)
        self.assertIn("Authentication required", result["error"])

    @patch('src.strava_client.StravaClient.get_activity_detail')
    @patch('src.trainingpeaks_client.TrainingPeaksClient.sync_from_strava')
    async def test_sync_strava_to_trainingpeaks_success(self, mock_sync, mock_get_activity):
        """Test successful sync from Strava to TrainingPeaks."""
        # Mock Strava activity
        mock_activity = {
            "id": 12345,
            "name": "Test Run",
            "type": "Run",
            "start_date": "2024-01-01T08:00:00Z",
            "distance": 5000
        }
        mock_get_activity.return_value = mock_activity
        
        # Mock sync result
        mock_sync.return_value = {
            "success": True,
            "strava_activity_id": 12345,
            "trainingpeaks_result": {"status": "uploaded"}
        }
        
        result = await self.mcp_server.handle_tool_call("sync_strava_to_trainingpeaks", {
            "activity_id": "12345",
            "include_tcx": False
        })
        
        self.assertTrue(result["success"])
        self.assertEqual(result["activity_id"], "12345")
        self.assertIn("sync_result", result)


class TestAsyncTrainingPeaksMethods(unittest.TestCase):
    """Test async TrainingPeaks methods with proper async test setup."""

    def test_async_trainingpeaks_methods(self):
        """Test async TrainingPeaks methods using asyncio.run."""
        async def run_tests():
            mcp_server = StravaActivityMCP()
            
            # Test TrainingPeaks auth info
            result = await mcp_server.handle_tool_call("get_trainingpeaks_auth_info", {})
            self.assertTrue(result["success"])
            
            # Test without authentication 
            result = await mcp_server.handle_tool_call("get_trainingpeaks_athlete", {})
            self.assertIn("error", result)
        
        asyncio.run(run_tests())


if __name__ == '__main__':
    unittest.main()