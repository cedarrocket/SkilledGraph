"""Real ToolNode integration with deterministic model requests."""
import asyncio
from pathlib import Path
import tempfile
import unittest
try:
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
except ImportError:
    raise unittest.SkipTest("requires runtime extra")

from skilledgraph import load_graph, build_graph, BindingError, BuildError, RoutingError
from skilledgraph.binding import load_file_object

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = """# [Node] Assistant
Use tools.
## [Transitions]
- @ToolCalls -> Exec
- @Otherwise -> @End
# [ToolNode] Exec
- **@tools**: all
## [Transitions]
- @Default -> Assistant
"""


@tool
def add(a: int, b: int) -> int:
    """Add integers."""
    return a + b


def request(name="add", ident="call1", **args):
    return {"name": name, "args": args or {"a": 2, "b": 3}, "id": ident, "type": "tool_call"}


class Model:
    def __init__(self, calls=None):
        self.requests = calls if calls is not None else [request()]
        self.inputs = []

    def invoke(self, messages, config=None):
        self.inputs.append(messages)
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content="complete")
        return AIMessage(content="request text", tool_calls=self.requests)

    async def ainvoke(self, messages, config=None):
        await asyncio.sleep(0)
        return self.invoke(messages, config)


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def path(self, text=WORKFLOW):
        path = self.directory / "graph.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_cycle_and_updates(self):
        model = Model()
        graph = load_graph(self.path(), model=model, tools=[add])
        updates = list(graph.stream({"messages": [HumanMessage("calculate")]}, stream_mode="updates"))
        self.assertEqual([next(iter(u)) for u in updates], ["Assistant", "Exec", "Assistant"])
        result = updates[1]["Exec"]["messages"][0]
        self.assertEqual((result.content, result.tool_call_id), ("5", "call1"))
        self.assertEqual(len(model.inputs), 2)
        self.assertIsInstance(model.inputs[1][-1], ToolMessage)

    def test_multiple_calls_and_async_tool(self):
        @tool
        async def twice(value: int) -> int:
            """Double an integer."""
            return value * 2
        model = Model([request(), request("twice", "call2", value=4)])
        graph = load_graph(self.path(), model=model, tools=[add, twice])
        result = asyncio.run(graph.ainvoke({"messages": [HumanMessage("go")]}))
        replies = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        self.assertEqual({m.tool_call_id: m.content for m in replies}, {"call1": "5", "call2": "8"})
        self.assertEqual(result["messages"][-1].content, "complete")

    def test_select_subset_unknown_and_duplicate(self):
        @tool
        def unused() -> str:
            """Must not execute."""
            raise AssertionError("not selected")
        graph = load_graph(self.path(WORKFLOW.replace(": all", ": [add]")), model=Model(), tools=[add, unused])
        self.assertEqual(graph.invoke({"messages": [HumanMessage("go")]})["messages"][-1].content, "complete")
        with self.assertRaises(BindingError):
            build_graph(self.path(WORKFLOW.replace(": all", ": [missing]")), model=Model(), tools=[add])
        with self.assertRaises(BindingError):
            build_graph(self.path(), model=Model(), tools=[add, add])

    def test_empty_and_callable_tools(self):
        def subtract(a: int, b: int) -> int:
            """Subtract integers."""
            return a - b
        graph = load_graph(self.path(), model=Model([request("subtract")]), tools=[subtract])
        result = graph.invoke({"messages": [HumanMessage("go")]})
        self.assertEqual(result["messages"][2].content, "-1")
        # ToolNode can be entered directly, without any model.
        graph = load_graph(self.path("# [ToolNode] Exec\n- **@tools**: []\n## [Transitions]\n- @Default -> @End\n"))
        result = graph.invoke({"messages": [AIMessage("", tool_calls=[])]})
        self.assertEqual(len(result["messages"]), 1)

    def test_toolnode_ignores_body_and_checks_schema(self):
        text = "# [ToolNode] Exec\n- **@tools**: [add]\nDo not invoke a model.\n## [Transitions]\n- @Default -> @End\n"
        graph = load_graph(self.path(text), tools=[add])
        result = graph.invoke({"messages": [AIMessage("", tool_calls=[request()])]})
        self.assertEqual(result["messages"][-1].content, "5")
        from typing_extensions import TypedDict
        class State(TypedDict):
            value: int
        with self.assertRaises(BuildError):
            build_graph(self.path(text), tools=[add], state_schema=State)

    def test_tool_signal_bypasses_router_and_router_handles_final(self):
        invocations = []
        async def router(state):
            invocations.append(state["messages"][-1])
            return "done"
        text = WORKFLOW.replace("Use tools.", "- **@router**: test:route").replace("@Otherwise", "done")
        graph = load_graph(self.path(text), model=Model(), tools=[add],
                           bindings={"test": lambda *a, **kw: router})
        result = asyncio.run(graph.ainvoke({"messages": [HumanMessage("go")]}))
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0].content, "complete")
        self.assertEqual(result["messages"][-1].content, "complete")

    def test_fallback_and_named_route_priority(self):
        text = """# [Node] A
## [Transitions]
- @Otherwise -> Wrong
- good -> @End
# [Node] Wrong
- **@uses**: test:wrong
"""
        class TextModel:
            def invoke(self, messages, config=None):
                return AIMessage("good")
        def wrong(state):
            raise AssertionError("fallback should not win")
        graph = load_graph(self.path(text), model=TextModel(), bindings={"test": lambda *a, **kw: wrong})
        self.assertEqual(graph.invoke({"messages": []})["messages"][-1].content, "good")

    def test_literal_signal_does_not_spoof(self):
        class TextModel:
            def invoke(self, messages, config=None):
                return AIMessage("@ToolCalls")
        graph = load_graph(self.path(), model=TextModel(), tools=[add])
        result = graph.invoke({"messages": []})
        self.assertEqual(len(result["messages"]), 1)

    def test_missing_fallback_errors_and_no_implicit_tool_edges(self):
        class TextModel:
            def invoke(self, messages, config=None):
                return AIMessage("free answer")
        with self.assertRaises(RoutingError):
            load_graph(self.path(WORKFLOW.replace("- @Otherwise -> @End\n", "")),
                       model=TextModel(), tools=[add]).invoke({"messages": []})
        graph = load_graph(self.path("# [Node] A\n## [Transitions]\n- @Default -> @End\n"),
                           model=Model(), tools=[add])
        result = graph.invoke({"messages": [HumanMessage("go")]})
        self.assertEqual(len(result["messages"]), 2)
        self.assertTrue(result["messages"][-1].tool_calls)

    def test_checkpoint_resume(self):
        model = Model()
        graph = load_graph(self.path(), model=model, tools=[add],
                           compile_kwargs={"checkpointer": InMemorySaver(), "interrupt_before": ["Exec"]})
        config = {"configurable": {"thread_id": "tools"}}
        graph.invoke({"messages": [HumanMessage("go")]}, config)
        self.assertEqual(graph.get_state(config).next, ("Exec",))
        result = graph.invoke(None, config)
        self.assertEqual(result["messages"][-1].content, "complete")
        self.assertEqual(len(model.inputs), 2)

    def test_native_command_tool(self):
        from langchain_core.tools import InjectedToolCallId
        from typing import Annotated
        @tool
        def update(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
            """Return a native state update."""
            return Command(update={"messages": [ToolMessage("updated", tool_call_id=tool_call_id)]})
        model = Model([{"name": "update", "args": {}, "id": "u", "type": "tool_call"}])
        result = load_graph(self.path(), model=model, tools=[update]).invoke({"messages": [HumanMessage("go")]})
        self.assertEqual(result["messages"][2].content, "updated")

    def test_python_node_signal_and_router_exception(self):
        def node(state):
            return {"messages": [AIMessage("", tool_calls=[request()])]}
        text = WORKFLOW.replace("Use tools.", "- **@uses**: test:node").replace("- @Default -> Assistant", "- @Default -> @End")
        graph = load_graph(self.path(text), tools=[add], bindings={"test": lambda *a, **kw: node})
        self.assertEqual(graph.invoke({"messages": []})["messages"][-1].content, "5")
        def bad_router(state):
            raise RuntimeError("router exploded")
        text = "# [Node] A\n- **@router**: test:route\n## [Transitions]\n- @Otherwise -> @End\n"
        class TextModel:
            def invoke(self, messages, config=None):
                return AIMessage("answer")
        graph = load_graph(self.path(text), model=TextModel(), bindings={"test": lambda *a, **kw: bad_router})
        with self.assertRaisesRegex(RuntimeError, "router exploded"):
            graph.invoke({"messages": []})

    def test_standard_example(self):
        path = ROOT / "examples/10-tool-calling/workflow_cn.md"
        model = load_file_object("./host_cn.py:DemoModel", base_dir=path.parent)()
        add_tool = load_file_object("./host_cn.py:add", base_dir=path.parent)
        result = load_graph(path, model=model, tools=[add_tool]).invoke({"messages": [HumanMessage("go")]})
        self.assertEqual(result["messages"][-1].content, "结果是 5")

    def test_reducer_merged_state_is_signal_source(self):
        from typing import Annotated
        from typing_extensions import TypedDict
        def redact(old, new):
            return [AIMessage("redacted")]
        class State(TypedDict):
            messages: Annotated[list, redact]
        graph = load_graph(self.path(), model=Model(), tools=[add], state_schema=State)
        result = graph.invoke({"messages": [HumanMessage("go")]})
        self.assertEqual([m.content for m in result["messages"]], ["redacted"])

    def test_pyfunction_and_toolnode_router(self):
        (self.directory / "prepare.py").write_text('def prepare(state):\n    return "material"\n', encoding="utf-8")
        text = WORKFLOW.replace("Use tools.", "- **@uses**: pyfunction:./prepare.py:prepare")
        # Choose finish at ToolNode through its explicit native router.
        text = text.replace("- **@tools**: all", "- **@tools**: all\n- **@router**: test:route")
        text = text.replace("- @Default -> Assistant", "- finish -> @End")
        def route(state):
            self.assertIsInstance(state["messages"][-1], ToolMessage)
            return "finish"
        result = load_graph(self.path(text), model=Model(), tools=[add],
                            bindings={"test": lambda *a, **kw: route}).invoke({"messages": []})
        self.assertEqual([m.content for m in result["messages"]], ["material", "request text", "5"])

    def test_no_eager_calls_or_model_binding(self):
        model = Model()
        model.bind_tools = lambda *a, **kw: self.fail("Host owns model binding")
        build_graph(self.path(), model=model, tools=[add])
        self.assertEqual(model.inputs, [])

    def test_missing_tool_is_native_error_message(self):
        # The model's advertised tools need not equal the executor's selection.
        graph = load_graph(self.path(WORKFLOW.replace(": all", ": []")), model=Model(), tools=[add])
        result = graph.invoke({"messages": [HumanMessage("go")]})
        tool_reply = result["messages"][2]
        self.assertIsInstance(tool_reply, ToolMessage)
        self.assertEqual(tool_reply.status, "error")
        self.assertEqual(tool_reply.tool_call_id, "call1")

    def test_native_business_exception_propagates(self):
        @tool
        def failing(value: int) -> str:
            """Raise a synthetic business exception."""
            raise ValueError("synthetic business failure")
        graph = load_graph(self.path(), model=Model([request("failing", value=1)]), tools=[failing])
        with self.assertRaisesRegex(ValueError, "synthetic business failure"):
            graph.invoke({"messages": [HumanMessage("go")]})

    def test_native_argument_error_is_tool_message(self):
        # Missing required argument is handled by the native default handler.
        model = Model([{"name": "add", "args": {"a": 1}, "id": "bad", "type": "tool_call"}])
        result = load_graph(self.path(), model=model, tools=[add]).invoke({"messages": [HumanMessage("go")]})
        reply = result["messages"][2]
        self.assertIsInstance(reply, ToolMessage)
        self.assertEqual((reply.status, reply.tool_call_id), ("error", "bad"))
