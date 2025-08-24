import re
import os
import time
import logging
import webbrowser

from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

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


class Sport(Enum):
    """Supported sports enumeration."""
    BIKE = "Bike"
    RUN = "Run"
    SWIM = "Swim"
    OTHER = "Other"


@dataclass
class AnalysisConfig:
    """Configuration for LLM analysis."""
    training_plan: str
    language: str = "Portuguese (Brazil)"


@dataclass
class ProcessingConfig:
    """Configuration for data processing."""
    euclidean_threshold_large: float = 0.55  # > 4000 rows
    euclidean_threshold_medium: float = 0.35  # > 1000 rows
    euclidean_threshold_small: float = 0.10   # <= 1000 rows
    large_dataset_threshold: int = 4000
    medium_dataset_threshold: int = 1000


class TCXProcessor:
    def __init__(self):
        load_dotenv()
        self.logger = setup_logging()
        self.config = ProcessingConfig()
        self.sport: Optional[Sport] = None

    def run(self) -> None:
        """Main execution flow."""
        try:
            self.sport = self._get_sport_selection()
            self.logger.info("Selected sport: %s", self.sport.value)

            file_path = self._get_tcx_file_path()
            if not file_path:
                self.logger.error("No valid file path provided")
                return

            self._process_by_sport(file_path)
            self._format_xml_file(file_path)

            self.logger.info("Process completed successfully!")

        except Exception as err:
            self.logger.error("Process failed: %s", str(err))
            raise Exception("An error occurred during processing") from err

    def _get_sport_selection(self) -> Sport:
        """Get sport selection from user."""
        sport_choice = questionary.select(
            "Which sport do you want to export to TrainingPeaks?",
            choices=[sport.value for sport in Sport]
        ).ask()

        return Sport(sport_choice)

    def _get_tcx_file_path(self) -> Optional[str]:
        """Get TCX file path from user input or download."""
        file_location = questionary.select(
            "Do you want to download the TCX file from Strava or provide the file path?",
            choices=["Download", "Provide path"]
        ).ask()

        if file_location == "Download":
            return self._handle_download_flow()
        return self._get_file_path_from_user()

    def _handle_download_flow(self) -> Optional[str]:
        """Handle Strava download flow."""
        activity_id = self._get_activity_id()

        self.logger.info("Selected activity ID: %s", activity_id)
        self.logger.info("Downloading the TCX file from Strava")

        self._download_tcx_file(activity_id)
        time.sleep(3)

        file_path = self._get_latest_download()
        self.logger.info(
            "Automatically detected downloaded file path: %s", file_path
        )

        return file_path

    def _get_activity_id(self) -> str:
        """Get and validate Strava activity ID."""
        activity_id = questionary.text(
            "Enter the Strava activity ID you want to export to TrainingPeaks:"
        ).ask()

        clean_id = re.sub(r"\D", "", activity_id)
        if not clean_id:
            raise ValueError("Invalid activity ID provided")

        return clean_id

    def _download_tcx_file(self, activity_id: str) -> None:
        """Download TCX file from Strava."""
        export_type = 'original' if self.sport in [
            Sport.SWIM, Sport.OTHER] else 'tcx'
        url = f"https://www.strava.com/activities/{activity_id}/export_{export_type}"

        try:
            webbrowser.open(url)
        except Exception as err:
            self.logger.error("Failed to download the TCX file from Strava")
            raise ValueError("Error opening the browser") from err

    def _get_latest_download(self) -> str:
        """Get the latest TCX file from Downloads folder."""
        download_folder = Path.home() / "Downloads"

        try:
            tcx_files = list(download_folder.glob("*.tcx"))
        except Exception:
            tcx_files = []

        if tcx_files:
            latest_file = max(tcx_files, key=lambda f: f.stat().st_mtime)
            return str(latest_file)
        self.logger.warning("No TCX file found in Downloads folder")
        return self._get_file_path_from_user()

    def _get_file_path_from_user(self) -> str:
        """Get file path from user input with validation."""
        return questionary.path(
            "Enter the path to the TCX file:",
            validate=lambda path: Path(path).is_file(),
            only_directories=False
        ).ask()

    def _process_by_sport(self, file_path: str) -> None:
        """Process TCX file based on sport type."""
        if self.sport in [Sport.SWIM, Sport.OTHER]:
            self.logger.info(
                "Formatting the TCX file for TrainingPeaks import"
            )
            self._format_swim_tcx(file_path)

        elif self.sport in [Sport.BIKE, Sport.RUN]:
            self.logger.info("Validating the TCX file")
            is_valid, tcx_data = self._validate_tcx_file(file_path)

            if not is_valid:
                raise ValueError("Invalid TCX file")

            if self._should_perform_ai_analysis():
                self._perform_ai_analysis(tcx_data, self.sport)
        else:
            raise ValueError(f"Unsupported sport: {self.sport}")

    def _format_swim_tcx(self, file_path: str) -> None:
        """Format TCX file for swimming activities."""
        xml_content = self._read_xml_file(file_path)

        # Modify XML header
        xml_content = xml_content.replace(
            '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">',
            '<TrainingCenterDatabase xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">'
        )

        xml_content = re.sub(r"<Value>(\d+)\.0</Value>",
                             r"<Value>\1</Value>", xml_content)
        xml_content = re.sub(r'<Activity Sport="Swim">',
                             r'<Activity Sport="Other">', xml_content)

        self._write_xml_file(file_path, xml_content)

    def _read_xml_file(self, file_path: str) -> str:
        """Read XML file content."""
        try:
            with open(file_path, "r", encoding='utf-8') as xml_file:
                return xml_file.read()
        except Exception as err:
            self.logger.error("Failed to read XML file: %s", str(err))
            raise

    def _write_xml_file(self, file_path: str, content: str) -> None:
        """Write content to XML file."""
        try:
            with open(file_path, "w", encoding='utf-8') as xml_file:
                xml_file.write(content)
        except Exception as err:
            self.logger.error("Failed to write XML file: %s", str(err))
            raise

    def _validate_tcx_file(self, file_path: str) -> Tuple[bool, Optional[TCXReader]]:
        """Validate TCX file and return reader if valid."""
        xml_content = self._read_xml_file(file_path)
        if not xml_content.strip():
            self.logger.error("The TCX file is empty")
            return False, None

        tcx_reader = TCXReader()
        try:
            data = tcx_reader.read(file_path)
            self.logger.info(
                "TCX file is valid. Distance covered: %d meters",
                data.distance
            )
            return True, data
        except Exception as err:
            self.logger.error("Invalid TCX file: %s", str(err))
            return False, None

    def _should_perform_ai_analysis(self) -> bool:
        """Ask user if they want AI analysis."""
        return questionary.confirm(
            "Do you want to perform AI analysis?",
            default=False
        ).ask()

    def _perform_ai_analysis(self, tcx_data: TCXReader, sport: Sport) -> None:
        """Perform AI analysis on TCX data."""
        self._ensure_openai_key()

        analysis_config = AnalysisConfig(
            training_plan=questionary.text(
                "Was there anything planned for this training?"
            ).ask() or "",
            language=questionary.text(
                "In which language do you want the analysis? (Default: Portuguese)",
                default="Portuguese (Brazil)"
            ).ask()
        )

        self.logger.info("Performing AI analysis")
        analysis_result = self._analyze_with_llm(
            tcx_data,
            sport,
            analysis_config
        )
        self.logger.info("AI analysis completed successfully")
        self.logger.info("AI response:\n%s", analysis_result)

    def _ensure_openai_key(self) -> None:
        """Ensure OpenAI API key is available."""
        if not os.getenv("OPENAI_API_KEY"):
            api_key = questionary.password("Enter your OpenAI API key:").ask()

            with open(".env", "w", encoding="utf-8") as env_file:
                env_file.write(f"OPENAI_API_KEY={api_key}")

            load_dotenv()
            self.logger.info("OpenAI API key loaded successfully")

    def _analyze_with_llm(self, tcx_data: TCXReader, sport: Sport, config: AnalysisConfig) -> str:
        """Analyze training data using LLM."""
        processed_data = self._preprocess_trackpoints(tcx_data)

        prompt_template = self._get_analysis_prompt_template(
            config.training_plan
        )
        prompt = PromptTemplate.from_template(prompt_template).format(
            sport=sport.value,
            training_data=processed_data.to_csv(index=False),
            language=config.language,
            plan=config.training_plan
        )

        llm = ChatOpenAI(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model_name="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.6,
            max_retries=5
        )

        response = llm.invoke(prompt)
        return response.content

    def _get_analysis_prompt_template(self, has_plan: bool) -> str:
        """Get the prompt template for analysis."""
        base_template = """
You are an expert AI performance coach specializing in sports science, physiology, and training methodology.
Begin with a concise checklist (3-7 bullets) of your analysis process before delivering the final output; keep items conceptual, not implementation-level.
Analyze the provided training session data for the specified {sport} and deliver a comprehensive performance report in the requested {language}.

# Required Analysis Sections

## 1. Session Overview
- Summarize key characteristics and the session's training type.
- Assess total training load and intensity distribution.
- Identify the primary training stimulus.

## 2. Performance Metrics
- **Pace/Speed:** Include averages, consistency, and variability.
- **Heart Rate Zones** (if available): Show distribution and cardiovascular efficiency.
- **Power Output** (if available): Present normalized power and efficiency metrics.
- **Cadence** (if available): Analyze consistency and suggest optimization opportunities.

## 3. Physiological Analysis
- Evaluate cardiovascular patterns and efficiency.
- Discuss energy system usage (aerobic vs. anaerobic).
- Analyze fatigue progression and pacing effectiveness.
- Assess within-session recovery patterns.

## 4. Performance Strengths
- Highlight the strongest aspects with supporting metrics.
- Identify best-performing segments.
- Indicate consistency and signs of improvement.

## 5. Critical Improvement Areas
- Identify specific weaknesses with data-based evidence.
- Highlight inconsistencies, pacing inefficiency, technical gaps, and physiological limiters.

## 6. Detailed Improvement Strategies
- List actionable technical improvements, including drills, form corrections, and equipment suggestions.
- Recommend training adaptations—workout types, intensity/volume/frequency adjustments, and progressive overload.
- Suggest physiological development priorities.

## 7. Immediate Action Plan
- Create a prioritized improvement roadmap.
- Set focus, targets, and modifications for the next 1-2 sessions.
- Outline a 2-4 week plan (benchmarks, adaptations).
- Provide a technique development protocol (steps, practice frequency, progress tracking, common errors).

## 8. Performance Optimization
- Identify warning signs or major improvement opportunities.
- Suggest efficiency improvements and advanced strategies for breakthroughs.

# Response Guidelines
- Support recommendations with data from the session wherever possible.
- Use exact numbers (e.g., times, distances, percentages, heart rates) when available.
- Prioritize actionable, impactful improvements.
- Structure recommendations by timeline.
- Be direct and specific, not motivational.

## Training Session Data
{training_data}"""

        if has_plan:
            base_template += """

## Training Plan Execution Analysis
- Compare actual performance to planned objectives using specific metrics.
- Assess execution quality and suggest adjustments for future sessions.
- Recommend optimizations based on the difference between actual and planned results.

Planned Training Details:
{plan}
"""

        return base_template

    def _preprocess_trackpoints(self, tcx_data: TCXReader) -> pd.DataFrame:
        """Preprocess trackpoints data for analysis."""
        processor = TrackpointProcessor(self.config)
        return processor.process(tcx_data)

    def _format_xml_file(self, file_path: str) -> None:
        """Format XML file with proper indentation."""
        try:
            xml_content = self._read_xml_file(file_path)
            xml_dom = parseString(xml_content)
            formatted_xml = xml_dom.toprettyxml(indent="  ")
            self._write_xml_file(file_path, formatted_xml)
        except Exception as err:
            self.logger.warning(
                "Failed to format XML file: %s. File saved without formatting.",
                str(err)
            )


