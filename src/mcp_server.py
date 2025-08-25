"""MCP server for Strava integration and activity analysis using official MCP package."""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from strava_client import StravaClient, StravaAPIError
from main import TCXProcessor, Sport, AnalysisConfig, setup_logging


def create_strava_mcp_server() -> FastMCP:
    """Create and configure the Strava MCP server with all tools."""
    
    # Create the FastMCP server
    mcp = FastMCP(
        name="strava-activity-server",
        instructions="MCP server for Strava integration providing activity synchronization and analysis tools"
    )
    
    # Initialize clients
    strava_client = StravaClient()
    tcx_processor = TCXProcessor()
    logger = setup_logging()

    @mcp.tool()
    async def list_activities(limit: int = 30, days_back: int = 30) -> Dict[str, Any]:
        """List recent Strava activities.
        
        Args:
            limit: Number of activities to retrieve (default: 30)
            days_back: Number of days to look back (default: 30)
            
        Returns:
            Dictionary containing success status, count, and list of activities
        """
        try:
            after = datetime.now() - timedelta(days=days_back)
            activities = await strava_client.get_activities(limit=limit, after=after)
            
            # Format activities for response
            formatted_activities = []
            for activity in activities:
                formatted_activity = {
                    "id": activity["id"],
                    "name": activity["name"],
                    "type": activity["type"],
                    "sport_type": activity.get("sport_type", activity["type"]),
                    "start_date": activity["start_date"],
                    "distance": activity.get("distance", 0),
                    "moving_time": activity.get("moving_time", 0),
                    "elapsed_time": activity.get("elapsed_time", 0),
                    "average_speed": activity.get("average_speed", 0),
                    "max_speed": activity.get("max_speed", 0),
                    "average_heartrate": activity.get("average_heartrate"),
                    "max_heartrate": activity.get("max_heartrate"),
                    "average_watts": activity.get("average_watts"),
                    "weighted_average_watts": activity.get("weighted_average_watts"),
                    "kilojoules": activity.get("kilojoules"),
                    "description": activity.get("description", "")
                }
                formatted_activities.append(formatted_activity)
            
            return {
                "success": True,
                "count": len(formatted_activities),
                "activities": formatted_activities
            }
            
        except StravaAPIError as e:
            logger.error(f"Strava API error in list_activities: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in list_activities: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_activity_detail(activity_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific activity.
        
        Args:
            activity_id: The Strava activity ID
            
        Returns:
            Dictionary containing activity details and streams data
        """
        try:
            activity = await strava_client.get_activity_detail(activity_id)
            streams = None
            
            # Try to get stream data as well
            try:
                streams = await strava_client.get_activity_streams(activity_id)
            except StravaAPIError:
                logger.warning(f"Could not fetch streams for activity {activity_id}")
            
            return {
                "success": True,
                "activity": activity,
                "streams": streams
            }
            
        except StravaAPIError as e:
            logger.error(f"Strava API error in get_activity_detail: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_activity_detail: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def analyze_activity(activity_id: str, language: str = "English") -> Dict[str, Any]:
        """Analyze a Strava activity using AI.
        
        Args:
            activity_id: The Strava activity ID to analyze
            language: Language for the analysis (default: English)
            
        Returns:
            Dictionary containing AI analysis of the activity
        """
        try:
            # Get activity details and streams
            activity = await strava_client.get_activity_detail(activity_id)
            streams = None
            
            try:
                streams = await strava_client.get_activity_streams(activity_id)
            except StravaAPIError:
                logger.warning(f"Could not fetch streams for activity {activity_id}")
            
            # Create analysis config
            config = AnalysisConfig(
                activity_file=None,  # We're using API data, not file
                language=language,
                analysis_type="activity",
                sport=Sport.from_strava_type(activity.get("type", "Run"))
            )
            
            # Format activity data for analysis
            activity_data = {
                "name": activity["name"],
                "type": activity["type"],
                "distance": activity.get("distance", 0),
                "moving_time": activity.get("moving_time", 0),
                "average_speed": activity.get("average_speed", 0),
                "average_heartrate": activity.get("average_heartrate"),
                "average_watts": activity.get("average_watts"),
                "description": activity.get("description", "")
            }
            
            if streams:
                activity_data["streams"] = streams
            
            # Perform analysis using existing processor
            analysis = await tcx_processor.analyze_activity_data(activity_data, config)
            
            return {
                "success": True,
                "activity_id": activity_id,
                "analysis": analysis
            }
            
        except StravaAPIError as e:
            logger.error(f"Strava API error in analyze_activity: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in analyze_activity: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def sync_recent_activities(days_back: int = 7, limit: int = 20) -> Dict[str, Any]:
        """Synchronize recent activities from Strava for TrainingPeaks export.
        
        Args:
            days_back: Number of days to look back (default: 7)
            limit: Maximum number of activities to sync (default: 20)
            
        Returns:
            Dictionary containing sync results
        """
        try:
            # Get recent activities
            after = datetime.now() - timedelta(days=days_back)
            activities = await strava_client.get_activities(limit=limit, after=after)
            
            sync_results = []
            for activity in activities:
                try:
                    # Get detailed activity data
                    activity_detail = await strava_client.get_activity_detail(str(activity["id"]))
                    streams = None
                    
                    try:
                        streams = await strava_client.get_activity_streams(str(activity["id"]))
                    except StravaAPIError:
                        logger.warning(f"Could not fetch streams for activity {activity['id']}")
                    
                    # Convert to TCX format for export
                    sport = Sport.from_strava_type(activity["type"])
                    tcx_data = tcx_processor.convert_strava_to_tcx(activity_detail, streams, sport)
                    
                    sync_results.append({
                        "activity_id": activity["id"],
                        "name": activity["name"],
                        "type": activity["type"],
                        "status": "synced",
                        "tcx_data": tcx_data
                    })
                    
                except Exception as e:
                    sync_results.append({
                        "activity_id": activity["id"],
                        "name": activity.get("name", "Unknown"),
                        "type": activity.get("type", "Unknown"),
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "synced_count": len([r for r in sync_results if r["status"] == "synced"]),
                "error_count": len([r for r in sync_results if r["status"] == "error"]),
                "results": sync_results
            }
            
        except StravaAPIError as e:
            logger.error(f"Strava API error in sync_recent_activities: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in sync_recent_activities: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_authorization_url(redirect_uri: str = "http://localhost:8000/auth") -> Dict[str, Any]:
        """Get Strava OAuth authorization URL for authentication.
        
        Args:
            redirect_uri: OAuth redirect URI (default: http://localhost:8000/auth)
            
        Returns:
            Dictionary containing the authorization URL
        """
        try:
            auth_url = strava_client.get_authorization_url(redirect_uri)
            return {
                "success": True,
                "authorization_url": auth_url,
                "redirect_uri": redirect_uri
            }
        except Exception as e:
            logger.error(f"Error in get_authorization_url: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def authenticate_with_code(code: str) -> Dict[str, Any]:
        """Exchange OAuth code for access tokens.
        
        Args:
            code: OAuth authorization code from Strava
            
        Returns:
            Dictionary containing authentication status and token info
        """
        try:
            token_data = await strava_client.exchange_code_for_tokens(code)
            return {
                "success": True,
                "athlete_id": token_data.get("athlete", {}).get("id"),
                "athlete_name": token_data.get("athlete", {}).get("firstname", "") + " " + token_data.get("athlete", {}).get("lastname", ""),
                "scope": token_data.get("scope"),
                "expires_at": token_data.get("expires_at")
            }
        except StravaAPIError as e:
            logger.error(f"Strava API error in authenticate_with_code: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in authenticate_with_code: {str(e)}")
            return {"error": str(e)}

    return mcp


# Legacy class for backward compatibility with existing tests
class StravaActivityMCP:
    """Legacy MCP-style server for backward compatibility."""
    
    def __init__(self):
        self.mcp_server = create_strava_mcp_server()
        self.strava_client = StravaClient()
        self.tcx_processor = TCXProcessor()
        self.logger = setup_logging()
        self._cached_tools = None
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools in legacy format."""
        # Since this is a sync method but the underlying API is async,
        # we'll cache the tools or provide a simulated response
        if self._cached_tools is None:
            # Create tool definitions manually for legacy compatibility
            self._cached_tools = [
                {
                    "name": "list_activities",
                    "description": "List recent Strava activities",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of activities to retrieve (default: 30)",
                                "default": 30
                            },
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back (default: 30)",
                                "default": 30
                            }
                        }
                    }
                },
                {
                    "name": "get_activity_detail",
                    "description": "Get detailed information about a specific activity",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "activity_id": {
                                "type": "string",
                                "description": "The Strava activity ID"
                            }
                        },
                        "required": ["activity_id"]
                    }
                },
                {
                    "name": "analyze_activity",
                    "description": "Analyze a Strava activity using AI",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "activity_id": {
                                "type": "string",
                                "description": "The Strava activity ID to analyze"
                            },
                            "language": {
                                "type": "string",
                                "description": "Language for the analysis (default: English)",
                                "default": "English"
                            }
                        },
                        "required": ["activity_id"]
                    }
                },
                {
                    "name": "sync_recent_activities",
                    "description": "Synchronize recent activities from Strava for TrainingPeaks export",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back (default: 7)",
                                "default": 7
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of activities to sync (default: 20)",
                                "default": 20
                            }
                        }
                    }
                },
                {
                    "name": "get_authorization_url",
                    "description": "Get Strava OAuth authorization URL for authentication",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "redirect_uri": {
                                "type": "string",
                                "description": "OAuth redirect URI (default: http://localhost:8000/auth)",
                                "default": "http://localhost:8000/auth"
                            }
                        }
                    }
                },
                {
                    "name": "authenticate_with_code",
                    "description": "Exchange OAuth code for access tokens",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "OAuth authorization code from Strava"
                            }
                        },
                        "required": ["code"]
                    }
                }
            ]
        return self._cached_tools
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls in legacy format."""
        try:
            result = await self.mcp_server.call_tool(tool_name, arguments)
            # Extract the actual result from MCP response format
            if isinstance(result, tuple) and len(result) == 2:
                # MCP returns (content_blocks, result_dict)
                return result[1].get('result', result[1])  # Extract result or return the dict
            return result
        except Exception as e:
            self.logger.error(f"Error in tool {tool_name}: {str(e)}")
            return {"error": str(e)}
    
    def _convert_streams_to_analysis_format(self, streams: Dict[str, Any], activity_detail: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Strava streams to a format suitable for analysis (legacy compatibility)."""
        if not streams:
            return {}
        
        # Extract trackpoints from streams
        trackpoints = []
        
        # Get stream data
        time_stream = streams.get("time", {}).get("data", [])
        distance_stream = streams.get("distance", {}).get("data", [])
        latlng_stream = streams.get("latlng", {}).get("data", [])
        altitude_stream = streams.get("altitude", {}).get("data", [])
        velocity_stream = streams.get("velocity_smooth", {}).get("data", [])
        heartrate_stream = streams.get("heartrate", {}).get("data", [])
        cadence_stream = streams.get("cadence", {}).get("data", [])
        watts_stream = streams.get("watts", {}).get("data", [])
        
        # Combine streams into trackpoints
        max_length = max(len(stream) for stream in [time_stream, distance_stream] if stream) if any([time_stream, distance_stream]) else 0
        
        for i in range(max_length):
            trackpoint = {}
            
            if i < len(time_stream):
                trackpoint["time"] = time_stream[i]
            if i < len(distance_stream):
                trackpoint["distance"] = distance_stream[i]
            if i < len(velocity_stream):
                trackpoint["speed"] = velocity_stream[i]
            if i < len(heartrate_stream):
                trackpoint["hr_value"] = heartrate_stream[i]
            if i < len(cadence_stream):
                trackpoint["cadence"] = cadence_stream[i]
            if i < len(watts_stream):
                trackpoint["watts"] = watts_stream[i]
            if i < len(altitude_stream):
                trackpoint["altitude"] = altitude_stream[i]
            if i < len(latlng_stream):
                trackpoint["latitude"] = latlng_stream[i][0]
                trackpoint["longitude"] = latlng_stream[i][1]
                
            trackpoints.append(trackpoint)
        
        return {
            "activity_id": activity_detail.get("id"),
            "trackpoints": trackpoints,
            "summary": {
                "total_time": activity_detail.get("elapsed_time"),
                "moving_time": activity_detail.get("moving_time"),
                "distance": activity_detail.get("distance"),
                "average_speed": activity_detail.get("average_speed"),
                "max_speed": activity_detail.get("max_speed")
            }
        }
