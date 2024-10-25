import cx_Freeze

cx_Freeze.setup(
    name="strava-to-trainingpeaks",
    version="0.1",
    description="A tool to sync Strava activities with TrainingPeaks, with the OpenAI API creating the workout descriptions.",
    executables=[cx_Freeze.Executable("src/main.py")],
)
