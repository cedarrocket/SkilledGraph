"""Single-run MCP Host. Session stays alive until graph execution finishes."""
import asyncio
import os
import sys

from fastmcp.client.transports import StdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from skilledgraph import load_graph
from sgraph_chat_host.host import create_model


def adapter_for(base_dir):
    # Do not inherit the Host's provider credentials into this local tool server.
    env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT") if name in os.environ}
    return MCPAdapter(StdioTransport(command=sys.executable,
                                     args=[str(base_dir / "server.py")], env=env, keep_alive=False))


async def run(graph_path, text):
    model = create_model(os.environ.get("SGRAPH_MODEL", "deepseek:deepseek-chat"),
                         base_dir=graph_path.parent)
    async with adapter_for(graph_path.parent) as adapter:
        tools = await adapter.list_tools()
        graph = load_graph(graph_path, model=model.bind_tools(tools), tools=tools)
        result = await graph.ainvoke({"messages": [HumanMessage(text)]}, {"recursion_limit": 12})
        for message in result["messages"]:
            if isinstance(message, ToolMessage):
                print(f"[MCP result] {message.text}", flush=True)
            elif isinstance(message, AIMessage) and message.text:
                print(f"[Assistant] {message.text}", flush=True)
        return result


def main(graph_path, argv):
    if argv:
        raise ValueError("MCP demo Host accepts no arguments")
    if sys.stdin.isatty():
        print("> ", end="", file=sys.stderr, flush=True)
        text = sys.stdin.readline().rstrip("\r\n")
    else:
        text = sys.stdin.read()
    if text.strip():
        asyncio.run(run(graph_path, text))
    return 0
