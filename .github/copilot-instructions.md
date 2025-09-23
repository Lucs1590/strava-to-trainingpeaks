# Strava to TrainingPeaks

**CRITICAL**: Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

This repository contains a Python CLI application that downloads activities from Strava and uploads them to TrainingPeaks. The application uses interactive prompts for user guidance, supports AI-powered analysis with OpenAI, and can generate audio summaries.

## Environment Setup

### Prerequisites
- **Python**: 3.12 (as specified in CI workflow, tested version)
- **pip**: Latest version
- **Internet access**: Required for OpenAI API and Strava downloads (optional for core functionality)

### Quick Start Commands
```bash
# Clone and setup (if starting fresh)
git clone https://github.com/Lucs1590/strava-to-trainingpeaks
cd strava-to-trainingpeaks

# Essential setup (4-5 minutes total)
pip install -r requirements.txt  # ~90 seconds
pip install .                    # ~15 seconds
python -m unittest discover -s tests -v  # ~52 seconds

# Verify installation
strava-to-trainingpeaks  # Should show sport selection menu
```

## Working Effectively

Bootstrap, build, and test the repository using these exact commands:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   - **Timing**: ~90 seconds. NEVER CANCEL - Set timeout to 300+ seconds.
   - **Dependencies**: 13 packages including cx_Freeze, langchain, openai, pandas, scipy

2. **Install the package**:
   ```bash
   pip install .
   ```
   - **Timing**: ~15 seconds.

3. **Run tests**:
   ```bash
   python -m unittest discover -s tests -v
   ```
   - **Timing**: ~52 seconds. NEVER CANCEL - Set timeout to 120+ seconds.
   - **Coverage**: 73 tests, 99% code coverage on src/main.py
   - Also run: `pytest --cov --junitxml=junit.xml -o junit_family=legacy`

4. **Build executable (optional)**:
   ```bash
   python exec_setup.py build
   ```
   - **Timing**: ~13 minutes (783 seconds). NEVER CANCEL - Set timeout to 1200+ seconds.
   - **Output**: Creates executable in `build/exe.linux-x86_64-3.12/main`
   - **Size**: ~5.8MB executable with extensive library dependencies

## Running the Application

- **CLI Command**: `strava-to-trainingpeaks` (after pip install)
- **Direct Python**: `python src/main.py`
- **Interactive Setup**: `python interactive_setup.py`

**IMPORTANT**: The application is interactive and requires user input. It will prompt for:
- Sport selection (Bike, Run, Swim, Other)
- Activity download method (download from Strava or provide file path)
- Optional AI analysis (requires OpenAI API key)
- Optional audio summary generation

## Validation

After making changes, ALWAYS run these validation steps in order:

### 1. Automated Testing
```bash
# Run full test suite (52 seconds, NEVER CANCEL)
python -m unittest discover -s tests -v

# Run with coverage reporting
pytest --cov --junitxml=junit.xml -o junit_family=legacy
```

### 2. Import and Basic Functionality
```bash
# Test import works
python -c "from src.main import TCXProcessor; print('Import successful')"

# Test CLI entry point exists
which strava-to-trainingpeaks  # Should show path after pip install
```

### 3. Manual Validation Scenarios

**CRITICAL**: You must manually test the application's core workflow after any changes:

1. **Basic CLI Launch**:
   ```bash
   python src/main.py
   ```
   - **Expected**: Sport selection menu appears with 4 options (Bike, Run, Swim, Other)
   - **Action**: Verify menu renders correctly, then Ctrl+C to exit

2. **Package Installation Test**:
   ```bash
   strava-to-trainingpeaks
   ```
   - **Expected**: Same sport selection menu
   - **Action**: Verify global command works after pip install

3. **Interactive Setup Test**:
   ```bash
   python interactive_setup.py
   ```
   - **Expected**: Setup method selection menu (Global installation, Virtual environment, Docker)
   - **Action**: Verify interactive prompts work correctly

