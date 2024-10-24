import re
import os
import time
import logging
import webbrowser

from typing import Tuple

import numpy as np
import pandas as pd
import questionary

from tqdm import tqdm
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate
from defusedxml.minidom import parseString
from scipy.spatial.distance import squareform, pdist
from tcxreader.tcxreader import TCXReader


load_dotenv()
logger = logging.getLogger()

if not logger.handlers:
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('logs.log')
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def main():
    sport = ask_sport()
    logger.info("Selected sport: %s", sport)

    file_location = ask_file_location()

    if file_location == "Download":
        activity_id = ask_activity_id()
        logger.info("Selected activity ID: %s", activity_id)
        logger.info("Downloading the TCX file from Strava")
        download_tcx_file(activity_id, sport)

        time.sleep(3)
        file_path = get_latest_download()
        logger.info(
            f"Automatically detected downloaded file path: {file_path}"
        )
    else:
        file_path = ask_file_path(file_location)

    if file_path:
        if sport in ["Swim", "Other"]:
            logger.info(
                "Formatting the TCX file to be imported to TrainingPeaks"
            )
            format_to_swim(file_path)
        elif sport in ["Bike", "Run"]:
            logger.info("Validating the TCX file")
            _, tcx_data = validate_tcx_file(file_path)
            if ask_llm_analysis():
                plan = ask_training_plan()
                logger.info("Performing LLM analysis")
                perform_llm_analysis(tcx_data, sport, plan)
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
    url = f"https://www.strava.com/activities/{activity_id}/export_{'original' if sport in ['Swim', 'Other'] else 'tcx'}"
    retry_attempts = 3
    for attempt in range(retry_attempts):
        try:
            webbrowser.open(url)
            break
        except Exception as err:
            logger.error(
                "Failed to download the TCX file from Strava. Attempt %d/%d", attempt + 1, retry_attempts)
            if attempt < retry_attempts - 1:
                time.sleep(2 ** attempt)
            else:
                raise ValueError("Error opening the browser") from err


def get_latest_download() -> str:
    download_folder = os.path.expanduser("~/Downloads")
    try:
        files = os.listdir(download_folder)
    except FileNotFoundError:
        files = []
    paths = [os.path.join(download_folder, f)
             for f in files if f.endswith('.tcx')]

    if paths:
        latest_file = max(paths, key=os.path.getmtime)
    else:
        logger.error("No TCX file found in the Downloads folder.")
        latest_file = ask_file_path("Download")

    return latest_file


def ask_file_path(file_location: str) -> str:
    if file_location == "Provide path":
        question = "Enter the path to the TCX file:"
    else:
        question = "Check if the TCX was downloaded and validate the file:"

    return questionary.path(
        question,
        validate=validation,
        only_directories=False
    ).ask()


def validation(path: str) -> bool:
    return os.path.isfile(path)


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


def validate_tcx_file(file_path: str) -> Tuple[bool, TCXReader]:
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
        return True, data
    except Exception as err:
        logger.error("Invalid TCX file.")
        raise ValueError(f"Error reading the TCX file: {err}") from err


def ask_llm_analysis() -> str:
    return questionary.confirm(
        "Do you want to perform AI analysis?",
        default=False
    ).ask()


def ask_training_plan() -> str:
    return questionary.text(
        "Was there anything planned for this training?"
    ).ask()


def perform_llm_analysis(data: TCXReader, sport: str, plan: str) -> str:
    dataframe = preprocess_trackpoints_data(data)

    prompt_template = """
    SYSTEM: You are an AI coach helping athletes optimize and improve their performance. 
    Based on the provided {sport} training session data, perform the following analysis:

    1. Identify key performance metrics.
    2. Highlight the athlete's strengths during the session.
    3. Pinpoint areas where the athlete can improve.
    4. Offer actionable suggestions for enhancing performance in future {sport} sessions.

    Training session data:
    {training_data}
    """

    if plan:
        prompt_template += "\nTraining plan details: {plan}"

    prompt = PromptTemplate.from_template(prompt_template).format(
        sport=sport,
        training_data=dataframe.to_csv(index=False),
        plan=plan
    )

    openai_llm = ChatOpenAI(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model_name="gpt-4o",
        max_tokens=1500,
        temperature=0.6,
        max_retries=5
    )
    response = openai_llm.invoke(prompt)
    logger.info("AI analysis completed successfully.")
    logger.info("\nAI response:\n %s \n", response.content)
    return response.content


def preprocess_trackpoints_data(data):
    dataframe = pd.DataFrame(data.trackpoints_to_dict())
    dataframe.rename(
        columns={
            "distance": "Distance_Km",
            "time": "Time",
            "Speed": "Speed_Kmh"
        }, inplace=True
    )
    dataframe["Time"] = dataframe["Time"].apply(lambda x: x.value / 10**9)
    dataframe["Distance_Km"] = round(dataframe["Distance_Km"] / 1000, 2)
    dataframe["Speed_Kmh"] = dataframe["Speed_Kmh"] * 3.6
    dataframe["Pace"] = round(
        dataframe["Speed_Kmh"].apply(lambda x: 60 / x if x > 0 else 0),
        2
    )
    dataframe = remove_null_columns(dataframe)

    dataframe = dataframe.drop_duplicates()
    dataframe = dataframe.reset_index(drop=True)
    dataframe = dataframe.dropna(subset=["Speed_Kmh", "Pace", "Distance_Km"])

    if dataframe.shape[0] > 4000:
        dataframe = run_euclidean_dist_deletion(dataframe, 0.55)
    elif dataframe.shape[0] > 1000:
        dataframe = run_euclidean_dist_deletion(dataframe, 0.35)
    else:
        dataframe = run_euclidean_dist_deletion(dataframe, 0.10)

    dataframe["Time"] = pd.to_datetime(
        dataframe["Time"],
        unit='s'
    ).dt.strftime('%H:%M:%S')

    return dataframe


def remove_null_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    columns_to_check = ["cadence", "hr_value", "latitude", "longitude"]
    threshold = len(dataframe) / 2

    for column in columns_to_check:
        if column in dataframe.columns and dataframe[column].isnull().sum() >= threshold:
            if column in ["latitude", "longitude"]:
                dataframe.drop(
                    columns=["latitude", "longitude"],
                    inplace=True,
                    errors='ignore'
                )
                break
            dataframe.drop(columns=[column], inplace=True, errors='ignore')

    return dataframe


def run_euclidean_dist_deletion(dataframe: pd.DataFrame, percentage: float) -> pd.DataFrame:
    dists = pdist(dataframe, metric='euclidean')
    dists = squareform(dists)
    np.fill_diagonal(dists, np.inf)

    total_rows = int(percentage * len(dataframe))
    with tqdm(total=total_rows, desc="Removing similar points") as pbar:
        for _ in range(total_rows):
            min_idx = np.argmin(dists)
            row, col = np.unravel_index(min_idx, dists.shape)
            dists[row, :] = np.inf
            dists[:, col] = np.inf
            dataframe = dataframe.drop(row)
            pbar.update(1)

    dataframe = dataframe.reset_index(drop=True)
    return dataframe


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
