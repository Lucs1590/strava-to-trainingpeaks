#!/usr/bin/env python3
"""
MCP Server for Strava Integration.
Implements a Model Context Protocol server providing Strava activity synchronization and analysis tools.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import StravaActivityMCP


class SimpleMCPServer:
    """Simplified MCP server implementation."""
    
    def __init__(self):
        self.strava_mcp = StravaActivityMCP()
        self.logger = logging.getLogger(__name__)
        
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        return self.strava_mcp.get_available_tools()
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool with arguments."""
        return await self.strava_mcp.handle_tool_call(name, arguments)
    
    async def run_interactive_session(self):
        """Run an interactive session for testing the MCP server."""
        print("Strava MCP Server - Interactive Mode")
        print("====================================")
        print("Type 'help' for available commands or 'quit' to exit")
        
        while True:
            try:
                command = input("\nmcp> ").strip()
                
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'help':
                    await self._show_help()
                elif command.lower() == 'list-tools':
                    tools = await self.list_tools()
                    print(json.dumps(tools, indent=2))
                elif command.startswith('call '):
                    await self._handle_call_command(command[5:])
                else:
                    print("Unknown command. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    async def _show_help(self):
        """Show help information."""
        print("\nAvailable Commands:")
        print("==================")
        print("help                    - Show this help")
        print("list-tools             - List all available MCP tools")
        print("call <tool> <args>     - Call a tool with JSON arguments")
        print("quit                   - Exit the server")
        
        print("\nAvailable Tools:")
        tools = await self.list_tools()
        for tool in tools:
            print(f"  {tool['name']:20} - {tool['description']}")
        
        print("\nExample calls:")
        print("call list_activities {}")
        print('call get_activity_detail {"activity_id": "12345"}')
        print('call analyze_activity {"activity_id": "12345", "language": "English"}')
    
    async def _handle_call_command(self, args: str):
        """Handle a tool call command."""
        try:
            # Parse the command: tool_name {json_args}
            parts = args.split(' ', 1)
            if len(parts) != 2:
                print("Usage: call <tool_name> <json_arguments>")
                return
            
            tool_name = parts[0]
            try:
                arguments = json.loads(parts[1])
            except json.JSONDecodeError as e:
                print(f"Invalid JSON arguments: {e}")
                return
            
            result = await self.call_tool(tool_name, arguments)
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"Error calling tool: {e}")


async def main():
    """Main function to run the MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Strava MCP Server")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run in interactive mode for testing")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = SimpleMCPServer()
    
    if args.interactive:
        await server.run_interactive_session()
    else:
        # In a real implementation, this would start the MCP protocol server
        print(f"Starting MCP server on {args.host}:{args.port}")
        print("Available tools:")
        tools = await server.list_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        print("\nServer ready. In a real MCP implementation, this would listen for MCP protocol messages.")
        print("For testing, use --interactive mode or the mcp_cli.py script.")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server...")


if __name__ == "__main__":
    asyncio.run(main())