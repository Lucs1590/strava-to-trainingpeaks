#!/usr/bin/env python3
"""
Strava MCP CLI - Command line interface for the Strava MCP server.
Demonstrates the MCP functionality for Strava integration.
"""

import asyncio
import json
import argparse
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import StravaActivityMCP


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Strava MCP CLI")
    parser.add_argument("command", help="MCP command to execute", choices=[
        "list-tools", "list-activities", "get-activity", "analyze-activity", 
        "sync-activities", "get-auth-url", "authenticate"
    ])
    parser.add_argument("--activity-id", help="Strava activity ID")
    parser.add_argument("--limit", type=int, default=10, help="Limit for activities list")
    parser.add_argument("--days-back", type=int, default=30, help="Days to look back")
    parser.add_argument("--training-plan", default="", help="Training plan context for analysis")
    parser.add_argument("--language", default="English", help="Language for analysis")
    parser.add_argument("--code", help="OAuth authorization code")
    parser.add_argument("--include-analysis", action="store_true", help="Include AI analysis")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Initialize MCP server
    mcp_server = StravaActivityMCP()
    
    try:
        if args.command == "list-tools":
            tools = mcp_server.get_available_tools()
            if args.json:
                print(json.dumps(tools, indent=2))
            else:
                print("Available MCP Tools:")
                print("==================")
                for tool in tools:
                    print(f"\n{tool['name']}")
                    print(f"Description: {tool['description']}")
                    if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                        print("Parameters:")
                        for param, details in tool['inputSchema']['properties'].items():
                            required = param in tool['inputSchema'].get('required', [])
                            print(f"  - {param} ({details['type']}{'*' if required else ''}): {details.get('description', '')}")
        
        elif args.command == "list-activities":
            result = await mcp_server.handle_tool_call("list_activities", {
                "limit": args.limit,
                "days_back": args.days_back
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Found {result['count']} activities:")
                    print("=" * 50)
                    for activity in result['activities']:
                        print(f"\nID: {activity['id']}")
                        print(f"Name: {activity['name']}")
                        print(f"Type: {activity['type']}")
                        print(f"Date: {activity['start_date']}")
                        if activity['distance']:
                            print(f"Distance: {activity['distance']/1000:.2f} km")
                        if activity['moving_time']:
                            print(f"Time: {activity['moving_time']//60}:{activity['moving_time']%60:02d}")
        
        elif args.command == "get-activity":
            if not args.activity_id:
                print("Error: --activity-id is required for get-activity command")
                sys.exit(1)
            
            result = await mcp_server.handle_tool_call("get_activity_detail", {
                "activity_id": args.activity_id
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    activity = result['activity']
                    print(f"Activity Details for ID: {args.activity_id}")
                    print("=" * 50)
                    print(f"Name: {activity['name']}")
                    print(f"Type: {activity['type']}")
                    print(f"Date: {activity['start_date']}")
                    print(f"Distance: {activity.get('distance', 0)/1000:.2f} km")
                    print(f"Moving Time: {activity.get('moving_time', 0)//60}:{activity.get('moving_time', 0)%60:02d}")
                    print(f"Elevation Gain: {activity.get('total_elevation_gain', 0)} m")
                    if activity.get('average_heartrate'):
                        print(f"Avg Heart Rate: {activity['average_heartrate']} bpm")
                    if activity.get('average_watts'):
                        print(f"Avg Power: {activity['average_watts']} W")
        
        elif args.command == "analyze-activity":
            if not args.activity_id:
                print("Error: --activity-id is required for analyze-activity command")
                sys.exit(1)
            
            result = await mcp_server.handle_tool_call("analyze_activity", {
                "activity_id": args.activity_id,
                "training_plan": args.training_plan,
                "language": args.language
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"AI Analysis for Activity {args.activity_id}")
                    print("=" * 50)
                    print(f"Sport: {result['sport']}")
                    print(f"Data Points: {result['data_points']}")
                    print(f"Analysis:\n{result['analysis']}")
        
        elif args.command == "sync-activities":
            result = await mcp_server.handle_tool_call("sync_recent_activities", {
                "days_back": args.days_back,
                "include_analysis": args.include_analysis
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Synchronized {result['synced_count']} activities")
                    print("=" * 50)
                    for activity in result['activities']:
                        print(f"✓ {activity['name']} ({activity['type']}) - {activity['date']}")
        
        elif args.command == "get-auth-url":
            result = await mcp_server.handle_tool_call("get_authorization_url", {})
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print("Strava Authorization")
                    print("=" * 50)
                    print(f"Visit this URL to authorize: {result['authorization_url']}")
                    print(f"\n{result['instructions']}")
        
        elif args.command == "authenticate":
            if not args.code:
                print("Error: --code is required for authenticate command")
                sys.exit(1)
            
            result = await mcp_server.handle_tool_call("authenticate_with_code", {
                "code": args.code
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print("Authentication Successful!")
                    print("=" * 50)
                    print(result['message'])
                    if 'athlete' in result:
                        athlete = result['athlete']
                        print(f"Welcome, {athlete.get('firstname', '')} {athlete.get('lastname', '')}!")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())