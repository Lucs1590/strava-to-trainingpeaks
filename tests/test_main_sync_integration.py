import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestMainSyncIntegration(unittest.TestCase):
    
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
    
    @patch('src.sync_agent.SyncAgent.schedule_weekly_sync')
    @patch('src.sync_agent.SyncAgent.__init__', return_value=None)
    @patch('src.main.load_dotenv')
    def test_tcx_processor_run_instantiates_sync_agent(self, mock_load_dotenv, mock_sync_agent_init, mock_schedule):
        """Test that TCXProcessor.run() properly instantiates and uses SyncAgent."""
        # Import here to ensure mocks are in place
        from src.main import TCXProcessor
        
        processor = TCXProcessor()
        
        # Mock the other dependencies of the run method
        with patch.object(processor, '_get_sport_selection', return_value=None), \
             patch.object(processor, '_get_tcx_file_path', return_value=None), \
             patch.object(processor.logger, 'error'):
            
            try:
                processor.run()
            except Exception:
                # Expected to fail due to None values, but we want to test SyncAgent instantiation
                pass
        
        # Verify the SyncAgent was initialized and scheduled
        mock_sync_agent_init.assert_called_once()
        mock_schedule.assert_called_once()

    @patch('src.sync_agent.SyncAgent.schedule_weekly_sync')
    @patch('src.sync_agent.SyncAgent.__init__', return_value=None)
    @patch('src.main.load_dotenv')
    def test_tcx_processor_run_sync_agent_called_after_success(self, mock_load_dotenv, mock_sync_agent_init, mock_schedule):
        """Test that SyncAgent is called after successful TCX processing."""
        from src.main import TCXProcessor, Sport
        
        processor = TCXProcessor()
        
        # Mock all dependencies to simulate successful processing
        with patch.object(processor, '_get_sport_selection', return_value=Sport.RUN), \
             patch.object(processor, '_get_tcx_file_path', return_value='test.tcx'), \
             patch.object(processor, '_process_by_sport') as mock_process, \
             patch.object(processor.logger, 'info'):
            
            mock_process.return_value = None  # Simulate successful processing
            
            processor.run()
        
        # Verify the SyncAgent was initialized and scheduled after successful processing
        mock_sync_agent_init.assert_called_once()
        mock_schedule.assert_called_once()

    @patch('src.sync_agent.SyncAgent')
    def test_sync_agent_import_and_instantiation(self, mock_sync_agent_class):
        """Test that SyncAgent can be properly imported and instantiated."""
        mock_sync_agent_instance = MagicMock()
        mock_sync_agent_class.return_value = mock_sync_agent_instance
        
        # Import and test the integration
        from src.sync_agent import SyncAgent
        
        agent = SyncAgent()
        
        mock_sync_agent_class.assert_called_once()
        self.assertEqual(agent, mock_sync_agent_instance)


if __name__ == '__main__':
    unittest.main()