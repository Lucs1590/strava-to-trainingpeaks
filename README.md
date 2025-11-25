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
- Indents TCX files for better readability.

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

4. Install the package globally;

```bash
pip install .
```

5. Run the project globally;

```bash
strava-to-trainingpeaks
```

## Usage

Follow the on-screen instructions after running the script. You'll be prompted to choose the sport, select activity download options, and provide the file path if necessary.

### Example Usage

[![asciicast](https://asciinema.org/a/YtCDwQMThtlfgerhir12YA4Kb.svg)](https://asciinema.org/a/YtCDwQMThtlfgerhir12YA4Kb)

## Packaging the Application into an Executable

To package the application into an executable using `cx_Freeze`, follow step:

1. Run the following command to create an executable:

```bash
python exec_setup.py build
```

The executable will be created in the `build` directory.

## Running the Project using Docker

To run the project using Docker, follow these steps:

1. Build the Docker image by running the following command in the root directory of the project:

```bash
docker build -t strava-to-trainingpeaks .
```

2. Run the Docker container using the following command:

```bash
docker run -it --rm strava-to-trainingpeaks
```

This will create a Docker container for the project, allowing it to be run in a consistent environment without manual setup.

## Using the Interactive Setup Script

To use the interactive setup script, follow these steps:

1. Run the interactive setup script:

```bash
python interactive_setup.py
```

2. Follow the on-screen instructions to choose your preferred setup method (global installation, virtual environment, Docker).

3. The script will guide you through the installation process, automate virtual environment creation, and install dependencies.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/Lucs1590/strava-to-trainingpeaks/blob/main/LICENSE) file for details.

## Coach Mode (Multi-Athlete Sync)

Coach Mode allows coaches to sync Strava activities for multiple athletes without requiring each athlete to run any code locally.

### Quick Start

1. Set up Strava OAuth credentials (see [docs/coach_mode.md](docs/coach_mode.md))
2. Run coach mode:

```bash
strava-coach-mode
```

3. Add athletes via OAuth authorization
4. Sync activities on behalf of your athletes

For detailed setup instructions, see [Coach Mode Documentation](docs/coach_mode.md).

## Contributing

1. Fork the repository.
2. Create a new branch for your feature (`git checkout -b my-feature`).
3. Commit your changes (`git commit -m 'feat: My new feature'`).
4. Push to the branch (`git push origin my-feature`).
5. Create a new Pull Request.
