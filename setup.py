import os
import re
from pathlib import Path
from setuptools import setup, find_packages


def read(file_name):
    with open(
        os.path.join(
            Path(os.path.dirname(__file__)),
            file_name)
    ) as _file:
        return _file.read()


setup(
    name="strava-to-trainingpeaks",
    version=re.findall(
        re.compile(r'[0-9]+\.[0-9]+\.[0-9]+'),
        read('__version__.py')
    )[0],
    author="Lucas de Brito Silva",
    author_email="lucasbsilva29@gmail.com",
    description="A tool to sync Strava activities with TrainingPeaks, with the OpenAI API creating the workout descriptions.",
    packages=find_packages(),
    install_requires=[
        "defusedxml==0.7.1",
        "langchain_openai==1.1.6",
        "langchain_core==1.2.7",
        "numpy==2.4.1",
        "openai==2.14.0",
        "pandas==2.3.3",
        "python-dotenv==1.2.1",
        "questionary==2.1.1",
        "requests",
        "scipy==1.17.0",
        "tcxreader==0.4.11",
        "tqdm==4.67.1"
    ],
    entry_points={
        "console_scripts": [
            "strava-to-trainingpeaks=src.main:main",
            "strava-coach-mode=src.coach_sync:coach_mode_main",
        ],
    },
)
