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
        # Simulate invalid XML content
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


if __name__ == '__main__':
    unittest.main()
