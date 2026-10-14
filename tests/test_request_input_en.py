"""Native interrupt semantics for the builtin text request backend."""
import asyncio
import tempfile
from pathlib import Path
import unittest

try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from langchain_core.messages import HumanMessage
except ImportError:
    raise unittest.SkipTest("requires runtime extra")

from skilledgraph import load_graph, parse_graph, BindingError, BuildError
from tests.test_execution_en import Model


class RequestInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "graph.md"
        self.config = {"configurable": {"thread_id": "test"}}

    def graph(self, payload, **kwargs):
        self.path.write_text(f"# [Node] Ask\n- **@uses**: request_input:{payload}\nIgnored body\n## [Transitions]\n- @Default -> @End\n", encoding="utf-8")
        return load_graph(self.path, compile_kwargs={"checkpointer": InMemorySaver()}, **kwargs)

    def test_literal_prompt_and_empty_string_resume(self):
        model = Model()
        graph = self.graph("请选择: A | B", model=model)
        first = graph.invoke({"messages": [HumanMessage(content="initial")]}, self.config)
        self.assertEqual(first["__interrupt__"][0].value, "请选择: A | B")
        self.assertEqual(model.calls, [])
        result = graph.invoke(Command(resume=""), self.config)
        self.assertEqual([m.content for m in result["messages"]], ["initial", ""])
        self.assertIsInstance(result["messages"][-1], HumanMessage)

    def test_json_string_prompt_keeps_parser_opaque(self):
        payload = r'"第一行\n第二行：\"格式\""'
        graph = self.graph(payload)
        self.assertEqual(parse_graph(self.path).nodes[0].setting("uses"), "request_input:" + payload)
        result = graph.invoke({"messages": []}, self.config)
        self.assertEqual(result["__interrupt__"][0].value, '第一行\n第二行："格式"')

    def test_invalid_and_empty_prompt_fail_at_binding(self):
        for payload in ("", '""', '"unterminated', '"ok" trailing'):
            with self.subTest(payload=payload), self.assertRaises(BindingError):
                self.graph(payload)

    def test_non_string_resume_is_not_stringified(self):
        graph = self.graph("question?")
        graph.invoke({"messages": []}, self.config)
        with self.assertRaisesRegex(TypeError, "must be a string"):
            graph.invoke(Command(resume={"approved": True}), self.config)

    def test_async_interrupt_and_resume(self):
        graph = self.graph("async?")
        async def run():
            result = await graph.ainvoke({"messages": []}, self.config)
            self.assertEqual(result["__interrupt__"][0].value, "async?")
            result = await graph.ainvoke(Command(resume="yes"), self.config)
            self.assertEqual(result["messages"][-1].content, "yes")
        asyncio.run(run())

    def test_router_sees_merged_reply_then_selects_table(self):
        self.path.write_text("# [Node] Ask\n- **@uses**: request_input:continue?\n- **@router**: python:./route.py:route\n## [Transitions]\n- yes -> Report\n- no -> @End\n# [Node] Report\nReply\n## [Transitions]\n- @Default -> @End\n", encoding="utf-8")
        (self.path.parent / "route.py").write_text('def route(state):\n    return state["messages"][-1].content\n', encoding="utf-8")
        model = Model()
        graph = load_graph(self.path, model=model, compile_kwargs={"checkpointer": InMemorySaver()})
        graph.invoke({"messages": []}, self.config)
        self.assertEqual(model.calls, [])
        graph.invoke(Command(resume="yes"), self.config)
        self.assertEqual(model.calls[0][-1].content, "yes")

    def test_messages_channel_required(self):
        from typing_extensions import TypedDict
        class State(TypedDict):
            value: int
        with self.assertRaisesRegex(BuildError, "messages"):
            self.graph("question?", state_schema=State)
