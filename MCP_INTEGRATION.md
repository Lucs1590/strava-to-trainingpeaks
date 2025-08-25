# Strava to TrainingPeaks MCP Integration

This document describes the Model Context Protocol (MCP) integration for Strava activity synchronization, TrainingPeaks workout management, and AI analysis.

## Overview

The MCP integration provides a standardized way to connect AI assistants to both Strava and TrainingPeaks for comprehensive training data management. It exposes several tools through the MCP protocol that allow:

### Strava Integration
- Fetching recent activities from Strava
- Getting detailed activity information with GPS streams
- Analyzing activities using AI
- Managing Strava OAuth authentication

### TrainingPeaks Integration  
- Uploading workouts to TrainingPeaks
- Fetching workouts and training plans
- Getting planned workouts and training metrics
- Syncing activities between Strava and TrainingPeaks

### Analysis & Synchronization
- AI-powered activity analysis using OpenAI
- Bidirectional sync between platforms
- TCX file generation and processing

## Setup

### 1. API Configuration

Create a `.env` file in the project root with your API credentials:

```bash
# Strava API Configuration
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_ACCESS_TOKEN=your_access_token_here  # Optional, can be obtained via OAuth
STRAVA_REFRESH_TOKEN=your_refresh_token_here  # Optional

# TrainingPeaks API Configuration (choose one authentication method)
TRAININGPEAKS_ACCESS_TOKEN=your_access_token_here  # Preferred: OAuth token
# OR
TRAININGPEAKS_API_KEY=your_api_key_here  # Alternative: API key  
# OR
TRAININGPEAKS_USERNAME=your_username_here  # Legacy: Basic auth
TRAININGPEAKS_PASSWORD=your_password_here

# AI Analysis
OPENAI_API_KEY=your_openai_key_here  # For AI analysis features
```

### 2. Getting API Credentials

