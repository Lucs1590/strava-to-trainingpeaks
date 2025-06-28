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
        self.langchain_agent = create_openai_functions_agent(
            llm=ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY")),
            functions=[
                self.get_workouts_from_strava,
                self.push_workouts_to_trainingpeaks
            ]
        )

    def get_workouts_from_strava(self, start_date, end_date):
        url = f"{self.base_strava_url}/athlete/activities"
        headers = {"Authorization": f"Bearer {self.strava_api_key}"}
        params = {
            "before": int(end_date.timestamp()),
            "after": int(start_date.timestamp()),
            "per_page": 200
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        self.logger.error(
            f"Failed to retrieve workouts from Strava: {response.status_code}"
        )
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

    def sync_workouts_for_week(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        workouts = self.get_workouts_from_strava(
            start_date,
            end_date
        )
        if workouts:
            self.push_workouts_to_trainingpeaks(workouts)
        else:
            self.logger.info("No workouts to sync for the past week.")

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

    def schedule_weekly_sync(self):
        schedule.every().week.do(self.sync_workouts_for_week)
        while True:
            schedule.run_pending()
            time.sleep(1)