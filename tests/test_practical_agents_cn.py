"""Practical agents: real tools, validators, branches and files; scripted models."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

try:
    from langchain_core.messages import AIMessage, HumanMessage
except ImportError:
    raise unittest.SkipTest("requires runtime extra")

from skilledgraph.binding import load_file_object

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CASES = ["12-evidence-assistant", "13-csv-auditor", "14-email-assistant", "15-parallel-code-review", "16-batch-digest"]


def host(case, entry):
    return load_file_object(f"./host_cn.py:{entry}", base_dir=EXAMPLES / case)


def model(reply):
    return load_file_object("./practical_cn.py:DemoModel", base_dir=EXAMPLES / "support")(reply)


def run(case, instance, initial, **kwargs):
    path = EXAMPLES / case / "workflow_cn.md"
    graph = host(case, "create_graph")(path, instance, **kwargs)
    execute = load_file_object("./practical_cn.py:execute", base_dir=EXAMPLES / "support")
    return execute(graph, initial)


class PracticalAgentTests(unittest.TestCase):
    def test_all_five_demo_clis(self):
        for case in CASES:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run([sys.executable, "-X", "utf8", "-m", "skilledgraph", str(EXAMPLES / case / "workflow_cn.md"),
                    "--", "--demo", "--output", directory], capture_output=True, text=True, encoding="utf-8", timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Offline demo", result.stderr)
                self.assertTrue(result.stdout.strip())

    def test_evidence_search_and_source_validation(self):
        case = CASES[0]
        instance = model(host(case, "demo_reply"))
        result = run(case, instance, {"messages": [HumanMessage(content="发布与回滚？")]})
        self.assertEqual(result["validation"], "valid")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(len(instance.calls), 2)
        self.assertIn("[release_cn.md]", result["messages"][-1].text)

    def test_evidence_unknown_citation_is_retried_then_rejected(self):
        case = CASES[0]
        instance = model(lambda messages: AIMessage(content="发布规则 [invented.md]"))
        result = run(case, instance, {"messages": [HumanMessage(content="发布？")]})
        self.assertEqual(result["validation"], "failed")
        self.assertEqual(result["attempts"], 3)
        self.assertIn("未通过", result["messages"][-1].text)

    def test_empty_knowledge_base_reports_no_evidence(self):
        case = CASES[0]
        with tempfile.TemporaryDirectory() as directory:
            result = run(case, model(host(case, "demo_reply")),
                         {"messages": [HumanMessage(content="发布？")]}, data=Path(directory))
        self.assertEqual(result["validation"], "valid")
        self.assertIn("无资料", result["messages"][-1].text)

    def test_csv_metrics_and_validated_report(self):
        case = CASES[1]
        result = run(case, model(host(case, "demo_reply")), {"messages": [HumanMessage(content="audit")],
                     "csv_path": str(EXAMPLES / case / "sample_cn.csv")})
        self.assertEqual(result["metrics"]["valid_total"], "30.50")
        self.assertEqual(result["metrics"]["invalid_rows"], [5])
        self.assertEqual(result["metrics"]["duplicate_ids"], ["A2"])
        self.assertEqual(result["metrics"]["missing_customer_rows"], [6])
        self.assertEqual(result["validation"], "valid")

    def test_csv_report_repair_uses_validator_feedback(self):
        case = CASES[1]
        calls = []
        def reply(messages):
            calls.append(messages)
            if len(calls) == 1:
                return AIMessage(content='{"rows":999}')
            return host(case, "demo_reply")(messages)
        result = run(case, model(reply), {"messages": [HumanMessage(content="audit")],
                     "csv_path": str(EXAMPLES / case / "sample_cn.csv")})
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["validation"], "valid")
        self.assertTrue(any("校验失败" in m.text for m in calls[1] if m.type == "human"))

    def test_csv_invalid_report_loop_is_bounded(self):
        case = CASES[1]
        result = run(case, model(lambda messages: AIMessage(content="not JSON")),
                     {"messages": [HumanMessage(content="audit")], "csv_path": str(EXAMPLES / case / "sample_cn.csv")})
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["validation"], "failed")
        self.assertIn("未通过", result["messages"][-1].text)

    def email(self, approval, directory):
        case = CASES[2]
        graph = host(case, "create_graph")(EXAMPLES / case / "workflow_cn.md", model(host(case, "demo_reply")))
        execute = load_file_object("./practical_cn.py:execute", base_dir=EXAMPLES / "support")
        return execute(graph, {"messages": [HumanMessage(content="重复收费，申请退款")], "output_dir": directory}, approval=approval)

    def test_email_approved_draft_is_saved_after_interrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.email("yes", directory)
            self.assertTrue(result["approved"])
            self.assertEqual(Path(result["artifact"]).read_text(encoding="utf-8"), result["draft"])
            self.assertIn("账单政策", result["policy"])
            self.assertEqual(len(list(Path(directory).glob("*.md"))), 1)

    def test_email_rejection_does_not_write_any_file(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.email("no", directory)
            self.assertFalse(result["approved"])
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertNotIn("artifact", result)

    def test_review_branches_are_concurrent_and_report_waits_for_all(self):
        case = CASES[3]
        barrier = Barrier(3, timeout=5)
        joined = []
        def reply(messages):
            if "TASK: REVIEW_REPORT" not in messages[0].text:
                self.assertFalse(any(m.type == "ai" for m in messages))
                barrier.wait()
            else:
                joined.append([m.text for m in messages if m.type == "ai"])
            return host(case, "demo_reply")(messages)
        source = (EXAMPLES / case / "sample_cn.py").read_text(encoding="utf-8")
        result = run(case, model(reply), {"messages": [HumanMessage(content=source)]})
        self.assertEqual(len(joined), 1)
        self.assertEqual(len(joined[0]), 3)
        self.assertIn("os.system", result["messages"][-1].text)

    def test_batch_worker_inputs_are_isolated_and_results_ordered(self):
        case = CASES[4]
        seen = []
        def reply(messages):
            if "TASK: DIGEST_WORKER" in messages[0].text:
                self.assertEqual(len(messages), 2)
                self.assertNotIn("\n---\n", messages[-1].text)
                return AIMessage(content="summary:" + messages[-1].text)
            data = json.loads(messages[-1].text)
            seen.append(data["documents"])
            return AIMessage(content="joined")
        result = run(case, model(reply), {"messages": [HumanMessage(content="one\n---\ntwo\n---\nthree")], "results": []})
        self.assertEqual([item["index"] for item in seen[0]], [1, 2, 3])
        self.assertEqual([item["summary"] for item in seen[0]], ["summary:one", "summary:two", "summary:three"])
        self.assertEqual(len(result["results"]), 3)
        self.assertFalse(any(m.text == "one\n---\ntwo\n---\nthree" for m in result["messages"]))

    def test_batch_async_native_binding(self):
        case = CASES[4]
        instance = model(host(case, "demo_reply"))
        graph = host(case, "create_graph")(EXAMPLES / case / "workflow_cn.md", instance)
        result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="one\n---\ntwo")], "results": []}))
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(len(instance.calls), 3)

    def test_csv_missing_amount_and_wrong_headers(self):
        case = CASES[1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("id,amount,customer\nX,2.00,A\nY,,B\n", encoding="utf-8")
            result = run(case, model(host(case, "demo_reply")), {"messages": [HumanMessage(content="audit")], "csv_path": str(path)})
            self.assertEqual(result["metrics"]["invalid_rows"], [3])
            self.assertEqual(result["metrics"]["valid_total"], "2.00")
            path.write_text("wrong,headers\na,b\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires"):
                run(case, model(host(case, "demo_reply")), {"messages": [HumanMessage(content="audit")], "csv_path": str(path)})

    def test_email_other_categories_load_corresponding_policies(self):
        case = CASES[2]
        for request, policy in (("出现故障", "技术政策"), ("请提供说明", "一般政策")):
            with self.subTest(request=request), tempfile.TemporaryDirectory() as directory:
                graph = host(case, "create_graph")(EXAMPLES / case / "workflow_cn.md", model(host(case, "demo_reply")))
                execute = load_file_object("./practical_cn.py:execute", base_dir=EXAMPLES / "support")
                result = execute(graph, {"messages": [HumanMessage(content=request)], "output_dir": directory}, approval="no")
                self.assertIn(policy, result["policy"])

    def test_batch_rejects_empty_document_batch(self):
        case = CASES[4]
        with self.assertRaisesRegex(ValueError, "No documents"):
            run(case, model(host(case, "demo_reply")), {"messages": [HumanMessage(content="\n---\n")], "results": []})