#### Strava
1. Go to [Strava Developers](https://developers.strava.com/)
2. Create a new application
3. Note your Client ID and Client Secret

#### TrainingPeaks
1. Go to [TrainingPeaks Developer Portal](https://www.trainingpeaks.com/developer/)
2. Register for API access
3. Get your API credentials (preferred method varies by TrainingPeaks API tier)

### 3. Authentication Flow

#### Strava OAuth
```bash
# Get authorization URL
python src/mcp_cli.py get-auth-url

# Visit the URL, authorize the app, and get the code from redirect
# Exchange code for tokens
python src/mcp_cli.py authenticate --code YOUR_CODE_HERE
```

#### TrainingPeaks Authentication
```bash
# Check authentication status
python src/mcp_cli.py tp-auth-info
```

## Available MCP Tools

### 1. list_activities

List recent Strava activities.

**Parameters:**
- `limit` (integer, optional): Number of activities to retrieve (default: 30)
- `days_back` (integer, optional): Number of days to look back (default: 30)

**Example:**
```bash
python src/mcp_cli.py list-activities --limit 10 --days-back 7
```

### 2. get_activity_detail

Get detailed information about a specific activity.

**Parameters:**
- `activity_id` (string, required): Strava activity ID

**Example:**
```bash
python src/mcp_cli.py get-activity --activity-id 12345
```

### 3. analyze_activity

Analyze a Strava activity using AI.

**Parameters:**
- `activity_id` (string, required): Strava activity ID
- `training_plan` (string, optional): Training plan context for analysis
- `language` (string, optional): Language for analysis output (default: "English")

**Example:**
```bash
python src/mcp_cli.py analyze-activity --activity-id 12345 --language "English" --training-plan "Marathon training week 3"
```

### 4. sync_recent_activities

Synchronize recent activities and prepare for TrainingPeaks export.

**Parameters:**
- `days_back` (integer, optional): Number of days to sync back (default: 7)
- `include_analysis` (boolean, optional): Include AI analysis for activities

**Example:**
```bash
python src/mcp_cli.py sync-activities --days-back 14 --include-analysis
```

### 5. get_authorization_url

Get Strava OAuth authorization URL for authentication.

**Parameters:**
- `redirect_uri` (string, optional): OAuth redirect URI (default: "http://localhost:8000/auth")

**Example:**
```bash
python src/mcp_cli.py get-auth-url
```

### 6. authenticate_with_code

Exchange OAuth code for access tokens.

**Parameters:**
- `code` (string, required): OAuth authorization code

**Example:**
```bash
python src/mcp_cli.py authenticate --code YOUR_OAUTH_CODE
```

## TrainingPeaks MCP Tools

### 7. get_trainingpeaks_auth_info

Get TrainingPeaks authentication status and required credentials.

**Parameters:** None

**Example:**
```bash
python src/mcp_cli.py tp-auth-info
```

### 8. get_trainingpeaks_athlete

Get TrainingPeaks athlete profile information.

**Parameters:** None

**Example:**
```bash
python src/mcp_cli.py tp-athlete
```

### 9. list_trainingpeaks_workouts

List recent workouts from TrainingPeaks.

**Parameters:**
- `days_back` (integer, optional): Number of days to look back (default: 30)
- `limit` (integer, optional): Maximum number of workouts to retrieve (default: 50)

**Example:**
```bash
python src/mcp_cli.py tp-workouts --days-back 30 --limit 20
```

### 10. get_trainingpeaks_workout_detail

Get detailed information about a specific TrainingPeaks workout.

**Parameters:**
- `workout_id` (string, required): TrainingPeaks workout ID

**Example:**
```bash
python src/mcp_cli.py tp-workout-detail --workout-id 67890
```

### 11. sync_strava_to_trainingpeaks

Sync a single Strava activity to TrainingPeaks.

**Parameters:**
- `activity_id` (string, required): Strava activity ID to sync
- `include_tcx` (boolean, optional): Include TCX data for better accuracy (default: True)

**Example:**
```bash
python src/mcp_cli.py sync-to-tp --activity-id 12345
```

### 12. bulk_sync_strava_to_trainingpeaks

Bulk sync recent Strava activities to TrainingPeaks.

**Parameters:**
- `days_back` (integer, optional): Number of days to look back (default: 7)
- `limit` (integer, optional): Maximum number of activities to sync (default: 10)

**Example:**
```bash
python src/mcp_cli.py bulk-sync-to-tp --days-back 7 --limit 10
```

### 13. get_training_plans

Get training plans from TrainingPeaks.

**Parameters:** None

**Example:**
```bash
python src/mcp_cli.py tp-plans
```

### 14. get_planned_workouts

Get planned workouts from TrainingPeaks training plans.

**Parameters:**
- `days_ahead` (integer, optional): Number of days ahead to look for planned workouts (default: 30)

**Example:**
```bash
python src/mcp_cli.py tp-planned-workouts --days-ahead 30
```

### 15. get_training_metrics

Get training metrics and analytics from TrainingPeaks.

**Parameters:**
- `days_back` (integer, optional): Number of days to look back for metrics (default: 30)

**Example:**
```bash
python src/mcp_cli.py tp-metrics --days-back 30
```

## Usage Examples

### Command Line Interface

The MCP functionality is exposed through a command-line interface:

#### Strava Commands
```bash
# List available tools
python src/mcp_cli.py list-tools

# List recent activities from Strava
python src/mcp_cli.py list-activities --limit 5

# Get activity details  
python src/mcp_cli.py get-activity --activity-id 12345

# Analyze an activity with AI
python src/mcp_cli.py analyze-activity --activity-id 12345 --language "Portuguese"

# Sync recent activities for export
python src/mcp_cli.py sync-activities --days-back 7
```

#### TrainingPeaks Commands
```bash
# Check TrainingPeaks authentication
python src/mcp_cli.py tp-auth-info

# List TrainingPeaks workouts
python src/mcp_cli.py tp-workouts --days-back 30 --limit 20

# Get athlete profile
python src/mcp_cli.py tp-athlete

# Get training plans
python src/mcp_cli.py tp-plans

# Get planned workouts
python src/mcp_cli.py tp-planned-workouts --days-ahead 30

# Get training metrics
python src/mcp_cli.py tp-metrics --days-back 30
```

#### Synchronization Commands
```bash
# Sync single activity from Strava to TrainingPeaks
python src/mcp_cli.py sync-to-tp --activity-id 12345

# Bulk sync recent activities
python src/mcp_cli.py bulk-sync-to-tp --days-back 7 --limit 10
```

### Interactive Mode

You can also run the MCP server in interactive mode for testing:

```bash
python src/mcp_server_main.py --interactive
```

This opens an interactive session where you can call tools directly:

```
mcp> help
mcp> call list_activities {}
mcp> call get_activity_detail {"activity_id": "12345"}
mcp> quit
```

### Programmatic Usage

You can also use the MCP server programmatically:

```python
import asyncio
from src.mcp_server import StravaActivityMCP

async def main():
    mcp_server = StravaActivityMCP()
    
    # List available tools
    tools = mcp_server.get_available_tools()
    print(f"Available tools: {[tool['name'] for tool in tools]}")
    
    # Call a tool
    result = await mcp_server.handle_tool_call("list_activities", {"limit": 5})
    if result.get("success"):
        print(f"Found {result['count']} activities")
    else:
        print(f"Error: {result.get('error')}")

asyncio.run(main())
```

## Integration with Existing CLI

The MCP integration is designed to complement the existing CLI interface. You can still use the original functionality:

```bash
# Original CLI (still works)
python src/main.py

# New MCP CLI
python src/mcp_cli.py list-activities
```

## Error Handling

The MCP tools include comprehensive error handling:

- **Authentication errors**: Tools will attempt to refresh expired tokens automatically
- **API errors**: Strava API errors are caught and returned with descriptive messages
- **Configuration errors**: Missing credentials are detected and reported clearly

## Data Processing

Activity data is processed to be compatible with the existing TrainingPeaks export functionality:

- **Stream data**: GPS, heart rate, power, and other sensor data
- **Analysis format**: Converted to match the existing TCX processing pipeline
- **AI analysis**: Uses the same analysis capabilities as the original tool

## Security

- **Credentials**: Stored in `.env` file (not committed to version control)
- **Token refresh**: Automatic refresh of expired access tokens
- **Scope limitation**: Requests minimal necessary permissions from Strava

## Backward Compatibility

The MCP integration maintains full backward compatibility:

- Existing CLI interface unchanged
- Original functionality preserved
- Same analysis and processing capabilities
- Compatible with existing tests and workflows