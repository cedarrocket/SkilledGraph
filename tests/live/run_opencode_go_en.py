"""Explicit live Go acceptance. Reads credentials locally; never records them."""
import argparse
from datetime import datetime, timezone
import ast
import json
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="authorize live quota usage")
    parser.add_argument("--auth-file", type=Path, default=Path.home() / ".local/share/opencode/auth.json")
    parser.add_argument("--model", default="glm-5.3-flash")
    parser.add_argument("--output", type=Path, default=Path("docs/development/OPENCODE_GO_LIVE_RESULTS.json"))
    args = parser.parse_args()
    if not args.run:
        parser.error("live requests require --run")
    credentials = json.loads(args.auth_file.read_text())["opencode-go"]
    if credentials.get("type") != "api" or not credentials.get("key"):
        raise ValueError("opencode-go API credentials required")
    key = credentials["key"]
    from langchain_core.messages import HumanMessage
    from langchain_core.tools import tool
    from skilledgraph import load_graph
    from sgraph_chat_host.host_en import create_model
    import httpx

    requests = []
    def observe(request):
        if request.method == "POST":
            if request.url.host != "opencode.ai" or request.url.path != "/zen/go/v1/chat/completions":
                raise ValueError("Live test refuses an unexpected API endpoint")
            if request.headers.get("User-Agent") != "sgraph-harness-agent/0.1.0.dev0" or not request.headers.get("x-opencode-session"):
                raise ValueError("Live test requires its own User-Agent and session header")
            requests.append({"path": request.url.path, "user_agent": request.headers.get("User-Agent"),
                             "session": request.headers.get("x-opencode-session")})
    report = {"date": datetime.now(timezone.utc).isoformat(), "provider": "opencode-go", "model": args.model,
              "base_url": "https://opencode.ai/zen/go/v1", "cases": [], "requests": requests}
    def record(name, run):
        try:
            data = run()
            report["cases"].append({"name": name, "passed": True, **data})
            print(name + ": PASS")
        except Exception as exc:
            # Some native errors include API response text. Redact the key.
            report["cases"].append({"name": name, "passed": False,
                                     "error": str(exc).replace(key, "[REDACTED]")[:1200]})
            print(name + ": FAIL (" + type(exc).__name__ + ")")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    with tempfile.TemporaryDirectory() as directory, httpx.Client(timeout=60, event_hooks={"request": [observe]}) as client:
        root = Path(directory)
        def model():
            # Explicit connection parameters, no copying credentials into repo/config.
            return create_model("openai:" + args.model, base_dir=root, connection_options={
                "base_url": report["base_url"], "api_key": key, "use_responses_api": False,
                "timeout": 60, "max_retries": 0, "max_tokens": 1024, "http_client": client})
        def basic():
            connection = model()
            session = connection.default_headers["x-opencode-session"]
            graph_path = root / "basic.md"
            graph_path.write_text("# [Node] Code\nYou are a coding assistant. Return only a Python function add(a, b) that returns a + b. No markdown.\n## [Transitions]\n- @Default -> @End\n")
            result = load_graph(graph_path, model=connection).invoke({"messages": [HumanMessage(content="Implement add(a, b).") ]})
            reply = result["messages"][-1]
            ast.parse(reply.text)
            assert "def add" in reply.text and "+" in reply.text, "Unexpected Python reply"
            return {"reply": reply.text, "usage": reply.usage_metadata, "session": session}
        record("coding_prompt", basic)

        def tools():
            connection = model()
            session = connection.default_headers["x-opencode-session"]
            calls = []
            @tool
            def read_snippet() -> str:
                """Read the small synthetic Python function under review."""
                calls.append(True)
                return "def add(a, b):\n    return a - b\n"
            graph_path = root / "tools.md"
            graph_path.write_text("# [Node] Assistant\nYou are a coding assistant. First call read_snippet to inspect the example function. After the tool result, provide its corrected Python implementation. Do not call the tool again.\n## [Transitions]\n- @ToolCalls -> ExecuteTools\n- @Otherwise -> @End\n# [ToolNode] ExecuteTools\n- **@tools**: [read_snippet]\n## [Transitions]\n- @Default -> Assistant\n")
            graph = load_graph(graph_path, model=connection.bind_tools([read_snippet]), tools=[read_snippet])
            result = graph.invoke({"messages": [HumanMessage(content="Fix the addition function using the tool to inspect it.")]}, {"recursion_limit": 6})
            assert len(calls) == 1, "Expected one real tool execution"
            ai = [m for m in result["messages"] if m.type == "ai"]
            assert len(ai) == 2 and ai[0].tool_calls and not ai[-1].tool_calls, "Unexpected tool loop"
            assert "def add" in ai[-1].text and "+" in ai[-1].text, "Correction missing"
            outputs = [m for m in result["messages"] if m.type == "tool"]
            assert outputs[0].tool_call_id == ai[0].tool_calls[0]["id"], "Tool call ID mismatch"
            return {"reply": ai[-1].text, "tool_calls": len(calls), "session": session,
                    "usage": [m.usage_metadata for m in ai]}
        record("tool_calling", tools)
    return 0 if all(case["passed"] for case in report["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
