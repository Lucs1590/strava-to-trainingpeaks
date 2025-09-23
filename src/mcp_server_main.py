#!/usr/bin/env python3
"""
MCP Server for Strava Integration using official MCP package.
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

from mcp_server import create_strava_mcp_server, StravaActivityMCP

async def run_stdio_server():
    """Run the MCP server using stdio transport."""
    mcp = create_strava_mcp_server()

    # Run the server using stdio transport (standard MCP protocol)
    await mcp.run_stdio_async()


async def run_sse_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the MCP server using SSE transport."""
    mcp = create_strava_mcp_server()

    print(f"Starting Strava MCP server on {host}:{port}")
    print("Available tools:")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # Run the server using SSE transport
    await mcp.run_sse_async(host=host, port=port)


class SimpleMCPServer:
    """Simplified MCP server implementation for interactive testing."""

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
                    print(f"\nAvailable tools ({len(tools)}):")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool['description']}")
                elif command.lower().startswith('call '):
                    await self._handle_tool_call(command[5:])
                else:
                    print("Unknown command. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

    async def _show_help(self):
        """Show help information."""
        print("\nAvailable commands:")
        print("  help           - Show this help message")
        print("  list-tools     - List all available MCP tools")
        print("  call <tool>    - Call a tool (interactive mode)")
        print("  quit/exit/q    - Exit the interactive session")
        print("\nExample tool calls:")
        print("  call list_activities")
        print("  call get_authorization_url")

    async def _handle_tool_call(self, tool_command: str):
        """Handle interactive tool calls."""
        try:
            # Parse the tool command
            parts = tool_command.strip().split()
            if not parts:
                print("Please specify a tool name")
                return

            tool_name = parts[0]

            # Get tool definition to understand required parameters
            tools = await self.list_tools()
            tool_def = next((t for t in tools if t['name'] == tool_name), None)

            if not tool_def:
                print(f"Unknown tool: {tool_name}")
                return

            # Collect arguments interactively
            arguments = {}
            input_schema = tool_def.get('inputSchema', {})
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])

            print(f"Calling tool: {tool_name}")
            if properties:
                print("Parameters:")
                for param_name, param_def in properties.items():
                    param_type = param_def.get('type', 'string')
                    param_desc = param_def.get('description', '')
                    default_value = param_def.get('default')
                    is_required = param_name in required

                    prompt = f"  {param_name}"
                    if param_desc:
                        prompt += f" ({param_desc})"
                    if default_value is not None:
                        prompt += f" [default: {default_value}]"
                    if is_required:
                        prompt += " (required)"
                    prompt += ": "

                    value = input(prompt).strip()

                    if value:
                        # Type conversion
                        if param_type == 'integer':
                            try:
                                arguments[param_name] = int(value)
                            except ValueError:
                                print(
                                    f"Invalid integer value for {param_name}")
                                return
                        elif param_type == 'boolean':
                            arguments[param_name] = value.lower() in [
                                'true', '1', 'yes', 'y']
                        else:
                            arguments[param_name] = value
                    elif is_required:
                        print(f"Required parameter {param_name} not provided")
                        return
                    elif default_value is not None:
                        arguments[param_name] = default_value

            # Call the tool
            print(f"\nCalling {tool_name} with arguments: {arguments}")
            result = await self.call_tool(tool_name, arguments)

            # Display result
            print(f"\nResult:")
            print(json.dumps(result, indent=2, default=str))

        except Exception as e:
            print(f"Error calling tool: {str(e)}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Strava MCP Server")
    parser.add_argument("--mode", choices=["stdio", "sse", "interactive"],
                        default="stdio", help="Server mode")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host for SSE mode")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for SSE mode")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode (shorthand for --mode interactive)")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    if args.interactive:
        args.mode = "interactive"

    if args.mode == "stdio":
        await run_stdio_server()
    elif args.mode == "sse":
        await run_sse_server(args.host, args.port)
    elif args.mode == "interactive":
        server = SimpleMCPServer()
        await server.run_interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
