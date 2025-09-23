# pylint: disable=protected-access
import os
import unittest

from pathlib import Path
from unittest.mock import patch

import numpy as np
from pandas import DataFrame
from tcxreader.tcxreader import TCXReader

from src import main as main_module
from src.main import (
    TrackpointProcessor, ProcessingConfig, TCXProcessor
)


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        tcx_reader = TCXReader()
        self.running_example_data = tcx_reader.read("assets/run.tcx")
        self.biking_example_data = tcx_reader.read("assets/bike.tcx")

    def test_trackpoint_processor_create_dataframe(self):
        tcx_data = self.running_example_data
        processor = TrackpointProcessor(ProcessingConfig())
        df = processor._create_dataframe(tcx_data)
        self.assertIsInstance(df, DataFrame)
        self.assertIn("Distance_Km", df.columns)
        self.assertIn("Time", df.columns)

    def test_trackpoint_processor_clean_and_transform(self):
        tcx_data = self.running_example_data
        processor = TrackpointProcessor(ProcessingConfig())
        df = processor._create_dataframe(tcx_data)
        df_clean = processor._clean_and_transform(df)
        self.assertIn("Pace", df_clean.columns)
        self.assertFalse(df_clean.isnull().any().any())

    def test_trackpoint_processor_remove_sparse_columns(self):
        processor = TrackpointProcessor(ProcessingConfig())
        df = DataFrame({
            "cadence": [None, None, None, 1, 2, 3],
            "hr_value": [None, None, None, None, None, None],
            "latitude": [1, 2, 3, 4, 5, 6],
            "longitude": [1, 2, 3, 4, 5, 6],
            "Speed_Kmh": [10, 11, 12, 13, 14, 15],
            "Distance_Km": [1, 2, 3, 4, 5, 6],
            "Time": [1, 2, 3, 4, 5, 6]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertNotIn("hr_value", df2.columns)

    def test_trackpoint_processor_reduce_data_size(self):
        processor = TrackpointProcessor(ProcessingConfig())
        df = DataFrame({
            "Speed_Kmh": np.random.rand(1200),
            "Distance_Km": np.arange(1200),
            "Time": np.arange(1200)
        })
        reduced_df = processor._reduce_data_size(df)
        self.assertLess(len(reduced_df), len(df))

    def test_trackpoint_processor_format_time_column(self):
        processor = TrackpointProcessor(ProcessingConfig())
        df = DataFrame({
            "Time": [1_600_000_000, 1_600_000_100],
            "Speed_Kmh": [10, 12],
            "Distance_Km": [1, 2]
        })
        formatted_df = processor._format_time_column(df)
        self.assertRegex(
            formatted_df["Time"].iloc[0], r"\d{2}:\d{2}:\d{2}")

    def test_tcx_processor_get_analysis_prompt_template(self):
        processor = TCXProcessor()
        prompt_no_plan = processor._get_analysis_prompt_template(False)
        self.assertIn(
            "you are an expert ai",
            prompt_no_plan.lower()
        )
        prompt_with_plan = processor._get_analysis_prompt_template(True)
        self.assertIn(
            "training plan execution analysis",
            prompt_with_plan.lower()
        )

    def test_tcx_processor_validate_tcx_file_empty(self):
        processor = TCXProcessor()
        with patch.object(processor, "_read_xml_file", return_value=""):
            valid, data = processor._validate_tcx_file("fake.tcx")
            self.assertFalse(valid)
            self.assertIsNone(data)

    def test_tcx_processor_validate_tcx_file_invalid(self):
        processor = TCXProcessor()
        with patch.object(processor, "_read_xml_file", return_value="<invalid></invalid>"), \
                patch("src.main.TCXReader.read", side_effect=Exception("bad file")):
            valid, data = processor._validate_tcx_file("fake.tcx")
            self.assertFalse(valid)
            self.assertIsNone(data)

    def test_tcx_processor_should_perform_ai_analysis(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            self.assertTrue(processor._should_perform_ai_analysis())
            mock_confirm.return_value.ask.return_value = False
            self.assertFalse(processor._should_perform_ai_analysis())

    def test_tcx_processor_format_swim_tcx(self):
        processor = TCXProcessor()
        xml = '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"><Activity Sport="Swim"><Value>123.0</Value></Activity></TrainingCenterDatabase>'
        with patch.object(processor, "_read_xml_file", return_value=xml), \
                patch.object(processor, "_write_xml_file") as mock_write:
            processor._format_swim_tcx("fake.tcx")
            args = mock_write.call_args[0][1]
            self.assertIn("xsi:schemaLocation", args)
            self.assertIn('<Activity Sport="Other">', args)
            self.assertIn("<Value>123</Value>", args)

    def test_main_invokes_processor_run(self):
        with patch.object(main_module, "TCXProcessor") as mock_processor_cls:
            mock_instance = mock_processor_cls.return_value
            main_module.main()
            mock_processor_cls.assert_called_once()
            mock_instance.run.assert_called_once()

    def test_tcx_processor_run_success(self):
        processor = TCXProcessor()
        with patch.object(processor, "_get_sport_selection", return_value=main_module.Sport.BIKE), \
                patch.object(processor, "_get_tcx_file_path", return_value="fake.tcx"), \
                patch.object(processor, "_process_by_sport") as mock_process, \
                patch.object(processor, "_format_xml_file") as mock_format, \
                patch.object(processor.logger, "info") as mock_info:
            processor.run()
            mock_process.assert_called_once_with("fake.tcx")
            mock_format.assert_called_once_with("fake.tcx")
            self.assertIn(
                ("Process completed successfully!",),
                [call.args for call in mock_info.call_args_list]
            )

    def test_tcx_processor_run_no_file_path(self):
        processor = TCXProcessor()
        with patch.object(processor, "_get_sport_selection", return_value=main_module.Sport.BIKE), \
                patch.object(processor, "_get_tcx_file_path", return_value=None), \
                patch.object(processor.logger, "error") as mock_error:
            processor.run()
            mock_error.assert_any_call("No valid file path provided")

    def test_tcx_processor_run_exception(self):
        processor = TCXProcessor()
        with patch.object(processor, "_get_sport_selection", side_effect=Exception("fail")), \
                patch.object(processor.logger, "error") as mock_error:
            with self.assertRaises(Exception) as context:
                processor.run()
            self.assertIn(
                "An error occurred during processing", str(context.exception))
            mock_error.assert_any_call("Process failed: %s", "fail")

    def test_tcx_processor_get_sport_selection(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "Run"
            sport = processor._get_sport_selection()
            self.assertEqual(sport, main_module.Sport.RUN)

            mock_select.return_value.ask.return_value = "Bike"
            sport = processor._get_sport_selection()
            self.assertEqual(sport, main_module.Sport.BIKE)

            mock_select.return_value.ask.return_value = "Swim"
            sport = processor._get_sport_selection()
            self.assertEqual(sport, main_module.Sport.SWIM)

            mock_select.return_value.ask.return_value = "Other"
            sport = processor._get_sport_selection()
            self.assertEqual(sport, main_module.Sport.OTHER)

    def test_tcx_processor_get_tcx_file_path_download(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.select') as mock_select, \
                patch.object(processor, "_handle_download_flow", return_value="downloaded.tcx") as mock_download:
            mock_select.return_value.ask.return_value = "Download"
            result = processor._get_tcx_file_path()
            mock_download.assert_called_once()
            self.assertEqual(result, "downloaded.tcx")

    def test_tcx_processor_get_tcx_file_path_provide_path(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.select') as mock_select, \
                patch.object(processor, "_get_file_path_from_user", return_value="provided.tcx") as mock_get_path:
            mock_select.return_value.ask.return_value = "Provide path"
            result = processor._get_tcx_file_path()
            mock_get_path.assert_called_once()
            self.assertEqual(result, "provided.tcx")

    def test_tcx_processor_handle_download_flow(self):
        processor = TCXProcessor()
        with patch.object(processor, "_get_activity_id", return_value="123456") as mock_get_id, \
                patch.object(processor, "_download_tcx_file") as mock_download, \
                patch("time.sleep") as mock_sleep, \
                patch.object(processor, "_get_latest_download", return_value="latest.tcx") as mock_latest, \
                patch.object(processor.logger, "info") as mock_info:
            result = processor._handle_download_flow()
            mock_get_id.assert_called_once()
            mock_download.assert_called_once_with("123456")
            mock_sleep.assert_called_once_with(3)
            mock_latest.assert_called_once()
            self.assertEqual(result, "latest.tcx")
            info_calls = [call.args[0] for call in mock_info.call_args_list]
            self.assertTrue(
                any("Selected activity ID" in msg for msg in info_calls)
            )
            self.assertTrue(
                any("Downloading the TCX file from Strava" in msg for msg in info_calls)
            )
            self.assertTrue(
                any("Automatically detected downloaded file path" in msg for msg in info_calls)
            )

    def test_tcx_processor_get_activity_id_valid(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = "123456"
            result = processor._get_activity_id()
            self.assertEqual(result, "123456")

            mock_text.return_value.ask.return_value = "abc123def"
            result = processor._get_activity_id()
            self.assertEqual(result, "123")

            mock_text.return_value.ask.return_value = "12-34-56"
            result = processor._get_activity_id()
            self.assertEqual(result, "123456")

    def test_tcx_processor_get_activity_id_invalid(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = "abc"
            with self.assertRaises(ValueError) as context:
                processor._get_activity_id()
            self.assertIn("Invalid activity ID provided",
                          str(context.exception))

            mock_text.return_value.ask.return_value = ""
            with self.assertRaises(ValueError):
                processor._get_activity_id()

    def test_tcx_processor_download_tcx_file_bike(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.BIKE
        with patch("src.main.webbrowser.open") as mock_open:
            processor._download_tcx_file("123456")
            mock_open.assert_called_once_with(
                "https://www.strava.com/activities/123456/export_tcx")

    def test_tcx_processor_download_tcx_file_swim(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.SWIM
        with patch("src.main.webbrowser.open") as mock_open:
            processor._download_tcx_file("654321")
            mock_open.assert_called_once_with(
                "https://www.strava.com/activities/654321/export_original")

    def test_tcx_processor_download_tcx_file_other(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.OTHER
        with patch("src.main.webbrowser.open") as mock_open:
            processor._download_tcx_file("111222")
            mock_open.assert_called_once_with(
                "https://www.strava.com/activities/111222/export_original")

    def test_tcx_processor_download_tcx_file_exception(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.BIKE
        with patch("src.main.webbrowser.open", side_effect=Exception("browser fail")), \
                patch.object(processor.logger, "error") as mock_error, \
                patch.object(processor.logger, "warning") as mock_warning, \
                patch('builtins.print') as mock_print:
            # Should not raise an exception anymore - gracefully handles the error
            processor._download_tcx_file("123456")
            mock_error.assert_called_with(
                "Failed to download the TCX file from Strava")
            # Should log a warning and print guidance
            mock_warning.assert_called()
            mock_print.assert_called()

    def test_is_wsl_environment(self):
        processor = TCXProcessor()
        # Test with mock WSL environment
        with patch('os.path.exists', return_value=True), \
                patch('builtins.open', unittest.mock.mock_open(read_data='Linux version 4.4.0-22621-Microsoft')):
            self.assertTrue(processor._is_wsl_environment())
        
        # Test with non-WSL environment
        with patch('os.path.exists', return_value=True), \
                patch('builtins.open', unittest.mock.mock_open(read_data='Linux version 5.15.0-generic')):
            self.assertFalse(processor._is_wsl_environment())
        
        # Test with no /proc/version file
        with patch('os.path.exists', return_value=False):
            self.assertFalse(processor._is_wsl_environment())

    def test_is_running_as_root(self):
        processor = TCXProcessor()
        # Test running as root
        with patch('src.main.os.geteuid', return_value=0):
            self.assertTrue(processor._is_running_as_root())
        
        # Test running as non-root
        with patch('src.main.os.geteuid', return_value=1000):
            self.assertFalse(processor._is_running_as_root())
        
        # Test when geteuid is not available (Windows) - simulate missing attribute
        with patch('src.main.hasattr', return_value=False):
            self.assertFalse(processor._is_running_as_root())

    def test_tcx_processor_get_latest_download_with_files(self):
        processor = TCXProcessor()
        mock_file1 = unittest.mock.Mock()
        mock_file2 = unittest.mock.Mock()
        mock_file1.stat.return_value.st_mtime = 100
        mock_file2.stat.return_value.st_mtime = 200
        with patch("src.main.Path.home") as mock_home:
            mock_downloads = unittest.mock.Mock()
            mock_home.return_value.__truediv__.return_value = mock_downloads
            mock_downloads.glob.return_value = [mock_file1, mock_file2]
            result = processor._get_latest_download()
            self.assertEqual(result, str(mock_file2))

    def test_tcx_processor_get_latest_download_no_files(self):
        processor = TCXProcessor()
        with patch("src.main.Path.home") as mock_home, \
                patch.object(processor, "_get_file_path_from_user", return_value="manual.tcx") as mock_get_path, \
                patch.object(processor.logger, "warning") as mock_warning:
            mock_downloads = unittest.mock.Mock()
            mock_home.return_value.__truediv__.return_value = mock_downloads
            mock_downloads.glob.return_value = []
            result = processor._get_latest_download()
            mock_warning.assert_called_with(
                "No TCX file found in Downloads folder")
            mock_get_path.assert_called_once()
            self.assertEqual(result, "manual.tcx")

    def test_tcx_processor_get_latest_download_exception(self):
        processor = TCXProcessor()
        with patch("src.main.Path.home") as mock_home, \
                patch.object(processor, "_get_file_path_from_user", return_value="manual2.tcx") as mock_get_path, \
                patch.object(processor.logger, "warning") as mock_warning:
            mock_downloads = unittest.mock.Mock()
            mock_home.return_value.__truediv__.return_value = mock_downloads
            mock_downloads.glob.side_effect = Exception("fail")
            result = processor._get_latest_download()
            mock_warning.assert_called_with(
                "No TCX file found in Downloads folder")
            mock_get_path.assert_called_once()
            self.assertEqual(result, "manual2.tcx")

    def test_tcx_processor_get_file_path_from_user_valid(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.path') as mock_path:
            mock_ask = mock_path.return_value
            mock_ask.ask.return_value = "valid.tcx"
            result = processor._get_file_path_from_user()
            mock_path.assert_called_once_with(
                "Enter the path to the TCX file:",
                validate=unittest.mock.ANY,
                only_directories=False
            )
            self.assertEqual(result, "valid.tcx")

    def test_tcx_processor_get_file_path_from_user_invalid(self):
        processor = TCXProcessor()
        # Simulate user cancelling or providing invalid input (returns None)
        with patch('src.main.questionary.path') as mock_path:
            mock_ask = mock_path.return_value
            mock_ask.ask.return_value = None
            result = processor._get_file_path_from_user()
            self.assertIsNone(result)

    def test_process_by_sport_swim(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.SWIM
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_format_swim_tcx") as mock_format:
            processor._process_by_sport("swim.tcx")
            mock_info.assert_any_call(
                "Formatting the TCX file for TrainingPeaks import")
            mock_format.assert_called_once_with("swim.tcx")

    def test_process_by_sport_other(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.OTHER
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_format_swim_tcx") as mock_format:
            processor._process_by_sport("other.tcx")
            mock_info.assert_any_call(
                "Formatting the TCX file for TrainingPeaks import")
            mock_format.assert_called_once_with("other.tcx")

    def test_process_by_sport_bike_valid_no_ai(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.BIKE
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_validate_tcx_file", return_value=(True, "tcx_data")) as mock_validate, \
                patch.object(processor, "_should_perform_ai_analysis", return_value=False) as mock_ai, \
                patch.object(processor, "_should_perform_tss", return_value=False) as mock_tss:
            processor._process_by_sport("bike.tcx")
            mock_info.assert_any_call("Validating the TCX file")
            mock_validate.assert_called_once_with("bike.tcx")
            mock_ai.assert_called_once()
            mock_tss.assert_called_once()

    def test_process_by_sport_run_valid_with_ai(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.RUN
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_validate_tcx_file", return_value=(True, "tcx_data")) as mock_validate, \
                patch.object(processor, "_should_perform_ai_analysis", return_value=True) as mock_ai, \
                patch.object(processor, "_perform_ai_analysis") as mock_perform_ai, \
                patch.object(processor, "_should_perform_tss", return_value=False) as mock_tss:
            processor._process_by_sport("run.tcx")
            mock_info.assert_any_call("Validating the TCX file")
            mock_validate.assert_called_once_with("run.tcx")
            mock_ai.assert_called_once()
            mock_perform_ai.assert_called_once_with(
                "tcx_data",
                main_module.Sport.RUN
            )
            mock_tss.assert_called_once()

    def test_process_by_sport_run_valid_with_ai_and_tss(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.RUN
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_validate_tcx_file", return_value=(True, "tcx_data")) as mock_validate, \
                patch.object(processor, "_should_perform_ai_analysis", return_value=True) as mock_ai, \
                patch.object(processor, "_perform_ai_analysis") as mock_perform_ai, \
                patch.object(processor, "_should_perform_tss", return_value=True) as mock_tss, \
                patch.object(processor, "_create_audio_summary", return_value=None) as mock_audio:
            processor._process_by_sport("run.tcx")
            mock_info.assert_any_call("Validating the TCX file")
            mock_validate.assert_called_once_with("run.tcx")
            mock_ai.assert_called_once()
            mock_perform_ai.assert_called_once_with(
                "tcx_data",
                main_module.Sport.RUN
            )
            mock_tss.assert_called_once()
            mock_audio.assert_called_once_with(mock_perform_ai.return_value)
            self.assertIsNone(processor._create_audio_summary("  "))

    def test_process_by_sport_invalid_tcx(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.BIKE
        with patch.object(processor.logger, "info"), \
                patch.object(processor, "_validate_tcx_file", return_value=(False, None)):
            with self.assertRaises(ValueError) as context:
                processor._process_by_sport("invalid.tcx")
            self.assertIn("Invalid TCX file", str(context.exception))

    def test_process_by_sport_unsupported(self):
        processor = TCXProcessor()
        processor.sport = None  # Not a valid Sport
        with self.assertRaises(ValueError) as context:
            processor._process_by_sport("file.tcx")
        self.assertIn("Unsupported sport", str(context.exception))

    def test_read_xml_file_success(self):
        processor = TCXProcessor()
        mock_content = "<xml>test</xml>"
        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)) as mock_open:
            result = processor._read_xml_file("somefile.tcx")
            mock_open.assert_called_once_with(
                "somefile.tcx", "r", encoding='utf-8')
            self.assertEqual(result, mock_content)

    def test_read_xml_file_exception(self):
        processor = TCXProcessor()
        with patch("builtins.open", side_effect=IOError("fail to open")), \
                patch.object(processor.logger, "error") as mock_error:
            with self.assertRaises(Exception) as context:
                processor._read_xml_file("badfile.tcx")
            mock_error.assert_called_with(
                "Failed to read XML file: %s", "fail to open")
            self.assertIn("fail to open", str(context.exception))

    def test_write_xml_file_success(self):
        processor = TCXProcessor()
        mock_content = "<xml>test</xml>"
        with patch("builtins.open", unittest.mock.mock_open()) as mock_open:
            processor._write_xml_file("output.tcx", mock_content)
            mock_open.assert_called_once_with(
                "output.tcx", "w", encoding='utf-8')
            handle = mock_open()
            handle.write.assert_called_once_with(mock_content)

    def test_write_xml_file_exception(self):
        processor = TCXProcessor()
        with patch("builtins.open", side_effect=IOError("write fail")), \
                patch.object(processor.logger, "error") as mock_error:
            with self.assertRaises(Exception) as context:
                processor._write_xml_file("badfile.tcx", "<xml></xml>")
            mock_error.assert_called_with(
                "Failed to write XML file: %s", "write fail")
            self.assertIn("write fail", str(context.exception))

    def test_validate_tcx_file_empty_file(self):
        processor = TCXProcessor()
        with patch.object(processor, "_read_xml_file", return_value="   "), \
                patch.object(processor.logger, "error") as mock_error:
            valid, data = processor._validate_tcx_file("empty.tcx")
            self.assertFalse(valid)
            self.assertIsNone(data)
            mock_error.assert_called_with("The TCX file is empty")

    def test_validate_tcx_file_valid(self):
        processor = TCXProcessor()
        mock_data = unittest.mock.Mock()
        mock_data.distance = 1234
        with patch.object(processor, "_read_xml_file", return_value="<xml></xml>"), \
                patch("src.main.TCXReader.read", return_value=mock_data) as mock_read, \
                patch.object(processor.logger, "info") as mock_info:
            valid, data = processor._validate_tcx_file("valid.tcx")
            self.assertTrue(valid)
            self.assertEqual(data, mock_data)
            mock_read.assert_called_once_with("valid.tcx")
            mock_info.assert_called_with(
                "TCX file is valid. Distance covered: %d meters", 1234
            )

    def test_validate_tcx_file_invalid(self):
        processor = TCXProcessor()
        with patch.object(processor, "_read_xml_file", return_value="<xml></xml>"), \
                patch("src.main.TCXReader.read", side_effect=Exception("bad tcx")), \
                patch.object(processor.logger, "error") as mock_error:
            valid, data = processor._validate_tcx_file("invalid.tcx")
            self.assertFalse(valid)
            self.assertIsNone(data)
            mock_error.assert_called_with("Invalid TCX file: %s", "bad tcx")

    def test_perform_ai_analysis(self):
        processor = TCXProcessor()
        mock_tcx_data = unittest.mock.Mock()
        mock_sport = main_module.Sport.BIKE

        with patch.object(processor, "_ensure_openai_key") as mock_ensure_key, \
                patch("src.main.questionary.text") as mock_text, \
                patch.object(processor, "_analyze_with_llm", return_value="analysis result") as mock_analyze, \
                patch.object(processor.logger, "info") as mock_info:

            mock_text.side_effect = [
                unittest.mock.Mock(ask=unittest.mock.Mock(
                    return_value="Planned workout")),
                unittest.mock.Mock(
                    ask=unittest.mock.Mock(return_value="English"))
            ]

            processor._perform_ai_analysis(mock_tcx_data, mock_sport)

            mock_ensure_key.assert_called_once()
            self.assertEqual(mock_text.call_count, 2)
            mock_analyze.assert_called_once()
            info_calls = [call.args[0] for call in mock_info.call_args_list]
            self.assertTrue(
                any("Performing AI analysis" in msg for msg in info_calls))
            self.assertTrue(
                any("AI analysis completed successfully" in msg for msg in info_calls))
            self.assertTrue(any("AI response" in msg for msg in info_calls))

    def test_perform_ai_analysis_empty_plan_and_default_language(self):
        processor = TCXProcessor()
        mock_tcx_data = unittest.mock.Mock()
        mock_sport = main_module.Sport.RUN

        with patch.object(processor, "_ensure_openai_key") as mock_ensure_key, \
                patch("src.main.questionary.text") as mock_text, \
                patch.object(processor, "_analyze_with_llm", return_value="result") as mock_analyze, \
                patch.object(processor.logger, "info") as mock_info:

            # Simulate user pressing enter for both questions (empty plan, default language)
            mock_text.side_effect = [
                unittest.mock.Mock(ask=unittest.mock.Mock(return_value="")),
                unittest.mock.Mock(ask=unittest.mock.Mock(
                    return_value="Portuguese (Brazil)"))
            ]

            processor._perform_ai_analysis(mock_tcx_data, mock_sport)

            mock_ensure_key.assert_called_once()
            self.assertEqual(mock_text.call_count, 2)
            mock_analyze.assert_called_once()
            info_calls = [call.args[0] for call in mock_info.call_args_list]
            self.assertTrue(
                any("Performing AI analysis" in msg for msg in info_calls))
            self.assertTrue(
                any("AI analysis completed successfully" in msg for msg in info_calls))
            self.assertTrue(any("AI response" in msg for msg in info_calls))

    def test_ensure_openai_key_already_set(self):
        processor = TCXProcessor()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "testkey"}), \
                patch("src.main.questionary.password") as mock_password, \
                patch("builtins.open") as mock_open, \
                patch("src.main.load_dotenv") as mock_load_dotenv, \
                patch.object(processor.logger, "info") as mock_info:
            processor._ensure_openai_key()
            mock_password.assert_not_called()
            mock_open.assert_not_called()
            mock_load_dotenv.assert_not_called()
            mock_info.assert_not_called()

    def test_ensure_openai_key_not_set(self):
        processor = TCXProcessor()
        with patch.dict("os.environ", {}, clear=True), \
                patch("src.main.questionary.password") as mock_password, \
                patch("builtins.open", unittest.mock.mock_open()) as mock_open, \
                patch("src.main.load_dotenv") as mock_load_dotenv, \
                patch.object(processor.logger, "info") as mock_info:
            mock_password.return_value.ask.return_value = "myapikey"
            processor._ensure_openai_key()
            mock_password.assert_called_once_with("Enter your OpenAI API key:")
            mock_open.assert_called_once_with(".env", "w", encoding="utf-8")
            handle = mock_open()
            handle.write.assert_called_once_with("OPENAI_API_KEY=myapikey")
            mock_load_dotenv.assert_called_once()
            mock_info.assert_called_once_with(
                "OpenAI API key loaded successfully")

    def test_analyze_with_llm(self):
        processor = TCXProcessor()
        mock_tcx_data = unittest.mock.Mock()
        mock_sport = main_module.Sport.BIKE
        mock_config = main_module.AnalysisConfig(
            training_plan="Plan",
            language="English"
        )

        # Patch all dependencies inside _analyze_with_llm
        with patch.object(processor, "_preprocess_trackpoints") as mock_preprocess, \
                patch.object(processor, "_get_analysis_prompt_template") as mock_prompt_template, \
                patch("src.main.PromptTemplate") as mock_prompt_template_cls, \
                patch("src.main.ChatOpenAI") as mock_chat_openai, \
                patch.dict("os.environ", {"OPENAI_API_KEY": "testkey"}):

            # Setup mocks
            mock_df = DataFrame({"a": [1], "b": [2]})
            mock_preprocess.return_value = mock_df
            mock_prompt_template.return_value = "TEMPLATE"
            mock_prompt_instance = unittest.mock.Mock()
            mock_prompt_instance.format.return_value = "PROMPT"
            mock_prompt_template_cls.from_template.return_value = mock_prompt_instance

            mock_llm_instance = unittest.mock.Mock()
            mock_response = unittest.mock.Mock()
            mock_response.content = [{'test': 'value'}, {"text": "LLM RESULT"}]
            mock_llm_instance.invoke.return_value = mock_response
            mock_chat_openai.return_value = mock_llm_instance

            result = processor._analyze_with_llm(
                mock_tcx_data,
                mock_sport,
                mock_config
            )

            mock_preprocess.assert_called_once_with(mock_tcx_data)
            mock_prompt_template.assert_called_once_with("Plan")
            mock_prompt_template_cls.from_template.assert_called_once_with(
                "TEMPLATE"
            )
            mock_prompt_instance.format.assert_called_once_with(
                sport=mock_sport.value,
                training_data=mock_df.to_csv(index=False),
                language="English",
                plan="Plan"
            )
            mock_chat_openai.assert_called_once_with(
                openai_api_key="testkey",
                model="gpt-5-mini",
                output_version="responses/v1",
                reasoning={"effort": "minimal"},
                model_kwargs={"text": {"verbosity": "high"}},
                max_retries=8,
                timeout=120
            )
            mock_llm_instance.invoke.assert_called_once_with("PROMPT")
            self.assertEqual(result, "LLM RESULT")

    def test_preprocess_trackpoints_calls_processor_process(self):
        processor = TCXProcessor()
        mock_tcx_data = unittest.mock.Mock()
        with patch("src.main.TrackpointProcessor") as mock_tp_cls:
            mock_tp_instance = mock_tp_cls.return_value
            mock_tp_instance.process.return_value = "processed_df"
            result = processor._preprocess_trackpoints(mock_tcx_data)
            mock_tp_cls.assert_called_once_with(processor.config)
            mock_tp_instance.process.assert_called_once_with(mock_tcx_data)
            self.assertEqual(result, "processed_df")

    def test_format_xml_file_success(self):
        processor = TCXProcessor()
        xml_content = "<root><child>data</child></root>"
        formatted_xml = '<?xml version="1.0" ?>\n<root>\n  <child>data</child>\n</root>\n'
        with patch.object(processor, "_read_xml_file", return_value=xml_content), \
                patch("src.main.parseString") as mock_parse, \
                patch.object(processor, "_write_xml_file") as mock_write:
            mock_dom = unittest.mock.Mock()
            mock_dom.toprettyxml.return_value = formatted_xml
            mock_parse.return_value = mock_dom
            processor._format_xml_file("file.tcx")
            mock_parse.assert_called_once_with(xml_content)
            mock_dom.toprettyxml.assert_called_once_with(indent="  ")
            mock_write.assert_called_once_with("file.tcx", formatted_xml)

    def test_format_xml_file_exception(self):
        processor = TCXProcessor()
        with patch.object(processor, "_read_xml_file", side_effect=Exception("fail")), \
                patch.object(processor.logger, "warning") as mock_warning:
            processor._format_xml_file("badfile.tcx")
            mock_warning.assert_called()
            args = mock_warning.call_args[0]
            self.assertIn(
                "Failed to format XML file: %s. File saved without formatting.", args[0])
            self.assertIn("fail", args[1])

    def test_trackpoint_processor_process_full_pipeline(self):
        # Create a mock TCXReader with trackpoints_to_dict returning a list of dicts
        mock_tcx_data = unittest.mock.Mock()
        # Simulate 100 trackpoints with required fields
        trackpoints = []
        for i in range(100):
            trackpoints.append({
                "distance": i * 10.0,
                "time": unittest.mock.Mock(value=1_600_000_000 + i * 10),
                "Speed": 3.0 + (i % 5),
                "cadence": 80 + (i % 3),
                "hr_value": 140 + (i % 10),
                "latitude": -23.0 + i * 0.0001,
                "longitude": -46.0 + i * 0.0001
            })
        mock_tcx_data.trackpoints_to_dict.return_value = trackpoints

        processor = TrackpointProcessor(ProcessingConfig())
        df = processor.process(mock_tcx_data)

        # Check that the returned object is a DataFrame
        self.assertIsInstance(df, DataFrame)
        # Check that required columns exist
        self.assertIn("Distance_Km", df.columns)
        self.assertIn("Time", df.columns)
        self.assertIn("Speed_Kmh", df.columns)
        self.assertIn("Pace", df.columns)
        # Check that time is formatted as HH:MM:SS
        self.assertRegex(df["Time"].iloc[0], r"\d{2}:\d{2}:\d{2}")
        # Check that there are no NaN in required columns
        self.assertFalse(
            df[["Distance_Km", "Speed_Kmh", "Pace"]].isnull().any().any())
        # Check that the number of rows is less than or equal to the original (due to possible reduction)
        self.assertLessEqual(len(df), 100)

    def test_remove_sparse_columns_removes_cadence(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # cadence has 4/6 nulls (>= 3), should be removed
        df = DataFrame({
            "cadence": [None, None, None, 1, 2, 3],
            "Speed_Kmh": [10, 11, 12, 13, 14, 15],
            "Distance_Km": [1, 2, 3, 4, 5, 6],
            "Time": [1, 2, 3, 4, 5, 6]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertNotIn("cadence", df2.columns)
        self.assertIn("Speed_Kmh", df2.columns)

    def test_remove_sparse_columns_removes_hr_value(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # hr_value has all nulls, should be removed
        df = DataFrame({
            "hr_value": [None, None, None, None],
            "Speed_Kmh": [10, 11, 12, 13],
            "Distance_Km": [1, 2, 3, 4],
            "Time": [1, 2, 3, 4]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertNotIn("hr_value", df2.columns)

    def test_remove_sparse_columns_removes_lat_lon_together(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # latitude and longitude both have >= threshold nulls, both should be dropped together
        df = DataFrame({
            "latitude": [None, None, 1, 2],
            "longitude": [None, None, 3, 4],
            "Speed_Kmh": [10, 11, 12, 13],
            "Distance_Km": [1, 2, 3, 4],
            "Time": [1, 2, 3, 4]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertNotIn("latitude", df2.columns)
        self.assertNotIn("longitude", df2.columns)

    def test_remove_sparse_columns_does_not_remove_if_below_threshold(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # Only 1 null in cadence, threshold is 2.5, so should not be removed
        df = DataFrame({
            "cadence": [None, 1, 2, 3, 4],
            "Speed_Kmh": [10, 11, 12, 13, 14],
            "Distance_Km": [1, 2, 3, 4, 5],
            "Time": [1, 2, 3, 4, 5]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertIn("cadence", df2.columns)

    def test_remove_sparse_columns_handles_missing_columns(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # DataFrame does not have any of the columns to check
        df = DataFrame({
            "Speed_Kmh": [10, 11, 12],
            "Distance_Km": [1, 2, 3],
            "Time": [1, 2, 3]
        })
        df2 = processor._remove_sparse_columns(df)
        self.assertListEqual(list(df2.columns), [
                             "Speed_Kmh", "Distance_Km", "Time"])

    def test_reduce_data_size_large_dataset(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # 5000 rows triggers large threshold
        df = DataFrame({
            "Speed_Kmh": np.random.rand(5000),
            "Distance_Km": np.arange(5000),
            "Time": np.arange(5000)
        })
        with patch.object(processor, "_apply_euclidean_filtering", return_value="filtered_df") as mock_apply:
            result = processor._reduce_data_size(df)
            mock_apply.assert_called_once_with(
                df, processor.config.euclidean_threshold_large)
            self.assertEqual(result, "filtered_df")

    def test_reduce_data_size_medium_dataset(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # 2000 rows triggers medium threshold
        df = DataFrame({
            "Speed_Kmh": np.random.rand(2000),
            "Distance_Km": np.arange(2000),
            "Time": np.arange(2000)
        })
        with patch.object(processor, "_apply_euclidean_filtering", return_value="filtered_df") as mock_apply:
            result = processor._reduce_data_size(df)
            mock_apply.assert_called_once_with(
                df, processor.config.euclidean_threshold_medium)
            self.assertEqual(result, "filtered_df")

    def test_reduce_data_size_small_dataset(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # 500 rows triggers small threshold
        df = DataFrame({
            "Speed_Kmh": np.random.rand(500),
            "Distance_Km": np.arange(500),
            "Time": np.arange(500)
        })
        with patch.object(processor, "_apply_euclidean_filtering", return_value="filtered_df") as mock_apply:
            result = processor._reduce_data_size(df)
            mock_apply.assert_called_once_with(
                df, processor.config.euclidean_threshold_small)
            self.assertEqual(result, "filtered_df")

    def test_reduce_data_size_empty_dataframe(self):
        processor = TrackpointProcessor(ProcessingConfig())
        df = DataFrame(columns=["Speed_Kmh", "Distance_Km", "Time"])
        with patch.object(processor, "_apply_euclidean_filtering", return_value="filtered_df") as mock_apply:
            result = processor._reduce_data_size(df)
            mock_apply.assert_called_once_with(
                df, processor.config.euclidean_threshold_small)
            self.assertEqual(result, "filtered_df")

    def test_apply_euclidean_filtering_returns_original_if_too_few_rows(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # DataFrame with less than 50 rows should be returned unchanged
        df = DataFrame({
            "Speed_Kmh": np.random.rand(10),
            "Distance_Km": np.arange(10),
            "Time": np.arange(10)
        })
        result = processor._apply_euclidean_filtering(df, 0.5)
        self.assertTrue(result.equals(df))

    def test_apply_euclidean_filtering_returns_original_if_no_numeric(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # DataFrame with no numeric columns should be returned unchanged
        df = DataFrame({
            "A": ["a"] * 60,
            "B": ["b"] * 60
        })
        result = processor._apply_euclidean_filtering(df, 0.5)
        self.assertTrue(result.equals(df))

    def test_apply_euclidean_filtering_reduces_rows(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # DataFrame with 100 rows and two numeric columns
        df = DataFrame({
            "Speed_Kmh": np.linspace(10, 20, 100),
            "Distance_Km": np.linspace(0, 10, 100),
            "Time": np.arange(100)
        })
        # Use a high percentage to ensure reduction
        result = processor._apply_euclidean_filtering(df, 0.2)
        self.assertLess(len(result), len(df))
        self.assertGreaterEqual(len(result), len(df) - int(0.2 * len(df)))

    def test_apply_euclidean_filtering_handles_exception(self):
        processor = TrackpointProcessor(ProcessingConfig())
        df = DataFrame({
            "Speed_Kmh": np.random.rand(60),
            "Distance_Km": np.arange(60),
            "Time": np.arange(60)
        })
        # Patch pdist to raise an exception
        with patch("src.main.pdist", side_effect=Exception("fail")), \
                patch.object(processor.logger, "warning") as mock_warning:
            result = processor._apply_euclidean_filtering(df, 0.1)
            self.assertTrue(result.equals(df))
            mock_warning.assert_called()
            self.assertIn("Failed to apply euclidean filtering",
                          mock_warning.call_args[0][0])

    def test_apply_euclidean_filtering_stops_before_removing_too_many(self):
        processor = TrackpointProcessor(ProcessingConfig())
        # 60 rows, percentage 0.9 would try to remove 54, but should stop at len(df)-10=50
        df = DataFrame({
            "Speed_Kmh": np.random.rand(60),
            "Distance_Km": np.arange(60),
            "Time": np.arange(60)
        })
        result = processor._apply_euclidean_filtering(df, 0.9)
        # Should not remove more than len(df)-10 rows
        self.assertGreaterEqual(len(result), 10)

    def test_create_audio_summary_user_accepts(self):
        processor = TCXProcessor()

        with patch("src.main.openai.OpenAI") as mock_openai_class, \
                patch("src.main.time.time", return_value=1234567890), \
                patch.dict("os.environ", {"OPENAI_API_KEY": "testkey"}), \
                patch.object(processor, "_clean_text_for_speech", return_value="Clean text") as mock_clean, \
                patch.object(processor.logger, "info") as mock_info:

            mock_client = unittest.mock.Mock()
            mock_response = unittest.mock.Mock()
            mock_client.audio.speech.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            processor._create_audio_summary("## Test Analysis\n**Bold text**")

            mock_openai_class.assert_called_once()
            mock_clean.assert_called_once_with(
                "## Test Analysis\n**Bold text**")
            mock_client.audio.speech.create.assert_called_once_with(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input="Clean text",
                speed=1.1,
                response_format="mp3"
            )
            download_folder = Path.home() / "Downloads"

            mock_response.stream_to_file.assert_called_once_with(
                f"{download_folder}/training_analysis_summary_1234567890.mp3",
                chunk_size=1024
            )

            info_calls = mock_info.call_args_list
            self.assertTrue(
                any(
                    "Generating audio summary using OpenAI TTS" in call.args[0] for call in info_calls)
            )

            file_log_found = False
            for call in info_calls:
                if "Audio summary saved as:" in call.args[0] and len(call.args) > 1:
                    self.assertEqual(
                        str(call.args[1]),
                        f"{download_folder}/training_analysis_summary_1234567890.mp3"
                    )
                    file_log_found = True
                    break
            self.assertTrue(
                file_log_found, "Expected file logging call not found")

    def test_create_audio_summary_exception_handling(self):
        processor = TCXProcessor()

        with patch("src.main.questionary.confirm") as mock_confirm, \
                patch("src.main.openai.OpenAI", side_effect=Exception("OpenAI TTS Error")), \
                patch.dict("os.environ", {"OPENAI_API_KEY": "testkey"}), \
                patch.object(processor.logger, "warning") as mock_warning:

            mock_confirm.return_value.ask.return_value = True

            processor._create_audio_summary("Test text")

            mock_warning.assert_called_once_with(
                "Failed to generate audio summary: %s", "OpenAI TTS Error")

    def test_create_audio_summary_empty_openai_key(self):
        processor = TCXProcessor()

        with patch("src.main.questionary.confirm") as mock_confirm, \
                patch.dict("os.environ", {}, clear=True), \
                patch.object(processor.logger, "error") as mock_error:
            mock_confirm.return_value.ask.return_value = True
            processor._create_audio_summary("Test text")
            mock_error.assert_called_once_with(
                "OpenAI API key not found. Aborting audio summary generation."
            )
            self.assertIsNone(processor._create_audio_summary("Test text"))

    def test_clean_text_for_speech(self):
        processor = TCXProcessor()

        # Test markdown cleanup
        input_text = """
# Session Overview
        
- Summarize key characteristics
- **Pace/Speed:** Include averages
- *Heart Rate*: Show distribution
        
## Performance Metrics
        
- Test item 1
* Test item 2
        
Multiple    spaces    and


newlines.
        """

        result = processor._clean_text_for_speech(input_text)

        # Check that markdown formatting is removed
        self.assertNotIn('#', result)
        self.assertNotIn('**', result)
        self.assertNotIn('*', result)
        self.assertNotIn('-', result)

        # Check that text is properly spaced
        self.assertNotIn('  ', result)  # No double spaces
        self.assertNotIn('\n', result)  # No newlines

        # Check basic content is preserved
        self.assertIn('Session Overview', result)
        self.assertIn('Performance Metrics', result)

    def test_clean_text_for_speech_length_limit(self):
        processor = TCXProcessor()

        long_text = "A" * 1500

        result = processor._clean_text_for_speech(long_text)

        self.assertEqual(len(result), 1500)

    def test_should_perform_tss_true(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            result = processor._should_perform_tss()
            mock_confirm.assert_called_once_with(
                "Do you want to generate an audio summary of the analysis?",
                default=False
            )
            self.assertTrue(result)

    def test_should_perform_tss_false(self):
        processor = TCXProcessor()
        with patch('src.main.questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            result = processor._should_perform_tss()
            mock_confirm.assert_called_once_with(
                "Do you want to generate an audio summary of the analysis?",
                default=False
            )
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
