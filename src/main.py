import re
import os
import logging
import webbrowser

from defusedxml.minidom import parseString

import questionary

from tcxreader.tcxreader import TCXReader

logger = logging.getLogger()

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('logs.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():
    sport = ask_sport()
    logger.info(f"Selected sport: %s", sport)

    file_location = ask_file_location()

    if file_location == "Download":
        activity_id = ask_activity_id()
        logger.info(f"Selected activity ID: %s", activity_id)
        logger.info("Downloading the TCX file from Strava")
        download_tcx_file(activity_id, sport)

    file_path = ask_file_path(file_location)

    if sport in ["Swim", "Other"]:
        logger.info("Formatting the TCX file to be imported to TrainingPeaks")
        format_to_swim(file_path)
    elif sport in ["Bike", "Run"]:
        logger.info("Validating the TCX file")
        validate_tcx_file(file_path)
    else:
        logger.error("Invalid sport selected")
        raise ValueError("Invalid sport selected")

    indent_xml_file(file_path)
    logger.info("Process completed successfully!")


def ask_sport() -> str:
    return questionary.select(
        "Which sport do you want to export to TrainingPeaks?",
        choices=["Bike", "Run", "Swim", "Other"]
    ).ask()


def ask_file_location() -> str:
    return questionary.select(
        "Do you want to download the TCX file from Strava or provide the file path?",
        choices=["Download", "Provide path"]
    ).ask()


def ask_activity_id() -> str:
    activity_id = questionary.text(
        "Enter the Strava activity ID you want to export to TrainingPeaks:"
    ).ask()
    return re.sub(r"\D", "", activity_id)


def download_tcx_file(activity_id: str, sport: str) -> None:
    if sport in ["Swim", "Other"]:
        url = f"https://www.strava.com/activities/{activity_id}/export_original"
    else:
        url = f"https://www.strava.com/activities/{activity_id}/export_tcx"
    try:
        webbrowser.open(url)
    except Exception as err:
        logger.error(
            "Failed to download the TCX file from Strava."
        )
        raise ValueError("Error opening the browser") from err


def ask_file_path(file_location) -> str:
    question = "Enter the path to the TCX file:" if file_location == "Provide path" else "Check if the TCX file was downloaded and then enter the path to the file:"
    return questionary.path(
        question,
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
    with open(file_path, "r", encoding='utf-8') as xml_file:
        return xml_file.read()


def modify_xml_header(xml_str: str) -> str:
    return xml_str.replace(
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">',
        '<TrainingCenterDatabase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">'
    )


def write_xml_file(file_path: str, xml_str: str) -> None:
    with open(file_path, "w", encoding='utf-8') as xml_file:
        xml_file.write(xml_str)


def validate_tcx_file(file_path: str) -> bool:
    xml_str = read_xml_file(file_path)
    if not xml_str:
        logger.error("The TCX file is empty.")
        raise ValueError("The TCX file is empty.")

    tcx_reader = TCXReader()
    try:
        data = tcx_reader.read(file_path)
        logger.info(
            "The TCX file is valid. You covered a significant distance in this activity, with %d meters.",
            data.distance
        )
        return True
    except Exception as err:
        logger.error("Invalid TCX file.")
        raise ValueError(f"Error reading the TCX file: {err}") from err


def indent_xml_file(file_path: str) -> None:
    try:
        with open(file_path, "r", encoding='utf-8') as xml_file:
            xml_content = xml_file.read()

        xml_dom = parseString(xml_content)

        with open(file_path, "w", encoding='utf-8') as xml_file:
            xml_file.write(xml_dom.toprettyxml(indent="  "))
    except Exception:
        logger.warning(
            "Failed to indent the XML file. The file will be saved without indentation."
        )


if __name__ == "__main__":
    main()
