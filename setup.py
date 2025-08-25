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
        "langchain_core==0.3.74",
        "langchain_openai==0.3.30",
        "numpy==2.0.2",
        "pandas==2.3.1",
        "python-dotenv==1.1.1",
        "questionary==2.1.0",
        "scipy==1.15.2",
        "tcxreader==0.4.11",
        "tqdm==4.67.1",
        "httpx==0.28.1"
    ],
    entry_points={
        "console_scripts": [
            "strava-to-trainingpeaks=src.main:main",
            "strava-mcp=src.mcp_cli:main",
            "strava-mcp-server=src.mcp_server_main:main",
        ],
    },
)
