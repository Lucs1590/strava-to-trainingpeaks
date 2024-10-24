from setuptools import setup, find_packages

setup(
    name='strava-to-trainingpeaks',
    version='0.1.0',
    author='Lucas de Brito Silva',
    description='A script to download activities from Strava and upload them to TrainingPeaks with the bonus of using OpenAI to generate a description for each activity.',
    packages=find_packages(),
    install_requires=[
        'defusedxml==0.7.1',
        'langchain_core==0.3.10',
        'langchain_openai==0.2.2',
        'numpy==1.24.2',
        'pandas==2.2.3',
        'python-dotenv==1.0.1',
        'questionary==2.0.1',
        'scipy==1.13.1',
        'tcxreader==0.4.10',
        'tqdm==4.66.5',
        'setuptools==72.1.0',
    ],
    entry_points={
        'console_scripts': [
            'strava-to-trainingpeaks=src.main:main',
        ],
    },
)
