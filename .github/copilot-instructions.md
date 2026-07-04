# Strava to TrainingPeaks

**CRITICAL**: Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

This repository contains a Python CLI application that downloads activities from Strava, formats TCX files for TrainingPeaks, and supports optional AI-powered analysis and audio summaries. The project now has two user-facing workflows: personal mode and coach mode.

## Environment Setup

### Prerequisites

- Python 3.12 or newer
- pip, kept reasonably up to date
- A Strava account for downloads and coach-mode OAuth
- OpenAI API access only if you want AI analysis or audio summaries

### Quick Start Commands

```bash
# Clone and setup (if starting fresh)
git clone https://github.com/Lucs1590/strava-to-trainingpeaks
cd strava-to-trainingpeaks

# Essential setup
pip install -r requirements.txt
pip install .
python -m unittest discover -s tests -v

# Verify installation
strava-to-trainingpeaks
```

## Working Effectively

Bootstrap, build, and test the repository using these commands:

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install the package:

   ```bash
   pip install .
   ```

3. Run tests:

   ```bash
   python -m unittest discover -s tests -v
   pytest --cov --junitxml=junit.xml -o junit_family=legacy
   ```

   The active suite is split across `tests/test_main.py`, `tests/test_coach_sync.py`, and `tests/test_strava_oauth.py`.

4. Build executable if needed:

   ```bash
   python exec_setup.py build
   ```

## Running the Application

- Personal mode CLI: `strava-to-trainingpeaks`
- Coach mode CLI: `strava-coach-mode`
- Personal mode direct run: `python src/main.py`
- Coach mode direct run: `python src/coach_sync.py`
- Interactive setup: `python interactive_setup.py`

Important prompts and dependencies:

- Personal mode asks for sport, source activity, optional AI analysis, and optional audio summary generation
- Coach mode requires `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET`
- AI features require `OPENAI_API_KEY`

## Validation

After making changes, run these checks in order:

### 1. Automated Testing

```bash
python -m unittest discover -s tests -v
pytest --cov --junitxml=junit.xml -o junit_family=legacy
```

If you are specifically testing OAuth behavior, make sure `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` are set or explicitly cleared so the environment does not change the result unexpectedly.

### 2. Import and Basic Functionality

```bash
python -c "from src.main import TCXProcessor; print('Import successful')"
python -c "from src.strava_oauth import StravaOAuthClient; print('OAuth import successful')"
which strava-to-trainingpeaks
which strava-coach-mode
```

### 3. Manual Validation Scenarios

1. Personal mode launch:

   ```bash
   python src/main.py
   ```

   Expected: the sport selection menu and the personal-mode workflow.

2. Coach mode launch:

   ```bash
   python src/coach_sync.py
   ```

   Expected: the coach-mode menu, or a clear message that OAuth is not configured if the Strava credentials are missing.

3. Installation helper:

   ```bash
   python interactive_setup.py
   ```

   Expected: setup method selection for global install, virtual environment, or Docker.

### 4. Build Validation

```bash
python exec_setup.py build
./build/exe.linux-x86_64-3.12/main
```

### 5. CI/CD Validation

- Tests must pass in CI
- Coverage is enforced in the GitHub Actions workflow
- Do not introduce new linting issues

## Common Tasks

### Testing Different Installation Methods

1. Global installation:

   ```bash
   pip install .
   ```

2. Virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install .
   ```

3. Interactive setup:

   ```bash
   python interactive_setup.py
   ```

4. Docker:

   ```bash
   docker build -t strava-to-trainingpeaks .
   docker run -it --rm strava-to-trainingpeaks
   ```

### Key Files and Directories

- `src/main.py` - Personal mode entry point and `TCXProcessor`
- `src/coach_sync.py` - Coach mode menu and athlete sync workflow
- `src/strava_oauth.py` - Strava OAuth and API client code
- `tests/test_main.py` - Personal mode test suite
- `tests/test_coach_sync.py` - Coach mode test suite
- `tests/test_strava_oauth.py` - OAuth and API client tests
- `docs/coach_mode.md` - Coach-mode setup guide
- `requirements.txt` - Python dependencies
- `setup.py` - Package configuration and console entry points
- `exec_setup.py` - cx_Freeze build configuration
- `interactive_setup.py` - Interactive installer
- `.github/workflows/coverage.yml` - CI workflow
- `.pylintrc` - Linting configuration; do not rely on direct pylint runs for validation

## Development Guidelines

### Code Quality

- Do not run `pylint` directly; use the test suite and coverage workflow instead
- Run the full test suite before finishing changes
- Keep changes consistent with the existing style in `src/main.py`, `src/coach_sync.py`, and `src/strava_oauth.py`

### Performance Considerations

- TCX processing may preprocess and reduce larger datasets
- AI analysis is optional and depends on OpenAI
- Audio summaries use OpenAI TTS
- Coach mode can batch-download activities for multiple athletes

### API Dependencies

- OpenAI API: optional, for analysis and audio summaries
- Strava API: required for activity downloads and coach mode
- TrainingPeaks: the manual upload destination for formatted TCX files

## Troubleshooting

### Common Issues

1. Interactive prompts hang because the application expects user input
2. Docker builds can fail in sandboxed environments because of network access
3. OAuth tests and coach mode depend on `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET`
4. Long builds are normal for the cx_Freeze executable step

### Error Messages

- Invalid TCX file: TCX validation failed
- OpenAI API key not found: set `OPENAI_API_KEY` if you want AI features
- STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables are required: configure coach mode credentials
- No TCX file found in Downloads folder: the app could not find a downloaded file automatically

## File Structure Reference

```
strava-to-trainingpeaks/
├── .github/workflows/coverage.yml
├── src/
│   ├── __init__.py
│   ├── coach_sync.py
│   ├── main.py
│   └── strava_oauth.py
├── tests/
│   ├── __init__.py
│   ├── test_coach_sync.py
│   ├── test_main.py
│   └── test_strava_oauth.py
├── requirements.txt
├── setup.py
├── exec_setup.py
├── interactive_setup.py
├── Dockerfile
├── Makefile
├── __version__.py
└── README.md
```

## Key Classes and Functions

- `TCXProcessor`: personal-mode TCX processing and AI analysis
- `TrackpointProcessor`: trackpoint preprocessing and reduction
- `CoachSyncManager`: coach-mode menu and athlete management
- `StravaOAuthClient`: OAuth authorization and token management
- `StravaAPIClient`: coach-mode activity download client
- `ProcessingConfig`: data-processing parameters
- `AnalysisConfig`: AI analysis configuration
- `Sport`: bike, run, swim, and other activity types

REMEMBER: This is an interactive CLI application. Always account for user input requirements when testing or demonstrating functionality.
