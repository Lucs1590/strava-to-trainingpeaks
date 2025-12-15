# Strava to TrainingPeaks

![strava-to-tp-logo](https://raw.githubusercontent.com/Lucs1590/strava-to-trainingpeaks/master/assets/strava_tp_low.png)

[![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=Sync%20your%20strava%20trainings%20with%20Traning%20Peaks&url=https://github.com/Lucs1590/strava-to-trainingpeaks&hashtags=strava,github,opensource,strava,dev)
[![codecov](https://codecov.io/gh/Lucs1590/strava-to-trainingpeaks/graph/badge.svg?token=V7BM0ZNAXS)](https://codecov.io/gh/Lucs1590/strava-to-trainingpeaks)
[![Python Coverage](https://github.com/Lucs1590/strava-to-trainingpeaks/actions/workflows/coverage.yml/badge.svg)](https://github.com/Lucs1590/strava-to-trainingpeaks/actions/workflows/coverage.yml)
[![CodeFactor](https://www.codefactor.io/repository/github/lucs1590/strava-to-trainingpeaks/badge)](https://www.codefactor.io/repository/github/lucs1590/strava-to-trainingpeaks)

A powerful tool that simplifies downloading activities from [Strava](https://www.strava.com/) and uploading them to [TrainingPeaks](https://www.trainingpeaks.com/), with optional **AI-powered training analysis** and **multi-athlete coach mode**.

## Overview

Originally created to sync triathlon training data from Samsung Watch to TrainingPeaks (via Strava as an intermediary), this tool has evolved to include:

- **Personal Mode**: Individual athletes can download and process their own activities
- **Coach Mode**: Coaches can manage and sync activities for multiple athletes via OAuth
- **AI Analysis**: Optional LLM-powered training insights and performance feedback
- **Audio Summaries**: Generate spoken analysis of your training sessions

## Features

### Core Functionality
- 🏃 Download activities from Strava (running, cycling, swimming, and more)
- 📊 Format TCX files for TrainingPeaks compatibility
- ✅ Validate and optimize TCX data for different sports
- 🎯 Interactive CLI with guided workflows

### AI-Powered Analysis
- 🤖 Intelligent training analysis using OpenAI's GPT models
- 📈 Performance metrics evaluation (pace, heart rate, power, cadence)
- 💪 Identify strengths and areas for improvement
- 🎧 Generate audio summaries of your training sessions

### Coach Mode (OAuth)
- 👥 Manage multiple athletes from a single interface
- 🔐 Secure OAuth 2.0 authorization
- 🔄 Automatic token refresh
- 📥 Batch download activities for your athletes

## Documentation

For detailed guides and tutorials, check out these articles:

- 📝 [Strava to Training Peaks - Setup Guide](https://medium.com/p/fa3a0fa05f79)
- 🤖 [LLM to Strava: Intelligent Training Analysis with AI Co-coaching](https://levelup.gitconnected.com/llm-to-strava-intelligent-training-analysis-with-ai-co-coaching-03f1cf866597)

[Watch the video guide on exporting from Strava to TrainingPeaks manually](https://www.youtube.com/watch?v=Y0nWzOAM8_M)

## Quick Start

### Personal Mode

```bash
# Install the package
pip install .

# Run the interactive CLI
strava-to-trainingpeaks
```

The CLI will guide you through:
1. Selecting your sport (running, cycling, swimming, other)
2. Downloading from Strava or providing a local TCX file
3. Optional AI analysis of your training session
4. Optional audio summary generation
5. Formatted TCX file ready for TrainingPeaks upload

### Coach Mode

```bash
# Set up OAuth credentials (one-time setup)
export STRAVA_CLIENT_ID=your_client_id
export STRAVA_CLIENT_SECRET=your_client_secret

# Run coach mode
strava-coach-mode
```

See [Coach Mode Documentation](docs/coach_mode.md) for complete setup instructions.

## Installation

### Prerequisites

- Python 3.12 or higher
- pip package manager
- Strava account (logged in on your browser for downloads)
- Optional: OpenAI API key (for AI analysis features)

### Standard Installation

```bash
# Clone the repository
git clone https://github.com/Lucs1590/strava-to-trainingpeaks
cd strava-to-trainingpeaks

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install .
```

### Alternative Installation Methods

#### Using Interactive Setup Script

```bash
python interactive_setup.py
```

Follow the prompts to choose between:
- Global installation
- Virtual environment
- Docker container

#### Docker Installation

```bash
# Build the image
docker build -t strava-to-trainingpeaks .

# Run the container
docker run -it --rm strava-to-trainingpeaks
```

## Configuration

### AI Analysis Setup (Optional)

To enable AI-powered training analysis:

1. Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/)
2. Set the environment variable:

```bash
export OPENAI_API_KEY=your_api_key_here
```

Or create a `.env` file:

```bash
OPENAI_API_KEY=your_api_key_here
```

### Coach Mode Setup

See the [Coach Mode Documentation](docs/coach_mode.md) for detailed OAuth setup instructions.

## Advanced Features

### AI Training Analysis

The tool can analyze your training sessions using advanced language models:

- **Performance Metrics**: Detailed analysis of pace, heart rate zones, power output, and cadence
- **Physiological Analysis**: Insights into cardiovascular efficiency and energy systems
- **Strengths & Weaknesses**: Identify what you're doing well and areas for improvement
- **Training Plan Comparison**: Compare actual performance against planned workouts

Example workflow:
```bash
strava-to-trainingpeaks
# Select sport → Download activity → Enable AI analysis → Answer prompts
```

### Audio Summaries

Generate spoken summaries of your training analysis:

- Uses OpenAI's text-to-speech technology
- Automatically removes markdown formatting
- Saves MP3 files to your Downloads folder
- Perfect for reviewing while cooling down or commuting

### Building an Executable

Package the application into a standalone executable:

```bash
python exec_setup.py build
```

The executable will be created in the `build/` directory.

## How It Works

### Personal Mode Workflow

1. **Sport Selection**: Choose your activity type (running, cycling, swimming, or other)
2. **Data Source**: Download from Strava (by activity ID) or provide a local TCX file
3. **Processing**: The tool formats and validates the TCX file for TrainingPeaks
4. **AI Analysis** (optional): Get detailed performance insights
5. **Audio Summary** (optional): Generate a spoken analysis
6. **Output**: Receive a formatted TCX file ready for TrainingPeaks upload

### Coach Mode Workflow

1. **Setup**: Configure Strava OAuth credentials (one-time)
2. **Athlete Authorization**: Athletes grant access through secure OAuth flow
3. **Manage Athletes**: View all authorized athletes and their token status
4. **Sync Activities**: Download any athlete's activities using their tokens
5. **Batch Processing**: Process multiple athletes' data efficiently

## Resources & Links

### Articles & Tutorials
- 📖 [Strava to Training Peaks - Complete Guide](https://medium.com/p/fa3a0fa05f79)
- 🤖 [AI-Powered Training Analysis with LLM Integration](https://levelup.gitconnected.com/llm-to-strava-intelligent-training-analysis-with-ai-co-coaching-03f1cf866597)
- 🎥 [Video: Manual Export from Strava to TrainingPeaks](https://www.youtube.com/watch?v=Y0nWzOAM8_M)

### Documentation
- [Coach Mode Setup Guide](docs/coach_mode.md)
- [Strava API Documentation](https://developers.strava.com/docs/)
- [TrainingPeaks Import Guide](https://help.trainingpeaks.com/hc/en-us/articles/360014889633-Uploading-Activities)

### Project Information
- **Author**: [Lucas Brito](https://lucasbrito.com.br/)
- **Repository**: [github.com/Lucs1590/strava-to-trainingpeaks](https://github.com/Lucs1590/strava-to-trainingpeaks)
- **License**: MIT License - see [LICENSE](LICENSE) file

## Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m unittest discover -s tests -v

# Run with coverage
pytest --cov --junitxml=junit.xml
```

## Support

If you find this project helpful, please consider:
- ⭐ Starring the repository
- 📢 Sharing it with your training community
- 🐛 Reporting bugs or suggesting features via [Issues](https://github.com/Lucs1590/strava-to-trainingpeaks/issues)
- 💡 Contributing code improvements

## Acknowledgments

Special thanks to the open-source community and all contributors who have helped improve this project.
