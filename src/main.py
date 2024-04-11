import re
import os
import sys
import logging
from typing import List

import questionary

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():
    file_path = ask_file_path()
    sport = ask_sport()

    logger.info(f"Selected sport: {sport}")
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

    indent_xml(file_path)
    logger.info("Done!")


def ask_file_path() -> str:
    return questionary.text(
        "Enter the path to the TCX file you want to export to trainingpeaks",
        validate=os.path.isfile
    ).ask()


def ask_sport() -> str:
    return questionary.select(
        "What sport do you want to export to trainingpeaks?",
        choices=["Bike", "Run", "Swim", "Other"]
    ).ask()


def format_to_swim(file_path: str) -> None:
    xml_str = read_xml_file(file_path)
    xml_str = modify_xml_header(xml_str)
    xml_str = re.sub(r"<Value>(\d+)\.0</Value>", r"<Value>\1</Value>", xml_str)
    xml_str = re.sub(r'<Activity Sport="Swim">',
                     r'<Activity Sport="Other">',xml_str)
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


if __name__ == "__main__":
    main()
