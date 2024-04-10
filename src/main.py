import re
import os
import sys
import logging

import questionary

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.addHandler(handler)


def main():
    file_path = questionary.text(
        "Enter the path to the TCX file you want to export to trainingpeaks",
        validate=lambda text: os.path.isfile(text)
    ).ask()
    sport = questionary.select(
        "What sport do you want to export to trainingpeaks?",
        choices=[
            "Bike",
            "Run",
            "Swim",
            "Other",
        ],
    ).ask()

    logger.info(f"Selected sport: %s", sport)
    if sport in ["Swim", "Other"]:
        logger.info("Formating the TCX file to be imported to trainingpeaks")
        format_to_swim(file_path)
    elif sport == "Run":
        logger.info("Not implemented yet")
    elif sport == "Bike":
        logger.info("Not implemented yet")
    else:
        logger.error("Invalid sport selected")
        sys.exit(1)


def format_to_swim(file_path: str) -> None:
    with open(file_path, "r") as xml_file:
        xml_str = xml_file.readlines()
        xml_str[0] = '''<TrainingCenterDatabase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">\n'''
        xml_str = "".join(xml_str)
        xml_str = re.sub(
            r"<Value>(\d+)\.0</Value>",
            r"<Value>\1</Value>",
            xml_str
        )
        xml_str = re.sub(
            r'<Activity Sport="Swim">',
            r'<Activity Sport="Other">',
            xml_str
        )
        xml_file.close()

    with open(file_path, "w") as xml_file:
        xml_file.write(xml_str)
        xml_file.close()


if __name__ == "__main__":
    main()
