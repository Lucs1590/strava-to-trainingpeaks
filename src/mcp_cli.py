#!/usr/bin/env python3
"""
Strava MCP CLI - Command line interface for the Strava MCP server.
Demonstrates the MCP functionality for Strava integration.
"""

from mcp_server import StravaActivityMCP
import asyncio
import json
import argparse
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Strava MCP CLI")
    parser.add_argument("command", help="MCP command to execute", choices=[
        # Strava commands
        "list-tools", "list-activities", "get-activity", "analyze-activity",
        "sync-activities", "get-auth-url", "authenticate",
        # TrainingPeaks commands
        "tp-auth-info", "tp-athlete", "tp-workouts", "tp-workout-detail",
        "tp-upload", "sync-to-tp", "bulk-sync-to-tp", "tp-plans",
        "tp-planned-workouts", "tp-metrics"
    ])
    parser.add_argument("--activity-id", help="Strava activity ID")
    parser.add_argument("--workout-id", help="TrainingPeaks workout ID")
    parser.add_argument("--limit", type=int, default=10,
                        help="Limit for activities list")
    parser.add_argument("--days-back", type=int,
                        default=30, help="Days to look back")
    parser.add_argument("--days-ahead", type=int, default=30,
                        help="Days to look ahead for planned workouts")
    parser.add_argument("--training-plan", default="",
                        help="Training plan context for analysis")
    parser.add_argument("--language", default="English",
                        help="Language for analysis")
    parser.add_argument("--code", help="OAuth authorization code")
    parser.add_argument("--include-analysis",
                        action="store_true", help="Include AI analysis")
    parser.add_argument("--include-tcx", action="store_true",
                        default=True, help="Include TCX data for sync")
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format")

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
                            required = param in tool['inputSchema'].get(
                                'required', [])
                            print(
                                f"  - {param} ({details['type']}{'*' if required else ''}): {details.get('description', '')}")

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
                            print(
                                f"Distance: {activity['distance']/1000:.2f} km")
                        if activity['moving_time']:
                            print(
                                f"Time: {activity['moving_time']//60}:{activity['moving_time'] % 60:02d}")

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
                    print(
                        f"Distance: {activity.get('distance', 0)/1000:.2f} km")
                    print(
                        f"Moving Time: {activity.get('moving_time', 0)//60}:{activity.get('moving_time', 0) % 60:02d}")
                    print(
                        f"Elevation Gain: {activity.get('total_elevation_gain', 0)} m")
                    if activity.get('average_heartrate'):
                        print(
                            f"Avg Heart Rate: {activity['average_heartrate']} bpm")
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
                        print(
                            f"✓ {activity['name']} ({activity['type']}) - {activity['date']}")

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
                    print(
                        f"Visit this URL to authorize: {result['authorization_url']}")
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
                        print(
                            f"Welcome, {athlete.get('firstname', '')} {athlete.get('lastname', '')}!")

        # TrainingPeaks Commands
        elif args.command == "tp-auth-info":
            result = await mcp_server.handle_tool_call("get_trainingpeaks_auth_info", {})
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    auth_info = result['auth_info']
                    print("TrainingPeaks Authentication Status:")
                    print("=" * 50)
                    print(f"Authenticated: {auth_info['authenticated']}")
                    if auth_info['auth_methods']:
                        print(
                            f"Available methods: {', '.join(auth_info['auth_methods'])}")
                    else:
                        print("No authentication methods configured")
                        print("\nRequired environment variables:")
                        for var in auth_info['required_env_vars']:
                            print(f"  - {var}")

        elif args.command == "tp-athlete":
            result = await mcp_server.handle_tool_call("get_trainingpeaks_athlete", {})
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    athlete = result['athlete']
                    print("TrainingPeaks Athlete Profile:")
                    print("=" * 50)
                    print(f"Name: {athlete.get('name', 'Unknown')}")
                    print(f"Email: {athlete.get('email', 'Unknown')}")

        elif args.command == "tp-workouts":
            result = await mcp_server.handle_tool_call("list_trainingpeaks_workouts", {
                "days_back": args.days_back,
                "limit": args.limit
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Found {result['count']} workouts:")
                    print("=" * 50)
                    for workout in result['workouts']:
                        print(f"\nID: {workout.get('id', 'Unknown')}")
                        print(f"Title: {workout.get('title', 'Untitled')}")
                        print(f"Date: {workout.get('workoutDate', 'Unknown')}")
                        print(f"Sport: {workout.get('sport', 'Unknown')}")
                        if workout.get('distance'):
                            print(f"Distance: {workout['distance']:.2f} km")
                        if workout.get('duration'):
                            print(
                                f"Duration: {workout['duration'] // 60} minutes")

        elif args.command == "sync-to-tp":
            if not args.activity_id:
                print("Error: --activity-id is required for sync-to-tp command")
                sys.exit(1)

            result = await mcp_server.handle_tool_call("sync_strava_to_trainingpeaks", {
                "activity_id": args.activity_id,
                "include_tcx": True
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print("Sync Successful!")
                    print("=" * 50)
                    print(f"Activity ID: {result['activity_id']}")
                    sync_result = result['sync_result']
                    if sync_result['success']:
                        print("Successfully synced to TrainingPeaks")
                    else:
                        print(
                            f"Sync failed: {sync_result.get('error', 'Unknown error')}")

        elif args.command == "bulk-sync-to-tp":
            result = await mcp_server.handle_tool_call("bulk_sync_strava_to_trainingpeaks", {
                "days_back": args.days_back,
                "limit": args.limit
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print("Bulk Sync Results:")
                    print("=" * 50)
                    print(f"Total activities: {result['total_activities']}")
                    print(f"Successful syncs: {result['successful_syncs']}")
                    print(f"Failed syncs: {result['failed_syncs']}")

                    if result['results']:
                        print("\nDetails:")
                        for item in result['results']:
                            status_icon = "✓" if item['status'] == 'success' else "✗"
                            print(
                                f"  {status_icon} {item['activity_name']} (ID: {item['activity_id']})")
                            if item['status'] == 'error':
                                print(
                                    f"    Error: {item.get('error', 'Unknown error')}")

        elif args.command == "tp-plans":
            result = await mcp_server.handle_tool_call("get_training_plans", {})
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Found {result['count']} training plans:")
                    print("=" * 50)
                    for plan in result['plans']:
                        print(f"\nID: {plan.get('id', 'Unknown')}")
                        print(f"Name: {plan.get('name', 'Untitled')}")
                        print(
                            f"Start Date: {plan.get('startDate', 'Unknown')}")
                        print(f"End Date: {plan.get('endDate', 'Unknown')}")

        elif args.command == "tp-planned-workouts":
            result = await mcp_server.handle_tool_call("get_planned_workouts", {
                "days_ahead": args.days_back  # Reuse days_back for days_ahead
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Found {result['count']} planned workouts:")
                    print("=" * 50)
                    for workout in result['planned_workouts']:
                        print(
                            f"\nDate: {workout.get('workoutDate', 'Unknown')}")
                        print(f"Title: {workout.get('title', 'Untitled')}")
                        print(f"Sport: {workout.get('sport', 'Unknown')}")
                        print(
                            f"Description: {workout.get('description', 'No description')}")

        elif args.command == "tp-metrics":
            result = await mcp_server.handle_tool_call("get_training_metrics", {
                "days_back": args.days_back
            })
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    metrics = result['metrics']
                    print("Training Metrics:")
                    print("=" * 50)
                    print(f"Period: Last {args.days_back} days")
                    for key, value in metrics.items():
                        print(f"{key}: {value}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
