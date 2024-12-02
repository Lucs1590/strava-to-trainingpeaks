from setuptools import setup, find_packages
setup(
    name="strava-to-trainingpeaks",
    version="1.0.0",
    author="Lucas de Brito Silva",
    author_email="lucasbsilva29@gmail.com",
    description="A tool to sync Strava activities with TrainingPeaks, with the OpenAI API creating the workout descriptions.",
    packages=find_packages(),
    install_requires=[
        "defusedxml==0.7.1",
            "langchain_core==0.3.21",
            "langchain_openai==0.2.10",
            "numpy==1.26.4",
            "pandas==2.2.3",
            "python-dotenv==1.0.1",
            "questionary==2.0.1",
            "scipy==1.13.1",
            "tcxreader==0.4.10",
            "tqdm==4.67.1"
    ],
    entry_points={
        "console_scripts": [
            "strava-to-trainingpeaks=src.main:main",
        ],
    },
)
