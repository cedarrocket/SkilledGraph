"""Opt-in live acceptance of the five examples; only shipped synthetic fixtures."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from threading import Lock

from langchain_core.messages import HumanMessage
from skilledgraph.binding import load_file_object
from sgraph_chat_host.host_cn import create_model
from sgraph_chat_host.host_config_cn import model_options

ROOT = Path(__file__).resolve().parents[2]
CASES = ["12-evidence-assistant", "13-csv-auditor", "14-email-assistant", "15-parallel-code-review", "16-batch-digest"]


class Monitor:
    def __init__(self, model, calls, lock=None):
        self.model, self.calls = model, calls
        self.lock = lock or Lock()

    def bind_tools(self, tools, **kwargs):
        return Monitor(self.model.bind_tools(tools, **kwargs), self.calls, self.lock)

    def invoke(self, messages, config=None):
        with self.lock:
            if len(self.calls) >= 8:
                raise RuntimeError("Example exceeded its eight-call live test budget")
            entry = {"task": messages[0].text.splitlines()[0] if messages and messages[0].type == "system" else "worker"}
            self.calls.append(entry)
        reply = self.model.invoke(messages, config=config)
        entry.update(usage=reply.usage_metadata, tool_names=[call["name"] for call in reply.tool_calls],
                     finish_reason=reply.response_metadata.get("finish_reason"))
        if entry["finish_reason"] == "length":
            raise RuntimeError("Model output was truncated by the token limit")
        return reply


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--case", action="append", choices=CASES)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/development/PRACTICAL_AGENTS_LIVE_RESULTS.json")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required for real API calls")
    name = os.environ.get("SGRAPH_MODEL")
    if not name:
        parser.error("set SGRAPH_MODEL and connection variables explicitly")
    # Coding subscriptions are not used for these mixed-purpose acceptance cases.
    if "opencode.ai/zen/go" in os.environ.get("SGRAPH_BASE_URL", ""):
        parser.error("use a general-purpose model API for this mixed-purpose suite")
    secrets = [v for v in (model_options(base_dir=ROOT).get("api_key"), os.environ.get("DEEPSEEK_API_KEY"), os.environ.get("OPENAI_API_KEY")) if v]
    report = {"date": datetime.now(timezone.utc).isoformat(), "model": name, "cases": []}
    for case in args.case or CASES:
        path = ROOT / "examples" / case / "workflow_cn.md"
        calls = []
        item = {"name": case, "calls": calls}
        with tempfile.TemporaryDirectory() as directory:
            try:
                model = Monitor(create_model(name, base_dir=path.parent), calls)
                build = load_file_object("./host_cn.py:create_graph", base_dir=path.parent)
                initial = {"messages": [HumanMessage(content="发布前需要哪些检查，什么时候回滚？")]}
                approval = None
                if case.startswith("13-"):
                    initial = {"messages": [HumanMessage(content="审计账目并提出清洗建议。")], "csv_path": str(path.parent / "sample_cn.csv")}
                elif case.startswith("14-"):
                    initial = {"messages": [HumanMessage(content="你好，我被重复收费，想申请退款。")], "output_dir": directory}
                    approval = "yes"  # Explicit approval only for synthetic, temporary draft.
                elif case.startswith("15-"):
                    initial = {"messages": [HumanMessage(content=(path.parent / "sample_cn.py").read_text())]}
                elif case.startswith("16-"):
                    initial = {"messages": [HumanMessage(content=(path.parent / "sample_cn.md").read_text())], "results": []}
                execute = load_file_object("./practical_cn.py:execute", base_dir=ROOT / "examples/support")
                result = execute(build(path, model), initial, approval=approval)
                if case.startswith("12-"):
                    assert result["validation"] == "valid", "Source citations failed verification"
                    assert "release_cn.md" in result["messages"][-1].text, "Relevant source missing"
                elif case.startswith("13-"):
                    assert result["validation"] == "valid", "Metrics failed validation"
                    assert result["report"]["valid_total"] == "30.50"
                elif case.startswith("14-"):
                    assert "账单政策" in result["policy"] and result["approved"]
                    assert Path(result["artifact"]).read_text() == result["draft"]
                    item["draft"] = result["draft"]
                elif case.startswith("15-"):
                    assert len(calls) == 4, "Expected three review calls and one joined report"
                    assert "os.system" in result["messages"][-1].text, "Known security finding missing"
                else:
                    assert sorted(r["index"] for r in result["results"]) == [1, 2, 3]
                    assert len(calls) == 4
                item.update(passed=True, reply=result["messages"][-1].text)
                print(case + ": PASS", flush=True)
            except Exception as exc:
                error = str(exc)
                for secret in secrets:
                    error = error.replace(secret, "[REDACTED]")
                item.update(passed=False, error=error[:1200])
                print(case + ": FAIL (" + type(exc).__name__ + ")", flush=True)
        report["cases"].append(item)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if all(item["passed"] for item in report["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
