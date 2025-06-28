import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestMainSyncIntegration(unittest.TestCase):
    
    @patch('src.sync_agent.SyncAgent')
    @patch('src.main.load_dotenv')
    def test_analysis_config_instantiates_sync_agent(self, mock_load_dotenv, mock_sync_agent_class):
        """Test that AnalysisConfig properly instantiates SyncAgent"""
        mock_sync_agent_instance = MagicMock()
        mock_sync_agent_class.return_value = mock_sync_agent_instance
        
        # Import here to ensure mocks are in place
        from src.main import AnalysisConfig
        
        # The AnalysisConfig class includes SyncAgent instantiation in its body
        # This test verifies that the SyncAgent is properly created and scheduled
        mock_sync_agent_class.assert_called_once()
        mock_sync_agent_instance.schedule_weekly_sync.assert_called_once_with("example_athlete_id")
    
    @patch('src.sync_agent.SyncAgent.schedule_weekly_sync')
    @patch('src.sync_agent.SyncAgent.__init__', return_value=None)
    def test_sync_agent_integration_with_athlete_id(self, mock_init, mock_schedule):
        """Test that the sync agent is properly configured with the athlete ID"""
        # Import here to trigger the AnalysisConfig class body execution
        from src.main import AnalysisConfig
        
        # Verify the SyncAgent was initialized
        mock_init.assert_called()
        
        # Verify schedule_weekly_sync was called with the correct athlete ID
        mock_schedule.assert_called_with("example_athlete_id")


if __name__ == '__main__':
    unittest.main()