import unittest
from unittest.mock import MagicMock, patch

from src.main import *


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        pass

    @patch('src.main.webbrowser.open')
    def test_download_tcx_file(self, mock_open):
        # Test for sport "Swim"
        activity_id = "12345"
        sport = "Swim"
        expected_url = "https://www.strava.com/activities/12345/export_original"

        download_tcx_file(activity_id, sport)

        mock_open.assert_called_once_with(expected_url)

        # Test for sport "Run"
        activity_id = "67890"
        sport = "Run"
        expected_url = "https://www.strava.com/activities/67890/export_tcx"

        download_tcx_file(activity_id, sport)

        mock_open.assert_called_with(expected_url)

    @patch('src.main.webbrowser.open')
    def test_download_tcx_file_error(self, mock_open):
        activity_id = "12345"
        sport = "Other"
        mock_open.side_effect = Exception("Error")

        with self.assertRaises(ValueError):
            download_tcx_file(activity_id, sport)

    def test_read_xml_file(self):
        file_path = "assets/bike.tcx"
        content = read_xml_file(file_path)

        self.assertIn(
            '<?xml version="1.0" encoding="UTF-8"?>',
            content
        )

    def test_modify_xml_header(self):
        xml_str = """<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">"""
        result = modify_xml_header(xml_str)

        self.assertIn(
            "http://www.w3.org/2001/XMLSchema-instance",
            result
        )

    def test_write_xml_file(self):
        file_path = "assets/test.xml"
        xml_str = "<root><element>Test</element></root>"

        write_xml_file(file_path, xml_str)

        with open(file_path, "r") as xml_file:
            content = xml_file.read()

        self.assertEqual(content, xml_str)

    @patch('src.main.write_xml_file')
    def test_format_to_swim(self, mock_write):
        file_path = "assets/swim.tcx"
        format_to_swim(file_path)

        mock_write.assert_called_once()
        self.assertTrue(mock_write.called)

    def test_validate_tcx_file(self):
        file_path = "assets/bike.tcx"
        result = validate_tcx_file(file_path)
        self.assertTrue(result)

    def test_validate_tcx_file_error(self):
        file_path = "assets/swim.tcx"

        with self.assertRaises(ValueError):
            validate_tcx_file(file_path)

    @patch('src.main.read_xml_file')
    def test_validate_tcx_file_error_no_file(self, mock_read):
        file_path = "assets/test.xml"
        mock_read.return_value = ""

        with self.assertRaises(ValueError):
            validate_tcx_file(file_path)

    def test_indent_xml_file(self):
        file_path = "assets/test.xml"
        indent_xml_file(file_path)

        with open(file_path, "r") as xml_file:
            content = xml_file.read()

        self.assertIn(
            "<root>",
            content
        )

    def test_indent_xml_file_error(self):
        file_path = "assets/test.xml"

        with patch('src.main.minidom.parseString') as mock_parseString:
            mock_parseString.return_value = Exception("Error")
            indent_xml_file(file_path)

        self.assertTrue(mock_parseString.called)


if __name__ == '__main__':
    unittest.main()
