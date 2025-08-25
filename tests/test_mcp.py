"""Tests for MCP server functionality."""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import sys
from pathlib import Path

# Add the src directory to Python path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server import StravaActivityMCP
from strava_client import StravaClient, StravaAPIError


class TestStravaClient(unittest.TestCase):
    """Test cases for StravaClient."""

    def setUp(self):
        self.client = StravaClient()

    @patch.dict('os.environ', {})
    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        client = StravaClient()
        self.assertIsNone(client.client_id)
        self.assertIsNone(client.access_token)

    @patch.dict('os.environ', {
        'STRAVA_CLIENT_ID': 'test_id',
        'STRAVA_ACCESS_TOKEN': 'test_token'
    })
    def test_init_with_credentials(self):
        """Test initialization with credentials."""
        client = StravaClient()
        self.assertEqual(client.client_id, 'test_id')
        self.assertEqual(client.access_token, 'test_token')

    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        self.client.client_id = "test_client_id"
        url = self.client.get_authorization_url()
        self.assertIn("client_id=test_client_id", url)
        self.assertIn("strava.com/oauth/authorize", url)

    def test_get_authorization_url_no_client_id(self):
        """Test authorization URL generation without client ID."""
        self.client.client_id = None
        with self.assertRaises(StravaAPIError):
            self.client.get_authorization_url()

    @patch('httpx.AsyncClient')
    async def test_get_activities_no_token(self, mock_client):
        """Test getting activities without access token."""
        self.client.access_token = None
        with self.assertRaises(StravaAPIError):
            await self.client.get_activities()

    @patch('httpx.AsyncClient')
    async def test_get_activities_success(self, mock_client):
        """Test successful activity retrieval."""
        self.client.access_token = "test_token"
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Test Activity", "type": "Run"}
        ]
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        activities = await self.client.get_activities(limit=1)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["name"], "Test Activity")

    @patch('httpx.AsyncClient')
    async def test_get_activities_401_error(self, mock_client):
        """Test activity retrieval with 401 error (triggers token refresh)."""
        self.client.access_token = "test_token"
        self.client.refresh_token = "refresh_token"
        self.client.client_id = "client_id"
        self.client.client_secret = "client_secret"
        
        # Mock the HTTP client for failed and successful requests
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 401
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = []
        
        mock_refresh_response = MagicMock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh"
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = [mock_response_fail, mock_response_success]
        mock_client_instance.post.return_value = mock_refresh_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        with patch.object(self.client, '_update_env_tokens'):
            activities = await self.client.get_activities()
            self.assertEqual(len(activities), 0)
            self.assertEqual(self.client.access_token, "new_token")


class TestStravaActivityMCP(unittest.TestCase):
    """Test cases for StravaActivityMCP."""

    def setUp(self):
        self.mcp_server = StravaActivityMCP()

    def test_get_available_tools(self):
        """Test getting available tools."""
        tools = self.mcp_server.get_available_tools()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        
        # Check that required tools are present
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "list_activities",
            "get_activity_detail", 
            "analyze_activity",
            "sync_recent_activities",
            "get_authorization_url",
            "authenticate_with_code"
        ]
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)

    @patch.object(StravaClient, 'get_authorization_url')
    async def test_get_authorization_url_success(self, mock_get_auth_url):
        """Test successful authorization URL generation."""
        mock_get_auth_url.return_value = "https://strava.com/oauth/authorize?..."
        
        result = await self.mcp_server.handle_tool_call("get_authorization_url", {})
        
        self.assertTrue(result["success"])
        self.assertIn("authorization_url", result)

    @patch.object(StravaClient, 'get_authorization_url')
    async def test_get_authorization_url_error(self, mock_get_auth_url):
        """Test authorization URL generation with error."""
        mock_get_auth_url.side_effect = StravaAPIError("No client ID")
        
        result = await self.mcp_server.handle_tool_call("get_authorization_url", {})
        
        self.assertIn("error", result)

    @patch.object(StravaClient, 'get_activities')
    async def test_list_activities_success(self, mock_get_activities):
        """Test successful activity listing."""
        mock_activities = [
            {
                "id": 12345,
                "name": "Morning Run",
                "type": "Run",
                "sport_type": "Run",
                "start_date": "2024-01-01T08:00:00Z",
                "distance": 5000,
                "moving_time": 1800,
                "elapsed_time": 1900,
                "average_speed": 2.78,
                "max_speed": 3.5,
                "average_heartrate": 145,
                "max_heartrate": 165
            }
        ]
        mock_get_activities.return_value = mock_activities
        
        result = await self.mcp_server.handle_tool_call("list_activities", {"limit": 1})
        
        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["activities"]), 1)
        self.assertEqual(result["activities"][0]["name"], "Morning Run")

    @patch.object(StravaClient, 'get_activities')
    async def test_list_activities_error(self, mock_get_activities):
        """Test activity listing with API error."""
        mock_get_activities.side_effect = StravaAPIError("API Error")
        
        result = await self.mcp_server.handle_tool_call("list_activities", {})
        
        self.assertIn("error", result)
        self.assertIn("Strava API error", result["error"])

    @patch.object(StravaClient, 'get_activity_detail')
    async def test_get_activity_detail_success(self, mock_get_detail):
        """Test successful activity detail retrieval."""
        mock_activity = {
            "id": 12345,
            "name": "Test Activity",
            "type": "Run",
            "start_date": "2024-01-01T08:00:00Z",
            "distance": 5000
        }
        mock_get_detail.return_value = mock_activity
        
        result = await self.mcp_server.handle_tool_call("get_activity_detail", {"activity_id": "12345"})
        
        self.assertTrue(result["success"])
        self.assertEqual(result["activity"]["name"], "Test Activity")

    async def test_unknown_tool(self):
        """Test handling of unknown tool."""
        result = await self.mcp_server.handle_tool_call("unknown_tool", {})
        
        self.assertIn("error", result)
        self.assertIn("Unknown tool", result["error"])

    def test_convert_streams_to_analysis_format(self):
        """Test stream conversion to analysis format."""
        streams = {
            "time": {"data": [0, 1, 2]},
            "distance": {"data": [0, 100, 200]},
            "velocity_smooth": {"data": [0, 5, 10]},
            "heartrate": {"data": [120, 140, 160]}
        }
        activity_detail = {"id": 12345, "elapsed_time": 3600}
        
        result = self.mcp_server._convert_streams_to_analysis_format(streams, activity_detail)
        
        self.assertEqual(result["activity_id"], 12345)
        self.assertEqual(len(result["trackpoints"]), 3)
        self.assertEqual(result["trackpoints"][0]["time"], 0)
        self.assertEqual(result["trackpoints"][1]["speed"], 5)
        self.assertEqual(result["trackpoints"][2]["hr_value"], 160)

    def test_convert_empty_streams(self):
        """Test conversion with empty streams."""
        result = self.mcp_server._convert_streams_to_analysis_format({}, {})
        
        self.assertEqual(result, {})


class TestAsyncMethods(unittest.TestCase):
    """Test async methods with proper async test setup."""

    def test_async_methods(self):
        """Test async methods using asyncio.run."""
        async def run_tests():
            mcp_server = StravaActivityMCP()
            
            # Test unknown tool
            result = await mcp_server.handle_tool_call("unknown_tool", {})
            self.assertIn("error", result)
            
            # Test get_authorization_url without credentials
            result = await mcp_server.handle_tool_call("get_authorization_url", {})
            self.assertIn("error", result)
        
        asyncio.run(run_tests())


if __name__ == '__main__':
    unittest.main()