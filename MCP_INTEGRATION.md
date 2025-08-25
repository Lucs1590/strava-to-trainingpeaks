# Strava MCP Integration

This document describes the Model Context Protocol (MCP) integration for Strava activity synchronization and analysis.

## Overview

The Strava MCP integration provides a standardized way to connect AI assistants to Strava data for activity synchronization and analysis. It exposes several tools through the MCP protocol that allow:

- Fetching recent activities from Strava
- Getting detailed activity information
- Analyzing activities using AI
- Synchronizing activities for TrainingPeaks export
- Managing Strava authentication

## Setup

### 1. Strava API Configuration

First, you need to register your application with Strava and get API credentials:

1. Go to [Strava Developers](https://developers.strava.com/)
2. Create a new application
3. Note your Client ID and Client Secret
4. Create a `.env` file in the project root:

```bash
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_ACCESS_TOKEN=your_access_token_here
STRAVA_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=your_openai_key_here  # For AI analysis
```

### 2. Authentication Flow

To get access tokens, use the authentication flow:

```bash
# Get authorization URL
python src/mcp_cli.py get-auth-url

# Visit the URL, authorize the app, and get the code from redirect
# Exchange code for tokens
python src/mcp_cli.py authenticate --code YOUR_CODE_HERE
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

## Usage Examples

### Command Line Interface

The MCP functionality is exposed through a command-line interface:

```bash
# List available tools
python src/mcp_cli.py list-tools

# List recent activities
python src/mcp_cli.py list-activities --limit 5

# Get activity details  
python src/mcp_cli.py get-activity --activity-id 12345

# Analyze an activity
python src/mcp_cli.py analyze-activity --activity-id 12345 --language "Portuguese"

# Sync recent activities
python src/mcp_cli.py sync-activities --days-back 7
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