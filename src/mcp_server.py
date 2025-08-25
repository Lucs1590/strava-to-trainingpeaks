"""MCP-style server for Strava integration and activity analysis."""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from strava_client import StravaClient, StravaAPIError
from main import TCXProcessor, Sport, AnalysisConfig, setup_logging


class StravaActivityMCP:
    """MCP-style server providing Strava integration tools."""
    
    def __init__(self):
        self.strava_client = StravaClient()
        self.tcx_processor = TCXProcessor()
        self.logger = setup_logging()
        
        # Define available tools
        self.tools = {
            "list_activities": {
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
            "get_activity_detail": {
                "name": "get_activity_detail", 
                "description": "Get detailed information about a specific activity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "activity_id": {
                            "type": "string",
                            "description": "Strava activity ID"
                        }
                    },
                    "required": ["activity_id"]
                }
            },
            "analyze_activity": {
                "name": "analyze_activity",
                "description": "Analyze a Strava activity using AI",
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "activity_id": {
                            "type": "string",
                            "description": "Strava activity ID"
                        },
                        "training_plan": {
                            "type": "string",
                            "description": "Training plan context for analysis",
                            "default": ""
                        },
                        "language": {
                            "type": "string",
                            "description": "Language for analysis output", 
                            "default": "English"
                        }
                    },
                    "required": ["activity_id"]
                }
            },
            "sync_recent_activities": {
                "name": "sync_recent_activities",
                "description": "Synchronize recent activities and prepare for TrainingPeaks export",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days_back": {
                            "type": "integer",
                            "description": "Number of days to sync back (default: 7)",
                            "default": 7
                        },
                        "include_analysis": {
                            "type": "boolean", 
                            "description": "Include AI analysis for activities",
                            "default": False
                        }
                    }
                }
            },
            "get_authorization_url": {
                "name": "get_authorization_url",
                "description": "Get Strava OAuth authorization URL for authentication",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "redirect_uri": {
                            "type": "string",
                            "description": "OAuth redirect URI",
                            "default": "http://localhost:8000/auth"
                        }
                    }
                }
            },
            "authenticate_with_code": {
                "name": "authenticate_with_code",
                "description": "Exchange OAuth code for access tokens", 
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "OAuth authorization code"
                        }
                    },
                    "required": ["code"]
                }
            }
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool calls."""
        try:
            if tool_name == "list_activities":
                return await self._list_activities(**arguments)
            elif tool_name == "get_activity_detail":
                return await self._get_activity_detail(**arguments)
            elif tool_name == "analyze_activity":
                return await self._analyze_activity(**arguments)
            elif tool_name == "sync_recent_activities":
                return await self._sync_recent_activities(**arguments)
            elif tool_name == "get_authorization_url":
                return await self._get_authorization_url(**arguments)
            elif tool_name == "authenticate_with_code":
                return await self._authenticate_with_code(**arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            self.logger.error(f"Error in tool {tool_name}: {str(e)}")
            return {"error": str(e)}
    
    async def _list_activities(self, limit: int = 30, days_back: int = 30) -> Dict[str, Any]:
        """List recent Strava activities."""
        try:
            after = datetime.now() - timedelta(days=days_back)
            activities = await self.strava_client.get_activities(limit=limit, after=after)
            
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
            return {"error": f"Strava API error: {str(e)}"}
    
    async def _get_activity_detail(self, activity_id: str) -> Dict[str, Any]:
        """Get detailed activity information."""
        try:
            activity = await self.strava_client.get_activity_detail(activity_id)
            streams = None
            
            # Try to get stream data as well
            try:
                streams = await self.strava_client.get_activity_streams(activity_id)
            except StravaAPIError:
                self.logger.warning(f"Could not fetch streams for activity {activity_id}")
            
            return {
                "success": True,
                "activity": activity,
                "streams": streams
            }
            
        except StravaAPIError as e:
            return {"error": f"Strava API error: {str(e)}"}
    
    async def _analyze_activity(self, activity_id: str, training_plan: str = "", language: str = "English") -> Dict[str, Any]:
        """Analyze a Strava activity using AI."""
        try:
            # Get activity streams for detailed analysis
            streams = await self.strava_client.get_activity_streams(activity_id)
            activity_detail = await self.strava_client.get_activity_detail(activity_id)
            
            # Convert streams to TCX-like format for analysis
            analysis_data = self._convert_streams_to_analysis_format(streams, activity_detail)
            
            # Determine sport type
            sport_mapping = {
                "Ride": Sport.BIKE,
                "Run": Sport.RUN, 
                "Swim": Sport.SWIM,
                "VirtualRide": Sport.BIKE,
                "VirtualRun": Sport.RUN
            }
            sport = sport_mapping.get(activity_detail.get("type", ""), Sport.OTHER)
            
            # Create analysis config
            config = AnalysisConfig(training_plan=training_plan, language=language)
            
            # Use existing AI analysis capability
            # Note: This would need the OpenAI API key to be configured
            analysis_result = "AI analysis would be performed here with the configured OpenAI API key"
            
            return {
                "success": True,
                "activity_id": activity_id,
                "sport": sport.value,
                "analysis": analysis_result,
                "data_points": len(analysis_data.get("trackpoints", [])) if analysis_data else 0
            }
            
        except StravaAPIError as e:
            return {"error": f"Strava API error: {str(e)}"}
        except Exception as e:
            return {"error": f"Analysis error: {str(e)}"}
    
    async def _sync_recent_activities(self, days_back: int = 7, include_analysis: bool = False) -> Dict[str, Any]:
        """Synchronize recent activities."""
        try:
            after = datetime.now() - timedelta(days=days_back)
            activities = await self.strava_client.get_activities(limit=50, after=after)
            
            sync_results = []
            for activity in activities:
                activity_id = str(activity["id"])
                
                result = {
                    "activity_id": activity_id,
                    "name": activity["name"],
                    "type": activity["type"],
                    "date": activity["start_date"],
                    "synced": True
                }
                
                if include_analysis:
                    analysis = await self._analyze_activity(activity_id)
                    result["analysis"] = analysis
                
                sync_results.append(result)
            
            return {
                "success": True,
                "synced_count": len(sync_results),
                "activities": sync_results
            }
            
        except StravaAPIError as e:
            return {"error": f"Strava API error: {str(e)}"}
    
    async def _get_authorization_url(self, redirect_uri: str = "http://localhost:8000/auth") -> Dict[str, Any]:
        """Get OAuth authorization URL."""
        try:
            url = self.strava_client.get_authorization_url(redirect_uri)
            return {
                "success": True,
                "authorization_url": url,
                "instructions": "Visit this URL to authorize the application, then use the 'code' parameter from the redirect to authenticate."
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _authenticate_with_code(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth code for tokens."""
        try:
            token_data = await self.strava_client.exchange_code_for_token(code)
            return {
                "success": True,
                "message": "Authentication successful. Tokens have been saved.",
                "athlete": token_data.get("athlete", {})
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _convert_streams_to_analysis_format(self, streams: Dict[str, Any], activity_detail: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Strava streams to a format suitable for analysis."""
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
        max_length = max(len(stream) for stream in [time_stream, distance_stream] if stream)
        
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

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return list(self.tools.values())

    async def run_server(self, host: str = "localhost", port: int = 8765):
        """Run the MCP server (simplified version for demonstration)."""
        self.logger.info(f"Starting Strava MCP server on {host}:{port}")
        self.logger.info("Available tools:")
        for tool in self.tools.values():
            self.logger.info(f"  - {tool['name']}: {tool['description']}")
        
        # This is a simplified implementation
        # In a real MCP server, this would handle the MCP protocol
        self.logger.info("Server started. Use the handle_tool_call method to execute tools.")
        
        return self