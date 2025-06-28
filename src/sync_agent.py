import os
import time
import logging

from datetime import datetime, timedelta

import schedule
import requests

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from langchain.agents import create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

load_dotenv()


class SyncAgent:
    def __init__(self):
        self.strava_api_key = os.getenv("STRAVA_API_KEY")
        self.trainingpeaks_username = os.getenv("TRAININGPEAKS_USERNAME")
        self.trainingpeaks_password = os.getenv("TRAININGPEAKS_PASSWORD")
        self.base_strava_url = "https://www.strava.com/api/v3"
        self.logger = logging.getLogger("SyncAgent")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler('sync_agent.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        # Initialize LangChain agent for intelligent workout syncing
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            self.logger.warning(
                "OpenAI API key not found. LangChain agent will not be available.")
            self.langchain_agent = None
        else:
            try:
                prompt = PromptTemplate(
                    input_variables=["start_date", "end_date", "user_input"],
                    template=(
                        "You are a helpful assistant that can interact with Strava and TrainingPeaks. "
                        "You can retrieve workouts from Strava and push them to TrainingPeaks. "
                        "Use the following tools:\n"
                        "- get_workouts_from_strava(start_date, end_date): Retrieve workouts from Strava between the specified dates.\n"
                        "- push_workouts_to_trainingpeaks(workouts): Push the provided workouts to TrainingPeaks.\n"
                        "Make sure to handle any errors gracefully and log the results.\n\n"
                        "User request: {user_input}\n"
                        "Date range: {start_date} to {end_date}"
                    )
                )

                self.langchain_agent = create_openai_functions_agent(
                    llm=ChatOpenAI(api_key=self.openai_api_key, temperature=0),
                    tools=[],  # Tools should be defined separately as LangChain Tool objects
                    prompt=prompt
                )
                self.logger.info("LangChain agent initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize LangChain agent: {e}")
                self.langchain_agent = None

    def get_workouts_from_strava(self, athlete_id, start_date, end_date):
        """
        Retrieve workouts from Strava for a given athlete and date range.
        """
        url = f"{self.strava_base_url}/athlete/{athlete_id}/activities"
        params = {
            "after": int(start_date.timestamp()),
            "before": int(end_date.timestamp()),
        }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            return []

    def push_workouts_to_trainingpeaks(self, workouts):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
        driver.get("https://home.trainingpeaks.com/login")

        # Login to TrainingPeaks
        driver.find_element(By.ID, "username").send_keys(
            self.trainingpeaks_username
        )
        driver.find_element(By.ID, "password").send_keys(
            self.trainingpeaks_password
        )
        driver.find_element(By.ID, "login-button").click()
        time.sleep(5)  # Wait for login to complete

        for workout in workouts:
            driver.get("https://app.trainingpeaks.com/#calendar")
            time.sleep(3)  # Wait for the page to load

            # Upload the TCX file
            tcx_file_path = workout["tcx_file_path"]
            upload_element = driver.find_element(By.ID, "upload-button")
            upload_element.send_keys(tcx_file_path)
            time.sleep(2)  # Wait for the upload to complete

            self.logger.info(
                f"Successfully pushed workout to TrainingPeaks: {workout['id']}"
            )

        driver.quit()

    def sync_workouts_for_week(self, athlete_id):
        """
        Sync workouts for the current week.
        """
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        workouts = self.get_workouts_from_strava(
            athlete_id, start_date, end_date)
        if workouts:
            self.push_workouts_to_trainingpeaks(workouts)

    def handle_api_rate_limits(self, func, *args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error("Max retries reached. Giving up.")
                    return None
        return None

    def schedule_weekly_sync(self, athlete_id):
        """
        Schedule weekly synchronization of workouts.
        """
        schedule.every().week.do(self.sync_workouts_for_week, athlete_id)

        while True:
            schedule.run_pending()
            time.sleep(60)
