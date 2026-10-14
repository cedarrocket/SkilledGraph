"""Temporary local stdio MCP server; synthetic arithmetic only."""
import os
from fastmcp import FastMCP

server = FastMCP("SkilledGraph local MCP test")
calls = 0


@server.tool()
def mcp_add(a: int, b: int) -> dict:
    """Add two integers and return the sum; no external data or side effects."""
    global calls
    calls += 1
    return {"sum": a + b, "call_count": calls, "server_pid": os.getpid()}


if __name__ == "__main__":
    server.run(transport="stdio", show_banner=False)
