"""Real stdio MCP transport, offline first; --live adds DeepSeek graph test."""
import argparse
import asyncio
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from skilledgraph import load_graph
from sgraph_chat_host.host import create_model

# This standalone test directory intentionally isn't imported by unittest.
from host import adapter_for

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def check(value, message):
    if not value:
        raise AssertionError(message)


def process_is_running(pid):
    """Check liveness without sending a signal or terminating a Windows process."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: PID no longer exists.
                return False
            raise ctypes.WinError(error)
        try:
            status = kernel32.WaitForSingleObject(handle, 0)
            if status == 0:  # WAIT_OBJECT_0: process has exited.
                return False
            if status == 258:  # WAIT_TIMEOUT: process is still running.
                return True
            raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def decoded(value):
    if isinstance(value, ToolMessage):
        value = value.text
    if isinstance(value, list):
        value = next(block["text"] for block in value if block["type"] == "text")
    return json.loads(value) if isinstance(value, str) else value


class OfflineModel:
    def invoke(self, messages, config=None):
        completed = sum(isinstance(m, ToolMessage) for m in messages)
        if completed < 2:
            args = {"a": 17, "b": 25} if completed == 0 else {"a": 2, "b": 3}
            return AIMessage("", tool_calls=[{
                "name": "mcp_add", "args": args, "id": f"offline-{completed}", "type": "tool_call",
            }])
        return AIMessage("offline complete")

    async def ainvoke(self, messages, config=None):
        return self.invoke(messages, config)


async def run(live):
    results = []
    server_pid = None
    async with adapter_for(BASE) as adapter:
        tools = await adapter.list_tools()
        check([t.name for t in tools] == ["mcp_add"], "Wrong tool catalog")
        results.append({"case": "discovery", "passed": True, "tools": [t.name for t in tools]})
        direct = decoded(await tools[0].ainvoke({"a": 17, "b": 25}))
        check(direct["sum"] == 42 and direct["call_count"] == 1, "Wrong direct result")
        server_pid = direct["server_pid"]
        check(server_pid != os.getpid(), "Server was not an external subprocess")
        check(process_is_running(server_pid), "MCP server is not running during its session")
        results.append({"case": "direct_call", "passed": True, "result": direct})

        graph = load_graph(BASE / "workflow.md", model=OfflineModel(), tools=tools)
        messages = (await graph.ainvoke({"messages": [HumanMessage("offline")]},
                                       {"recursion_limit": 12}))["messages"]
        replies = [m for m in messages if isinstance(m, ToolMessage)]
        values = [decoded(m) for m in replies]
        check([v["sum"] for v in values] == [42, 5], "Wrong graph tool results")
        check([v["call_count"] for v in values] == [2, 3], "MCP session was not preserved")
        check(all(v["server_pid"] == server_pid for v in values), "Server restarted")
        check([m.tool_call_id for m in replies] == ["offline-0", "offline-1"], "Wrong result IDs")
        check(messages[-1].text == "offline complete", "Graph did not finish")
        results.append({"case": "graph_two_rounds", "passed": True, "tool_results": values})

        if live:
            model = create_model(os.environ.get("SGRAPH_MODEL", "deepseek:deepseek-chat"), base_dir=BASE)
            records = []
            class Monitor:
                def invoke(self, messages, config=None):
                    raise AssertionError("MCP tools require this demo's async execution")
                async def ainvoke(self, messages, config=None):
                    reply = await bound.ainvoke(messages, config=config)
                    records.append({"model": reply.response_metadata.get("model_name"),
                                    "usage": reply.usage_metadata, "tool_calls": reply.tool_calls,
                                    "text": reply.text})
                    return reply
            bound = model.bind_tools(tools)
            graph = load_graph(BASE / "workflow.md", model=Monitor(), tools=tools)
            messages = (await graph.ainvoke({"messages": [HumanMessage("请调用 mcp_add 计算17加25，然后告诉我结果。")]},
                                           {"recursion_limit": 12}))["messages"]
            replies = [m for m in messages if isinstance(m, ToolMessage)]
            check(replies, "Model did not call MCP tool")
            check(any(decoded(m)["sum"] == 42 for m in replies), "Wrong live tool result")
            ids = {call["id"] for m in messages if isinstance(m, AIMessage) for call in m.tool_calls}
            check(all(m.tool_call_id in ids for m in replies), "Unmatched live tool IDs")
            check(not messages[-1].tool_calls and "42" in messages[-1].text, "Wrong final answer")
            results.append({"case": "deepseek_mcp_graph", "passed": True,
                            "calls": records, "tool_results": [decoded(m) for m in replies],
                            "final": messages[-1].text})
    # stdio context exit must reap the local subprocess.
    check(not process_is_running(server_pid), "MCP server still running after context exit")
    results.append({"case": "server_cleanup", "passed": True})
    return {"date_utc": datetime.now(timezone.utc).isoformat(), "live": live,
            "versions": {name: importlib.metadata.version(name) for name in ("langchain", "fastmcp", "mcp")},
            "results": results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Also call configured model API")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/development/MCP_LOCAL_RESULTS.json")
    args = parser.parse_args()
    result = asyncio.run(asyncio.wait_for(run(args.live), timeout=120))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(result['results'])} MCP checks")
    for item in result["results"]:
        print(item["case"], "PASS")


if __name__ == "__main__":
    main()
