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

- Downloads activities from Strava based on activity IDs or via API integration.
- **NEW**: Model Context Protocol (MCP) integration for AI assistant connectivity.
- Assisted mode for choosing the sport and activity download/upload options.
- Formats TCX files for specific sports like swimming.
- Validates TCX files for running and biking activities.
- Indents TCX files for better readability.
- **NEW**: Strava API integration for programmatic access to activities.
- **NEW**: Activity synchronization and analysis through MCP tools.

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

### Environment Configuration (for MCP integration)

For Strava API access and AI analysis features, create a `.env` file in the project root:

```bash
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_ACCESS_TOKEN=your_access_token_here  # Optional, can be obtained via OAuth
STRAVA_REFRESH_TOKEN=your_refresh_token_here  # Optional, can be obtained via OAuth
OPENAI_API_KEY=your_openai_key_here  # For AI analysis features
```

Get Strava API credentials at [Strava Developers](https://developers.strava.com/).

4. Install the package globally;

```bash
pip install .
```

5. Run the project globally;

```bash
strava-to-trainingpeaks
```

## Usage

### Traditional CLI Mode

Follow the on-screen instructions after running the script. You'll be prompted to choose the sport, select activity download options, and provide the file path if necessary.

```bash
python src/main.py
```

### MCP Integration (NEW)

The tool now supports Model Context Protocol (MCP) for AI assistant integration:

```bash
# List available MCP tools
python src/mcp_cli.py list-tools

# List recent activities from Strava API
python src/mcp_cli.py list-activities --limit 10

# Analyze a specific activity with AI
python src/mcp_cli.py analyze-activity --activity-id 12345 --language "English"

# Run interactive MCP server
python src/mcp_server_main.py --interactive
```

For detailed MCP usage, see [MCP_INTEGRATION.md](MCP_INTEGRATION.md).

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

## Contributing

1. Fork the repository.
2. Create a new branch for your feature (`git checkout -b my-feature`).
3. Commit your changes (`git commit -m 'feat: My new feature'`).
4. Push to the branch (`git push origin my-feature`).
5. Create a new Pull Request.
