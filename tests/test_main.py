import os
#import sys
import unittest
from unittest.mock import patch

# sys.path.append(os.path.abspath(''))

from src.main import (
    download_tcx_file,
    read_xml_file,
    modify_xml_header,
    write_xml_file,
    format_to_swim,
    validate_tcx_file,
    indent_xml_file,
    main,
    ask_sport,
    ask_file_location,
    ask_activity_id,
    ask_file_path,
    get_latest_download
)


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

        with open(file_path, "r", encoding='utf-8') as xml_file:
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

        with open(file_path, "r", encoding='utf-8') as xml_file:
            content = xml_file.read()

        self.assertIn(
            "<root>",
            content
        )

    def test_indent_xml_file_error(self):
        file_path = "assets/test.xml"

        with patch('src.main.parseString') as mock_parse_string:
            mock_parse_string.return_value = Exception("Error")
            indent_xml_file(file_path)

        self.assertTrue(mock_parse_string.called)

    @patch('src.main.get_latest_download')
    @patch('src.main.ask_sport')
    @patch('src.main.ask_file_location')
    @patch('src.main.ask_activity_id')
    @patch('src.main.download_tcx_file')
    @patch('src.main.format_to_swim')
    @patch('src.main.validate_tcx_file')
    @patch('src.main.indent_xml_file')
    def test_main(self, mock_indent, mock_validate, mock_format, mock_download, mock_ask_id,
                  mock_ask_location, mock_ask_sport, mock_latest_download):
        mock_ask_sport.return_value = "Swim"
        mock_ask_location.return_value = "Download"
        mock_ask_id.return_value = "12345"
        mock_latest_download.return_value = "assets/swim.tcx"

        main()

        mock_ask_sport.assert_called_once()
        mock_ask_location.assert_called_once()
        mock_ask_id.assert_called_once()
        mock_latest_download.assert_called_once()
        mock_download.assert_called_once_with("12345", "Swim")
        mock_format.assert_called_once_with("assets/swim.tcx")
        mock_validate.assert_not_called()
        mock_indent.assert_called_once_with("assets/swim.tcx")

    @patch('src.main.ask_sport')
    @patch('src.main.ask_file_location')
    @patch('src.main.ask_activity_id')
    @patch('src.main.download_tcx_file')
    @patch('src.main.get_latest_download')
    @patch('src.main.format_to_swim')
    @patch('src.main.validate_tcx_file')
    @patch('src.main.indent_xml_file')
    def test_main_invalid_sport(self, mock_indent, mock_validate, mock_format, mock_latest_download, mock_download,
                                mock_ask_id, mock_ask_location, mock_ask_sport):
        mock_ask_sport.return_value = "InvalidSport"
        mock_ask_location.return_value = "Download"
        mock_ask_id.return_value = "12345"
        mock_latest_download.return_value = "assets/swim.tcx"

        with self.assertRaises(ValueError):
            main()

        mock_ask_sport.assert_called_once()
        mock_ask_location.assert_called_once()
        mock_ask_id.assert_called_once()
        mock_latest_download.assert_called_once()
        mock_download.assert_called_once()
        mock_format.assert_not_called()
        mock_validate.assert_not_called()
        mock_indent.assert_not_called()

    @patch('src.main.ask_sport')
    @patch('src.main.ask_file_location')
    @patch('src.main.ask_activity_id')
    @patch('src.main.download_tcx_file')
    @patch('src.main.ask_file_path')
    @patch('src.main.format_to_swim')
    @patch('src.main.validate_tcx_file')
    @patch('src.main.indent_xml_file')
    def test_main_bike_sport(self, mock_indent, mock_validate, mock_format, mock_ask_path, mock_download,
                             mock_ask_id, mock_ask_location, mock_ask_sport):
        mock_ask_sport.return_value = "Bike"
        mock_ask_location.return_value = "Local"
        mock_ask_path.return_value = "assets/bike.tcx"

        main()

        mock_ask_sport.assert_called_once()
        mock_ask_location.assert_called_once()
        mock_ask_id.assert_not_called()
        mock_ask_path.assert_called_once()
        mock_download.assert_not_called()
        mock_format.assert_not_called()
        mock_validate.assert_called_once_with("assets/bike.tcx")
        mock_indent.assert_called_once_with("assets/bike.tcx")

    def test_ask_sport(self):
        with patch('src.main.questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "Bike"
            result = ask_sport()
            mock_select.assert_called_once_with(
                "Which sport do you want to export to TrainingPeaks?",
                choices=["Bike", "Run", "Swim", "Other"]
            )
            self.assertEqual(result, "Bike")

    def test_ask_file_location(self):
        with patch('src.main.questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = "Download"
            result = ask_file_location()
            mock_select.assert_called_once_with(
                "Do you want to download the TCX file from Strava or provide the file path?",
                choices=["Download", "Provide path"]
            )
            self.assertEqual(result, "Download")

    def test_ask_activity_id(self):
        with patch('src.main.questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = "1234"
            result = ask_activity_id()
            mock_text.assert_called_once_with(
                "Enter the Strava activity ID you want to export to TrainingPeaks:"
            )
            self.assertEqual(result, "1234")

    def test_ask_file_path(self):
        with patch('src.main.questionary.path') as mock_path:
            mock_path.return_value.ask.return_value = "assets/test.tcx"
            result = ask_file_path("Provide path")
            mock_path.assert_called_once_with(
                "Enter the path to the TCX file:",
                validate=os.path.isfile
            )
            self.assertEqual(result, "assets/test.tcx")

            mock_path.reset_mock()

            mock_path.return_value.ask.return_value = "assets/downloaded.tcx"
            result = ask_file_path("Download")
            mock_path.assert_called_once_with(
                "Check if the TCX file was downloaded and then enter the path to the file:",
                validate=os.path.isfile
            )
            self.assertEqual(result, "assets/downloaded.tcx")

    @patch('os.path.expanduser')
    @patch('os.listdir')
    def test_get_latest_downloads_without_ask(self, mock_listdir, mock_expanduser):
        mock_listdir.return_value = ["bike.tcx", "run.tcx", "swim.tcx"]
        mock_expanduser.return_value = "assets/"
        result = get_latest_download()

        self.assertEqual(result, "assets/swim.tcx")

    @patch('src.main.ask_file_path')
    def test_get_latest_downloads_with_ask(self, mock_ask_path):
        mock_ask_path.return_value = "assets/bike.tcx"
        result = get_latest_download()

        self.assertEqual(result, "assets/bike.tcx")


if __name__ == '__main__':
    unittest.main()
