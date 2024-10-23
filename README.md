# Strava to TrainingPeaks

![strava-to-tp-logo](https://raw.githubusercontent.com/Lucs1590/strava-to-trainingpeaks/master/assets/strava_tp_low.png)

[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=Sync%20your%20strava%20trainings%20with%20Traning%20Peaks&url=https://github.com/Lucs1590/strava-to-trainingpeaks&hashtags=strava,github,opensource,strava,dev)
[![codecov](https://codecov.io/gh/Lucs1590/strava-to-trainingpeaks/graph/badge.svg?token=V7BM0ZNAXS)](https://codecov.io/gh/Lucs1590/strava-to-trainingpeaks)
[![Python Coverage](https://github.com/Lucs1590/strava-to-trainingpeaks/actions/workflows/coverage.yml/badge.svg)](https://github.com/Lucs1590/strava-to-trainingpeaks/actions/workflows/coverage.yml)
[![CodeFactor](https://www.codefactor.io/repository/github/lucs1590/strava-to-trainingpeaks/badge)](https://www.codefactor.io/repository/github/lucs1590/strava-to-trainingpeaks)

This script simplifies the process of downloading activities from [Strava](https://www.strava.com/) and uploading them to [TrainingPeaks](https://www.trainingpeaks.com/) in assisted mode.

## How it works

The idea for this script came from the need to synchronize my triathlon training data from my Samsung Watch to TrainingPeaks, a platform not directly compatible with my watch. The script streamlines this process by leveraging Strava as an intermediary.

### Features

- Downloads activities from Strava based on activity IDs.
- Assisted mode for choosing the sport and activity download/upload options.
- Formats TCX files for specific sports like swimming.
- Validates TCX files for running and biking activities.

[Watch the video guide on exporting from Strava to TrainingPeaks manually](https://www.youtube.com/watch?v=Y0nWzOAM8_M)

### Workflow

1. Choose the sport you want to export;
2. Do you want to download the `.tcx` file or select from the local directory;
    1. User chooses the ID of the activity on Strava;
    2. The download is performed by accessing the activity route with `/export_original` or `/export_tcx` endpoints;
3. If it is swimming or something else, the `.tcx` file is formatted; if it is running or biking, the `.tcx` file is validated;
4. Indent the `.tcx` file.

## Installation

### Prerequisites

1. Python 3.6 or higher installed;
2. Pip installed;
3. Logged into your Strava account in your preferred browser.

### Steps

1. Clone the repository;

```bash
git clone https://github.com/Lucs1590/strava-to-trainingpeaks
```

2. Navigate to the project directory:

```bash
cd strava-to-trainingpeaks
```

3. Install the dependencies;

```bash
pip install -r requirements.txt
```

4. Install the package;

```bash
pip install .
```

5. Run the script;

```bash
strava-to-trainingpeaks
```

## Usage

Follow the on-screen instructions after running the script. You'll be prompted to choose the sport, select activity download options, and provide the file path if necessary.

### Example Usage

[![asciicast](https://asciinema.org/a/YtCDwQMThtlfgerhir12YA4Kb.svg)](https://asciinema.org/a/YtCDwQMThtlfgerhir12YA4Kb)

## Common Issues and Solutions

### Issue: No TCX file found in the Downloads folder

**Solution**: Ensure that the TCX file has been downloaded correctly. If not, manually download the TCX file from Strava and provide the file path when prompted.

### Issue: Invalid TCX file

**Solution**: Verify that the TCX file is not corrupted and is in the correct format. If the issue persists, try downloading the TCX file again from Strava.

### Issue: AI analysis not working

**Solution**: Ensure that you have set up the OpenAI API key correctly in your environment variables. If the issue persists, check the logs for more details.

## Additional Examples and Scenarios

### Example 1: Exporting a Running Activity

1. Run the script using the command `strava-to-trainingpeaks`.
2. Select "Run" as the sport.
3. Choose to download the TCX file from Strava.
4. Enter the Strava activity ID.
5. The script will download, validate, and process the TCX file for the running activity.

### Example 2: Exporting a Swimming Activity

1. Run the script using the command `strava-to-trainingpeaks`.
2. Select "Swim" as the sport.
3. Choose to download the TCX file from Strava.
4. Enter the Strava activity ID.
5. The script will download and format the TCX file for the swimming activity.

### Example 3: Resetting the Configuration

1. Run the script using the command `strava-to-trainingpeaks --reset-config`.
2. The script will reset the configuration to default settings.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Lucs1590/strava-to-trainingpeaks/blob/main/LICENSE) file for details.

## Contributing

1. Fork the repository.
2. Create a new branch for your feature (`git checkout -b my-feature`).
3. Commit your changes (`git commit -m 'feat: My new feature'`).
4. Push to the branch (`git push origin my-feature`).
5. Create a new Pull Request.
