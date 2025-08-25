"""MCP server for Strava integration and activity analysis using official MCP package."""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from strava_client import StravaClient, StravaAPIError
from trainingpeaks_client import TrainingPeaksClient, TrainingPeaksAPIError
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
    trainingpeaks_client = TrainingPeaksClient()
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

    # TrainingPeaks Tools
    
    @mcp.tool()
    async def get_trainingpeaks_auth_info() -> Dict[str, Any]:
        """Get TrainingPeaks authentication status and required credentials.
        
        Returns:
            Dictionary containing authentication status and setup instructions
        """
        try:
            auth_info = trainingpeaks_client.get_auth_info()
            return {
                "success": True,
                "auth_info": auth_info
            }
        except Exception as e:
            logger.error(f"Error in get_trainingpeaks_auth_info: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_trainingpeaks_athlete() -> Dict[str, Any]:
        """Get TrainingPeaks athlete information.
        
        Returns:
            Dictionary containing athlete profile data
        """
        try:
            athlete_info = await trainingpeaks_client.get_athlete_info()
            return {
                "success": True,
                "athlete": athlete_info
            }
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in get_trainingpeaks_athlete: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_trainingpeaks_athlete: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def list_trainingpeaks_workouts(days_back: int = 30, limit: int = 50) -> Dict[str, Any]:
        """List recent workouts from TrainingPeaks.
        
        Args:
            days_back: Number of days to look back (default: 30)
            limit: Maximum number of workouts to retrieve (default: 50)
            
        Returns:
            Dictionary containing success status and list of workouts
        """
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            end_date = datetime.now()
            
            workouts = await trainingpeaks_client.get_workouts(
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return {
                "success": True,
                "count": len(workouts),
                "workouts": workouts
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in list_trainingpeaks_workouts: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in list_trainingpeaks_workouts: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_trainingpeaks_workout_detail(workout_id: str) -> Dict[str, Any]:
        """Get detailed information about a TrainingPeaks workout.
        
        Args:
            workout_id: The TrainingPeaks workout ID
            
        Returns:
            Dictionary containing detailed workout information
        """
        try:
            workout = await trainingpeaks_client.get_workout_detail(workout_id)
            return {
                "success": True,
                "workout": workout
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in get_trainingpeaks_workout_detail: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_trainingpeaks_workout_detail: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def upload_workout_to_trainingpeaks(workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upload a workout to TrainingPeaks.
        
        Args:
            workout_data: Workout data in TrainingPeaks format
            
        Returns:
            Dictionary containing upload result
        """
        try:
            result = await trainingpeaks_client.upload_workout(workout_data)
            return {
                "success": True,
                "upload_result": result
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in upload_workout_to_trainingpeaks: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in upload_workout_to_trainingpeaks: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def sync_strava_to_trainingpeaks(activity_id: str, include_tcx: bool = True) -> Dict[str, Any]:
        """Sync a Strava activity to TrainingPeaks.
        
        Args:
            activity_id: The Strava activity ID to sync
            include_tcx: Whether to include TCX data for better accuracy (default: True)
            
        Returns:
            Dictionary containing sync result
        """
        try:
            # Get Strava activity details
            strava_activity = await strava_client.get_activity_detail(activity_id)
            
            tcx_content = None
            if include_tcx:
                try:
                    # Try to get streams and convert to TCX
                    streams = await strava_client.get_activity_streams(activity_id)
                    if streams:
                        # Convert streams to TCX format using the processor
                        sport = Sport.from_strava_type(strava_activity.get("type", "Run"))
                        tcx_content = tcx_processor.convert_strava_to_tcx(strava_activity, streams, sport)
                except Exception as e:
                    logger.warning(f"Could not generate TCX for activity {activity_id}: {str(e)}")
            
            # Sync to TrainingPeaks
            sync_result = await trainingpeaks_client.sync_from_strava(strava_activity, tcx_content)
            
            return {
                "success": True,
                "activity_id": activity_id,
                "sync_result": sync_result
            }
            
        except StravaAPIError as e:
            logger.error(f"Strava API error in sync_strava_to_trainingpeaks: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in sync_strava_to_trainingpeaks: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in sync_strava_to_trainingpeaks: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def bulk_sync_strava_to_trainingpeaks(days_back: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Bulk sync recent Strava activities to TrainingPeaks.
        
        Args:
            days_back: Number of days to look back for activities (default: 7)
            limit: Maximum number of activities to sync (default: 10)
            
        Returns:
            Dictionary containing bulk sync results
        """
        try:
            # Get recent Strava activities
            after = datetime.now() - timedelta(days=days_back)
            strava_activities = await strava_client.get_activities(limit=limit, after=after)
            
            sync_results = []
            for activity in strava_activities:
                try:
                    result = await sync_strava_to_trainingpeaks(str(activity["id"]), include_tcx=True)
                    sync_results.append({
                        "activity_id": activity["id"],
                        "activity_name": activity.get("name", "Unknown"),
                        "status": "success" if result.get("success") else "error",
                        "result": result
                    })
                except Exception as e:
                    sync_results.append({
                        "activity_id": activity["id"],
                        "activity_name": activity.get("name", "Unknown"),
                        "status": "error",
                        "error": str(e)
                    })
            
            successful_syncs = len([r for r in sync_results if r["status"] == "success"])
            failed_syncs = len([r for r in sync_results if r["status"] == "error"])
            
            return {
                "success": True,
                "total_activities": len(strava_activities),
                "successful_syncs": successful_syncs,
                "failed_syncs": failed_syncs,
                "results": sync_results
            }
            
        except Exception as e:
            logger.error(f"Error in bulk_sync_strava_to_trainingpeaks: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_training_plans() -> Dict[str, Any]:
        """Get training plans from TrainingPeaks.
        
        Returns:
            Dictionary containing list of training plans
        """
        try:
            plans = await trainingpeaks_client.get_training_plans()
            return {
                "success": True,
                "count": len(plans),
                "plans": plans
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in get_training_plans: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_training_plans: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_planned_workouts(days_ahead: int = 30) -> Dict[str, Any]:
        """Get planned workouts from TrainingPeaks training plans.
        
        Args:
            days_ahead: Number of days ahead to look for planned workouts (default: 30)
            
        Returns:
            Dictionary containing planned workouts
        """
        try:
            start_date = datetime.now()
            end_date = datetime.now() + timedelta(days=days_ahead)
            
            planned_workouts = await trainingpeaks_client.get_planned_workouts(
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "success": True,
                "count": len(planned_workouts),
                "planned_workouts": planned_workouts
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in get_planned_workouts: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_planned_workouts: {str(e)}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_training_metrics(days_back: int = 30) -> Dict[str, Any]:
        """Get training metrics and analytics from TrainingPeaks.
        
        Args:
            days_back: Number of days to look back for metrics (default: 30)
            
        Returns:
            Dictionary containing training metrics
        """
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            end_date = datetime.now()
            
            metrics = await trainingpeaks_client.get_metrics(
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "success": True,
                "metrics": metrics
            }
            
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in get_training_metrics: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_training_metrics: {str(e)}")
            return {"error": str(e)}

    return mcp


# Legacy class for backward compatibility with existing tests
class StravaActivityMCP:
    """Legacy MCP-style server for backward compatibility."""
    
    def __init__(self):
        self.mcp_server = create_strava_mcp_server()
        self.strava_client = StravaClient()
        self.trainingpeaks_client = TrainingPeaksClient()
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
                },
                # TrainingPeaks Tools
                {
                    "name": "get_trainingpeaks_auth_info",
                    "description": "Get TrainingPeaks authentication status and required credentials",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_trainingpeaks_athlete",
                    "description": "Get TrainingPeaks athlete information",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "list_trainingpeaks_workouts",
                    "description": "List recent workouts from TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back (default: 30)",
                                "default": 30
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of workouts to retrieve (default: 50)",
                                "default": 50
                            }
                        }
                    }
                },
                {
                    "name": "get_trainingpeaks_workout_detail",
                    "description": "Get detailed information about a TrainingPeaks workout",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "workout_id": {
                                "type": "string",
                                "description": "The TrainingPeaks workout ID"
                            }
                        },
                        "required": ["workout_id"]
                    }
                },
                {
                    "name": "upload_workout_to_trainingpeaks",
                    "description": "Upload a workout to TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "workout_data": {
                                "type": "object",
                                "description": "Workout data in TrainingPeaks format"
                            }
                        },
                        "required": ["workout_data"]
                    }
                },
                {
                    "name": "sync_strava_to_trainingpeaks",
                    "description": "Sync a Strava activity to TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "activity_id": {
                                "type": "string",
                                "description": "The Strava activity ID to sync"
                            },
                            "include_tcx": {
                                "type": "boolean",
                                "description": "Whether to include TCX data for better accuracy (default: True)",
                                "default": True
                            }
                        },
                        "required": ["activity_id"]
                    }
                },
                {
                    "name": "bulk_sync_strava_to_trainingpeaks",
                    "description": "Bulk sync recent Strava activities to TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back for activities (default: 7)",
                                "default": 7
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of activities to sync (default: 10)",
                                "default": 10
                            }
                        }
                    }
                },
                {
                    "name": "get_training_plans",
                    "description": "Get training plans from TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_planned_workouts",
                    "description": "Get planned workouts from TrainingPeaks training plans",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "days_ahead": {
                                "type": "integer",
                                "description": "Number of days ahead to look for planned workouts (default: 30)",
                                "default": 30
                            }
                        }
                    }
                },
                {
                    "name": "get_training_metrics",
                    "description": "Get training metrics and analytics from TrainingPeaks",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "description": "Number of days to look back for metrics (default: 30)",
                                "default": 30
                            }
                        }
                    }
                }
            ]
        return self._cached_tools
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls in legacy format."""
        # Initialize the clients needed for the tools
        strava_client = StravaClient()
        trainingpeaks_client = TrainingPeaksClient()
        tcx_processor = TCXProcessor()
        logger = setup_logging()
        
        try:
            # Handle Strava tools
            if tool_name == "list_activities":
                after = datetime.now() - timedelta(days=arguments.get("days_back", 30))
                activities = await strava_client.get_activities(
                    limit=arguments.get("limit", 30), 
                    after=after
                )
                
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
            
            elif tool_name == "get_activity_detail":
                activity = await strava_client.get_activity_detail(arguments["activity_id"])
                streams = None
                try:
                    streams = await strava_client.get_activity_streams(arguments["activity_id"])
                except StravaAPIError:
                    logger.warning(f"Could not fetch streams for activity {arguments['activity_id']}")
                
                return {
                    "success": True,
                    "activity": activity,
                    "streams": streams
                }
            
            elif tool_name == "get_authorization_url":
                auth_url = strava_client.get_authorization_url(
                    arguments.get("redirect_uri", "http://localhost:8000/auth")
                )
                return {
                    "success": True,
                    "authorization_url": auth_url,
                    "redirect_uri": arguments.get("redirect_uri", "http://localhost:8000/auth")
                }
            
            elif tool_name == "authenticate_with_code":
                token_data = await strava_client.exchange_code_for_tokens(arguments["code"])
                return {
                    "success": True,
                    "athlete_id": token_data.get("athlete", {}).get("id"),
                    "athlete_name": token_data.get("athlete", {}).get("firstname", "") + " " + token_data.get("athlete", {}).get("lastname", ""),
                    "scope": token_data.get("scope"),
                    "expires_at": token_data.get("expires_at")
                }
            
            # Handle TrainingPeaks tools
            elif tool_name == "get_trainingpeaks_auth_info":
                auth_info = trainingpeaks_client.get_auth_info()
                return {
                    "success": True,
                    "auth_info": auth_info
                }
            
            elif tool_name == "get_trainingpeaks_athlete":
                athlete_info = await trainingpeaks_client.get_athlete_info()
                return {
                    "success": True,
                    "athlete": athlete_info
                }
            
            elif tool_name == "list_trainingpeaks_workouts":
                start_date = datetime.now() - timedelta(days=arguments.get("days_back", 30))
                end_date = datetime.now()
                
                workouts = await trainingpeaks_client.get_workouts(
                    start_date=start_date,
                    end_date=end_date,
                    limit=arguments.get("limit", 50)
                )
                
                return {
                    "success": True,
                    "count": len(workouts),
                    "workouts": workouts
                }
            
            elif tool_name == "sync_strava_to_trainingpeaks":
                strava_activity = await strava_client.get_activity_detail(arguments["activity_id"])
                
                tcx_content = None
                if arguments.get("include_tcx", True):
                    try:
                        streams = await strava_client.get_activity_streams(arguments["activity_id"])
                        if streams:
                            sport = Sport.from_strava_type(strava_activity.get("type", "Run"))
                            tcx_content = tcx_processor.convert_strava_to_tcx(strava_activity, streams, sport)
                    except Exception as e:
                        logger.warning(f"Could not generate TCX for activity {arguments['activity_id']}: {str(e)}")
                
                sync_result = await trainingpeaks_client.sync_from_strava(strava_activity, tcx_content)
                
                return {
                    "success": True,
                    "activity_id": arguments["activity_id"],
                    "sync_result": sync_result
                }
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except StravaAPIError as e:
            logger.error(f"Strava API error in {tool_name}: {str(e)}")
            return {"error": f"Strava API error: {str(e)}"}
        except TrainingPeaksAPIError as e:
            logger.error(f"TrainingPeaks API error in {tool_name}: {str(e)}")
            return {"error": f"TrainingPeaks API error: {str(e)}"}
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
