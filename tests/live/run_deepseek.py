"""Explicit live acceptance suite. Run only with --run (incurs API usage).

No user files are sent. Tools operate solely on synthetic local test data.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from skilledgraph import load_graph
from sgraph_chat_host.host import create_model, run_chat

ROOT = Path(__file__).resolve().parents[2]
TOOL_GRAPH = """# [Node] Assistant
{prompt}
## [Transitions]
- @ToolCalls -> Tools
- @Otherwise -> @End
# [ToolNode] Tools
- **@tools**: all
## [Transitions]
- @Default -> Assistant
"""


@tool
def add(a: int, b: int) -> int:
    """Add two integers. Use this tool rather than calculating yourself."""
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers. Use this tool rather than calculating yourself."""
    return a * b


@tool
def lookup_secret(label: str) -> int:
    """Look up a synthetic test value. Only label alpha is available."""
    if label != "alpha":
        raise ValueError("Unknown test label")
    return 37


@tool
def checked_lookup(label: Literal["valid"]) -> str:
    """Look up a synthetic value. Only label valid is permitted and returns RECOVERED."""
    if label != "valid":
        raise ValueError("Try label valid")
    return "RECOVERED"


class Monitor:
    def __init__(self, model, records):
        self.model, self.records = model, records

    def record(self, reply, messages):
        self.records.append({
            "input_messages": [{"type": m.type, "text": m.text} for m in messages],
            "model": reply.response_metadata.get("model_name"),
            "usage": reply.usage_metadata,
            "text": reply.text,
            "tool_calls": reply.tool_calls,
        })
        return reply

    def invoke(self, messages, config=None):
        return self.record(self.model.invoke(messages, config=config), messages)

    async def ainvoke(self, messages, config=None):
        return self.record(await self.model.ainvoke(messages, config=config), messages)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_protocol(messages):
    pending = set()
    calls = []
    for message in messages:
        if isinstance(message, AIMessage):
            require(not pending, "AI reply appeared before all tool results")
            pending = {call["id"] for call in message.tool_calls}
            require(len(pending) == len(message.tool_calls), "Duplicate tool call ID")
            calls.extend(message.tool_calls)
        elif isinstance(message, ToolMessage):
            require(message.tool_call_id in pending, "Unmatched tool result ID")
            pending.remove(message.tool_call_id)
    require(not pending, "Unresolved tool requests at end")
    require(isinstance(messages[-1], AIMessage) and not messages[-1].tool_calls, "Missing final model answer")
    return calls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Allow real API calls")
    parser.add_argument("--case", action="append", help="Run selected case names only; repeatable")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/development/DEEPSEEK_LIVE_RESULTS.json")
    args = parser.parse_args()
    if not args.run:
        parser.error("Explicit --run is required; this suite uses the configured API")
    records = []
    results = []
    name = os.environ.get("SGRAPH_MODEL", "deepseek:deepseek-chat")
    model = create_model(name, base_dir=ROOT)
    started = datetime.now(timezone.utc).isoformat()
    # Error strings are redacted before recording.
    key = os.environ.get("SGRAPH_API_KEY", "")
    if os.environ.get("SGRAPH_API_KEY_FILE"):
        key_path = Path(os.environ["SGRAPH_API_KEY_FILE"]).expanduser()
        if not key_path.is_absolute():
            key_path = ROOT / key_path
        key = key_path.read_text().strip()

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        def graph(text, tools=None):
            path = base / "workflow.md"
            path.write_text(text)
            bound = model.bind_tools(tools) if tools else model
            return load_graph(path, model=Monitor(bound, records), tools=tools)

        def run_case(case, action):
            if args.case and case not in args.case:
                return
            offset = len(records)
            before = time.monotonic()
            try:
                detail = action()
                result = {"case": case, "passed": True, "detail": detail}
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                if key:
                    error = error.replace(key, "[REDACTED]")
                result = {"case": case, "passed": False, "error": error[:2000]}
            result["seconds"] = round(time.monotonic() - before, 3)
            result["calls"] = records[offset:]
            results.append(result)
            print(f"{case}: {'PASS' if result['passed'] else 'FAIL'} ({result['seconds']}s)", flush=True)
            # Save after each case, so partial progress survives interruption.
            save()

        def save():
            usage = [r["usage"] for r in records if r.get("usage")]
            report = {"started_utc": started, "requested_model": name,
                      "served_models": sorted({r["model"] for r in records if r.get("model")}),
                      "passed": sum(r["passed"] for r in results), "total": len(results),
                      "api_calls_in_process": len(records),
                      "tokens_in_process": {field: sum(u.get(field, 0) for u in usage)
                                            for field in ("input_tokens", "output_tokens", "total_tokens")},
                      "results": results,
                      "scope": "Synthetic test data only. CLI child call excluded from in-process token totals. No MCP."}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

        def ordinary():
            g = graph("# [Node] A\nReply exactly SG_LIVE_OK.\n## [Transitions]\n- @Default -> @End\n")
            result = g.invoke({"messages": [HumanMessage("test")]})
            require(result["messages"][-1].text.strip() == "SG_LIVE_OK", "Unexpected response")
            return {"reply": result["messages"][-1].text}
        run_case("ordinary_prompt", ordinary)

        def history():
            offset = len(records)
            g = graph("""# [Node] First
回答“蓝鲸”，不要加其他文字。
## [Transitions]
- @Default -> Second
# [Node] Second
用一句话说明前一条助手回复提到的动物，必须包含这个动物的名称。
## [Transitions]
- @Default -> @End
""")
            messages = g.invoke({"messages": [HumanMessage("开始")]})["messages"]
            require(len(records) == offset + 2, "Wrong model call count")
            second_input = records[offset + 1]["input_messages"]
            require(second_input[-1] == {"type": "ai", "text": messages[1].text}, "Previous reply not passed")
            require(second_input[-2]["type"] == "human", "Original input not passed")
            require("蓝鲸" in messages[1].text and "蓝鲸" in messages[-1].text, "Model did not use previous animal")
            return {"replies": [m.text for m in messages[1:]], "second_input": second_input}
        run_case("chain_history", history)

        def routing(text, expected, table):
            heading = "# [Node] Route\nReturn only yes if user text contains apple, otherwise return only no.\n## [Transitions]\n"
            transitions = "| key | target |\n| --- | --- |\n| yes | Yes |\n| no | No |\n" if table else "- yes -> Yes\n- no -> No\n"
            ending = """# [Node] Yes
Reply exactly SG_YES.
## [Transitions]
- @Default -> @End
# [Node] No
Reply exactly SG_NO.
## [Transitions]
- @Default -> @End
"""
            messages = graph(heading + transitions + ending).invoke({"messages": [HumanMessage(text)]})["messages"]
            require(messages[-1].text.strip() == expected, "Wrong branch")
            return {"route": messages[1].text, "reply": messages[-1].text}
        run_case("routing_list_yes", lambda: routing("apple", "SG_YES", False))
        run_case("routing_list_no", lambda: routing("orange", "SG_NO", False))
        run_case("routing_table_yes", lambda: routing("apple", "SG_YES", True))
        run_case("routing_table_no", lambda: routing("orange", "SG_NO", True))

        def material():
            (base / "material.py").write_text('def prepare(state):\n    return "Synthetic lookup result: SG_MATERIAL_842"\n')
            g = graph("# [Node] A\n- **@uses**: pyfunction:./material.py:prepare\nReply only with the SG_ token from the synthetic lookup result.\n## [Transitions]\n- @Default -> @End\n")
            messages = g.invoke({"messages": [HumanMessage("look up")]})["messages"]
            require(messages[-1].text.strip() == "SG_MATERIAL_842", "Material not used")
            require(messages[-2].text.startswith("Synthetic lookup result"), "Material not saved")
            return {"reply": messages[-1].text}
        run_case("pyfunction_material", material)

        def tools_case(prompt, user, selected, expected_names, expected_value, asynchronous=False):
            g = graph(TOOL_GRAPH.format(prompt=prompt), tools=selected)
            initial = {"messages": [HumanMessage(user)]}
            config = {"recursion_limit": 12}
            result = asyncio.run(g.ainvoke(initial, config)) if asynchronous else g.invoke(initial, config)
            messages = result["messages"]
            calls = validate_protocol(messages)
            require(set(expected_names).issubset({c["name"] for c in calls}), "Required tool not called")
            require(expected_value in messages[-1].text, "Wrong final result")
            return {"called_tools": [c["name"] for c in calls],
                    "tool_results": [{"id": m.tool_call_id, "content": m.content, "status": m.status}
                                     for m in messages if isinstance(m, ToolMessage)],
                    "final": messages[-1].text}
        run_case("single_tool_sync", lambda: tools_case(
            "Always use add for arithmetic. After tool result, answer with only the number.",
            "Use add to calculate 17 + 25.", [add], ["add"], "42"))
        run_case("two_tools", lambda: tools_case(
            "Use both requested tools. After results, output the two results.",
            "Call add for 17+25 and multiply for 6*7, then report both.", [add, multiply], ["add", "multiply"], "42"))
        run_case("dependent_tool_rounds", lambda: tools_case(
            "Use lookup_secret first. Then use add to add 5 to the returned value. Never guess the lookup result. Answer only the final number.",
            "Look up alpha, then add 5.", [lookup_secret, add], ["lookup_secret", "add"], "42"))
        run_case("single_tool_async", lambda: tools_case(
            "Always use add, then answer only the number.",
            "Use add to calculate 19+23.", [add], ["add"], "42", True))

        def recover():
            detail = tools_case(
                "For this validation test, deliberately request checked_lookup with label invalid first, even though the schema only permits valid. After the error ToolMessage, request label valid. Report the returned value.",
                "Run the lookup and recover from its error.", [checked_lookup], ["checked_lookup"], "RECOVERED")
            require(any(r["status"] == "error" for r in detail["tool_results"]), "Missing native error ToolMessage")
            require(any(r["status"] == "success" for r in detail["tool_results"]), "Missing recovered result")
            return detail
        run_case("tool_argument_error_recovery", recover)

        def business_error():
            @tool
            def fail_business(value: int) -> str:
                """A synthetic tool that raises a business error."""
                raise ValueError("SG_SYNTHETIC_BUSINESS_ERROR")
            g = graph(TOOL_GRAPH.format(prompt="Always call fail_business with value 1."), tools=[fail_business])
            try:
                g.invoke({"messages": [HumanMessage("Call the tool.")]}, {"recursion_limit": 8})
            except ValueError as exc:
                require(str(exc) == "SG_SYNTHETIC_BUSINESS_ERROR", "Unexpected exception")
                return {"expected_exception": "ValueError", "message": str(exc)}
            raise AssertionError("Business error was swallowed")
        run_case("tool_business_error_propagation", business_error)

        def host_display():
            g = graph("# [Node] A\nReply exactly SG_HOST_OK.\n## [Transitions]\n- @Default -> @End\n")
            output = io.StringIO()
            run_chat(g, input_stream=io.StringIO("host test"), output_stream=output)
            require("[A] SG_HOST_OK" in output.getvalue(), "Host output missing")
            return {"stdout": output.getvalue()}
        run_case("host_pipe", host_display)

        def cli():
            path = base / "cli.md"
            path.write_text("# [Node] A\nReply exactly SG_CLI_OK.\n## [Transitions]\n- @Default -> @End\n")
            result = subprocess.run([sys.executable, "-m", "skilledgraph", str(path)], input="cli test",
                                    capture_output=True, text=True, timeout=90)
            require(result.returncode == 0, "CLI failed: " + result.stderr)
            require("[A] SG_CLI_OK" in result.stdout, "CLI output mismatch")
            return {"stdout": result.stdout, "api_calls": 1}
        run_case("cli_environment_connection", cli)
    print(f"Completed: {sum(r['passed'] for r in results)}/{len(results)} passed", flush=True)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