class TrackpointProcessor:
    """Processor for trackpoint data preprocessing."""

    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = setup_logging()

    def process(self, tcx_data: TCXReader) -> pd.DataFrame:
        """Process trackpoints data."""
        df = self._create_dataframe(tcx_data)
        df = self._clean_and_transform(df)
        df = self._reduce_data_size(df)
        df = self._format_time_column(df)

        return df

    def _create_dataframe(self, tcx_data: TCXReader) -> pd.DataFrame:
        """Create initial dataframe from TCX data."""
        df = pd.DataFrame(tcx_data.trackpoints_to_dict())

        # Rename columns for clarity
        column_mapping = {
            "distance": "Distance_Km",
            "time": "Time",
            "Speed": "Speed_Kmh"
        }
        df.rename(columns=column_mapping, inplace=True)

        return df

    def _clean_and_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and transform the dataframe."""
        df["Time"] = df["Time"].apply(lambda x: x.value / 10**9)
        df["Distance_Km"] = round(df["Distance_Km"] / 1000, 2)
        df["Speed_Kmh"] = df["Speed_Kmh"] * 3.6
        df["Pace"] = round(
            df["Speed_Kmh"].apply(lambda x: 60 / x if x > 0 else 0),
            2
        )

        df = self._remove_sparse_columns(df)

        df = df.drop_duplicates().reset_index(drop=True)
        df = df.dropna(subset=["Speed_Kmh", "Pace", "Distance_Km"])

        return df

    def _remove_sparse_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove columns with too many null values."""
        columns_to_check = ["cadence", "hr_value", "latitude", "longitude"]
        threshold = len(df) / 2

        for column in columns_to_check:
            if column in df.columns and df[column].isnull().sum() >= threshold:
                if column in ["latitude", "longitude"]:
                    df.drop(
                        columns=["latitude", "longitude"],
                        inplace=True,
                        errors='ignore'
                    )
                df.drop(columns=[column], inplace=True, errors='ignore')

        return df

    def _reduce_data_size(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reduce data size using euclidean distance filtering."""
        row_count = len(df)

        if row_count > self.config.large_dataset_threshold:
            threshold = self.config.euclidean_threshold_large
        elif row_count > self.config.medium_dataset_threshold:
            threshold = self.config.euclidean_threshold_medium
        else:
            threshold = self.config.euclidean_threshold_small

        return self._apply_euclidean_filtering(df, threshold)

    def _apply_euclidean_filtering(self, df: pd.DataFrame, percentage: float) -> pd.DataFrame:
        """Apply euclidean distance filtering to reduce similar points."""
        if len(df) < 50:
            return df

        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            return df

        try:
            distances = pdist(numeric_df, metric='euclidean')
            distance_matrix = squareform(distances)
            np.fill_diagonal(distance_matrix, np.inf)

            rows_to_remove = int(percentage * len(df))
            indices_to_drop = set()

            with tqdm(total=rows_to_remove, desc="Filtering similar points") as pbar:
                for _ in range(rows_to_remove):
                    if len(indices_to_drop) >= len(df) - 10:
                        break

                    min_idx = np.argmin(distance_matrix)
                    row, col = np.unravel_index(min_idx, distance_matrix.shape)

                    if row not in indices_to_drop and col not in indices_to_drop:
                        indices_to_drop.add(row)
                        distance_matrix[row, :] = np.inf
                        distance_matrix[:, row] = np.inf
                        pbar.update(1)

            df = df.drop(index=list(indices_to_drop)).reset_index(drop=True)

        except Exception as err:
            self.logger.warning(
                "Failed to apply euclidean filtering: %s",
                str(err)
            )

        return df

    def _format_time_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format time column to HH:MM:SS."""
        df["Time"] = pd.to_datetime(
            df["Time"],
            unit='s'
        ).dt.strftime('%H:%M:%S')
        return df


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)

    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
        handler = logging.FileHandler('tcx_processor.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def main():
    processor = TCXProcessor()
    processor.run()


if __name__ == "__main__":
    main()
