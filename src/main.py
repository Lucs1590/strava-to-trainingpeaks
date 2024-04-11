import re
import os
import sys
import logging
from xml.dom import minidom
from typing import List

import questionary
import webbrowser

logger = logging.getLogger()

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('logs.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():
    sport = ask_sport()
    logger.info(f"Selected sport: {sport}")

    activity_id = ask_activity_id()
    logger.info(f"Selected activity ID: {activity_id}")
    logger.info("Downloading the TCX file from strava")
    download_tcx_file(activity_id, sport)

    file_path = ask_file_path()

    if sport in ["Swim", "Other"]:
        logger.info("Formatting the TCX file to be imported to trainingpeaks")
        format_to_swim(file_path)
    elif sport == "Run":
        logger.info("Not implemented yet")
    elif sport == "Bike":
        logger.info("Not implemented yet")
    else:
        logger.error("Invalid sport selected")
        sys.exit(1)

    indent_xml_file(file_path)
    logger.info("Done!")


def ask_sport() -> str:
    return questionary.select(
        "What sport do you want to export to trainingpeaks?",
        choices=["Bike", "Run", "Swim", "Other"]
    ).ask()


def ask_activity_id() -> str:
    return questionary.text(
        "Enter the strava activity ID you want to export to trainingpeaks:"
    ).ask()


def download_tcx_file(activity_id: str, sport: str) -> None:
    if sport in ["Swim", "Other"]:
        url = f"https://www.strava.com/activities/{activity_id}/export_original"
    else:
        url = f"https://www.strava.com/activities/{activity_id}/export_tcx"
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(
            "It was not possible to download the TCX file from strava."
        )
        logger.error(f"Error opening the browser: {e}.")
        sys.exit(1)


def ask_file_path() -> str:
    return questionary.text(
        "Check if the TCX file was downloaded and then enter the path to the file:",
        validate=os.path.isfile
    ).ask()


def format_to_swim(file_path: str) -> None:
    xml_str = read_xml_file(file_path)
    xml_str = modify_xml_header(xml_str)
    xml_str = re.sub(r"<Value>(\d+)\.0</Value>", r"<Value>\1</Value>", xml_str)
    xml_str = re.sub(r'<Activity Sport="Swim">',
                     r'<Activity Sport="Other">', xml_str)
    write_xml_file(file_path, xml_str)


def read_xml_file(file_path: str) -> str:
    with open(file_path, "r") as xml_file:
        return xml_file.read()


def modify_xml_header(xml_str: str) -> str:
    return xml_str.replace(
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">',
        '<TrainingCenterDatabase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">'
    )


def write_xml_file(file_path: str, xml_str: str) -> None:
    with open(file_path, "w") as xml_file:
        xml_file.write(xml_str)


def indent_xml_file(file_path: str) -> None:
    try:
        with open(file_path, "r") as xml_file:
            xml_content = xml_file.read()

        xml_dom = minidom.parseString(xml_content)

        with open(file_path, "w") as xml_file:
            xml_file.write(xml_dom.toprettyxml(indent="  "))
    except Exception as e:
        logger.warning(
            "It was not possible to indent the XML file. The file will be saved without indentation."
        )


if __name__ == "__main__":
    main()
