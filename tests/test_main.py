import unittest

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
        self.assertIn("ANALYSIS STRUCTURE", prompt_no_plan)
        prompt_with_plan = processor._get_analysis_prompt_template(True)
        self.assertIn("TRAINING PLAN EXECUTION ANALYSIS", prompt_with_plan)

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
                patch.object(processor.logger, "error") as mock_error:
            with self.assertRaises(ValueError) as context:
                processor._download_tcx_file("123456")
            self.assertIn("Error opening the browser", str(context.exception))
            mock_error.assert_called_with(
                "Failed to download the TCX file from Strava")

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
                patch.object(processor, "_should_perform_ai_analysis", return_value=False) as mock_ai:
            processor._process_by_sport("bike.tcx")
            mock_info.assert_any_call("Validating the TCX file")
            mock_validate.assert_called_once_with("bike.tcx")
            mock_ai.assert_called_once()

    def test_process_by_sport_run_valid_with_ai(self):
        processor = TCXProcessor()
        processor.sport = main_module.Sport.RUN
        with patch.object(processor.logger, "info") as mock_info, \
                patch.object(processor, "_validate_tcx_file", return_value=(True, "tcx_data")) as mock_validate, \
                patch.object(processor, "_should_perform_ai_analysis", return_value=True) as mock_ai, \
                patch.object(processor, "_perform_ai_analysis") as mock_perform_ai:
            processor._process_by_sport("run.tcx")
            mock_info.assert_any_call("Validating the TCX file")
            mock_validate.assert_called_once_with("run.tcx")
            mock_ai.assert_called_once()
            mock_perform_ai.assert_called_once_with(
                "tcx_data", main_module.Sport.RUN)

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

            # Mock questionary.text for training_plan and language
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
            # Check that logger.info was called with expected messages
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


if __name__ == '__main__':
    unittest.main()