### 4. Build Validation (if modifying core functionality)
```bash
# Test executable build (13 minutes, NEVER CANCEL, timeout 1200+ seconds)
python exec_setup.py build

# Test executable runs
./build/exe.linux-x86_64-3.12/main
```

### 5. CI/CD Validation
Always ensure your changes don't break the GitHub Actions workflow:
- Tests must pass in CI environment
- Coverage must remain above 99%
- No new linting issues should be introduced

## Common Tasks

### Testing Different Installation Methods

1. **Global Installation** (recommended for development):
   ```bash
   pip install .
   ```

2. **Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install .
   ```

3. **Interactive Setup**:
   ```bash
   python interactive_setup.py
   ```

4. **Docker** (network-dependent, may fail in sandboxed environments):
   ```bash
   docker build -t strava-to-trainingpeaks .
   docker run -it --rm strava-to-trainingpeaks
   ```

### Key Files and Directories

- `src/main.py` - Main application entry point with TCXProcessor class
- `tests/test_main.py` - Comprehensive test suite (73 tests)
- `requirements.txt` - Python dependencies
- `setup.py` - Package configuration and entry points
- `exec_setup.py` - cx_Freeze configuration for executable builds
- `interactive_setup.py` - Interactive installation script
- `Dockerfile` - Docker configuration
- `.github/workflows/coverage.yml` - CI/CD pipeline
- `.pylintrc` - Linting configuration (may have compatibility issues with newer pylint)

### CI/CD Integration

The repository uses GitHub Actions for testing:
- **Coverage Workflow**: `.github/workflows/coverage.yml`
- **Python Version**: 3.12
- **Test Command**: `pytest --cov --junitxml=junit.xml -o junit_family=legacy`
- **Coverage**: Reports to Codecov

## Development Guidelines

### Code Quality
- **DO NOT** run `pylint` directly - the `.pylintrc` configuration has compatibility issues
- **DO** run the full test suite before committing
- **DO** maintain 99%+ test coverage
- **DO** follow the existing code style in `src/main.py`

### Performance Considerations
- The application processes TCX files and may perform data preprocessing
- AI analysis is optional and requires OpenAI API key
- Audio generation uses OpenAI TTS API
- Large datasets are reduced using Euclidean filtering

### API Dependencies
- **OpenAI API**: For AI analysis and audio generation (optional)
- **Strava API**: For downloading TCX files (requires activity ID)
- **TrainingPeaks**: Manual upload destination

## Troubleshooting

### Common Issues
1. **Interactive prompts hang**: The application requires user input - this is expected behavior
2. **Docker build fails**: Network connectivity issues in sandboxed environments are expected
3. **Pylint errors**: Use the test suite instead of pylint for code validation
4. **Long build times**: cx_Freeze builds are CPU-intensive and take 13+ minutes

### Error Messages
- **"Invalid TCX file"**: TCX validation failed, check file format
- **"OpenAI API key not found"**: Set `OPENAI_API_KEY` environment variable for AI features
- **"No TCX file found in Downloads folder"**: Application looks for downloaded files automatically

## File Structure Reference

```
strava-to-trainingpeaks/
├── .github/workflows/coverage.yml    # CI/CD pipeline
├── src/
│   ├── __init__.py
│   └── main.py                       # Main application (TCXProcessor class)
├── tests/
│   ├── __init__.py
│   └── test_main.py                  # Test suite (73 tests)
├── requirements.txt                  # Dependencies
├── setup.py                          # Package configuration
├── exec_setup.py                     # Executable build config
├── interactive_setup.py              # Interactive installer
├── Dockerfile                        # Docker configuration
├── Makefile                          # Simple install target
├── __version__.py                    # Version: 1.3.0
└── README.md                         # Documentation
```

## Key Classes and Functions

- `TCXProcessor`: Main application class handling TCX file processing
- `TrackpointProcessor`: Data preprocessing for trackpoint analysis
- `ProcessingConfig`: Configuration for data processing parameters
- `Sport` enum: Bike, Run, Swim, Other activity types

REMEMBER: This is an interactive CLI application. Always account for user input requirements when testing or demonstrating functionality.