"""Model execution uses deterministic models; no network or credentials."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

try:
    import langgraph
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
except ImportError:
    raise unittest.SkipTest("requires runtime extra")
from typing_extensions import TypedDict

from skilledgraph import load_graph, RoutingError
from skilledgraph.execution import material_messages

ROOT = Path(__file__).resolve().parents[1]


class Model:
    def __init__(self, response="answer"):
        self.response = response
        self.calls = []

    def invoke(self, messages, config=None):
        self.calls.append(list(messages))
        return AIMessage(content=self.response(messages) if callable(self.response) else self.response)

    async def ainvoke(self, messages, config=None):
        await asyncio.sleep(0)
        return self.invoke(messages, config)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def graph(self, text):
        path = self.directory / "graph.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_prompt_history_and_body_not_saved(self):
        model = Model()
        graph = load_graph(ROOT / "examples/02-chain/workflow_en.md", model=model)
        result = graph.invoke({"messages": [HumanMessage(content="hello")]})
        self.assertEqual(len(model.calls), 2)
        self.assertIsInstance(model.calls[0][0], SystemMessage)
        self.assertEqual([m.content for m in model.calls[1][1:]], ["hello", "answer"])
        self.assertEqual([m.content for m in result["messages"]], ["hello", "answer", "answer"])

    def test_empty_prompt_still_invokes(self):
        model = Model()
        load_graph(self.graph("# [Node] A\n"), model=model).invoke({"messages": []})
        self.assertEqual(model.calls, [[]])

    def test_material_conversion(self):
        message = AIMessage(content="material", id="id", additional_kwargs={"extra": 1})
        self.assertIs(material_messages(message)[0], message)
        self.assertEqual(material_messages([message]), [message])
        for value in [None, []]:
            self.assertEqual(material_messages(value), [])
        for value, expected in [("", ""), ("hello", "hello"), (3, "3"),
                                ({"role": "assistant", "content": "x"}, '{"role": "assistant", "content": "x"}'),
                                ([1, 2], "[1, 2]")]:
            with self.subTest(value=value):
                result = material_messages(value)
                self.assertIsInstance(result[0], HumanMessage)
                self.assertEqual(result[0].content, expected)
        circular = []; circular.append(circular)
        self.assertEqual(material_messages(circular)[0].content, "[[...]]")

    def test_pyfunction_materials_order_and_single_invoke(self):
        (self.directory / "tools_en.py").write_text('def prepare(state):\n    return "material:" + state["messages"][-1].content\n', encoding="utf-8")
        path = self.graph("# [Node] A\n- **@uses**: pyfunction:./tools_en.py:prepare\nInstructions\n")
        model = Model()
        result = load_graph(path, model=model).invoke({"messages": [HumanMessage(content="input")]})
        self.assertEqual(len(model.calls), 1)
        self.assertEqual([m.content for m in model.calls[0]], ["Instructions", "input", "material:input"])
        self.assertEqual([m.content for m in result["messages"]], ["input", "material:input", "answer"])

    def test_pyfunction_none_still_calls_model(self):
        (self.directory / "tools_en.py").write_text('def prepare(state):\n    return None\n', encoding="utf-8")
        model = Model()
        graph = load_graph(self.graph("# [Node] A\n- **@uses**: pyfunction:./tools_en.py:prepare\n"), model=model)
        self.assertEqual(len(graph.invoke({"messages": []})["messages"]), 1)
        self.assertEqual(model.calls, [[]])

    def routing_graph(self, model, **kwargs):
        return load_graph(self.graph('''# [Node] Decide
Only yes or no.
## [Transitions]
- yes -> Yes
- no -> No
# [Node] Yes
YES
# [Node] No
NO
'''), model=model, **kwargs)

    def test_default_route_does_not_depend_on_reducer(self):
        from typing import Annotated
        def replace_with_redacted(left, right):
            return [AIMessage(content="redacted")]
        class State(TypedDict):
            messages: Annotated[list, replace_with_redacted]
        model = Model(lambda msgs: " yes \n" if msgs[0].content.startswith("Only") else msgs[0].content)
        result = self.routing_graph(model, state_schema=State).invoke({"messages": []})
        self.assertEqual(len(model.calls), 2)
        self.assertEqual(model.calls[1][0].content, "YES")
        self.assertEqual(result["messages"][0].content, "redacted")

    def test_raw_route_reply_is_saved(self):
        model = Model(lambda msgs: " yes \n" if msgs[0].content.startswith("Only") else "done")
        result = self.routing_graph(model).invoke({"messages": []})
        self.assertEqual([m.content for m in result["messages"]], [" yes \n", "done"])

    def test_route_invalid_text_not_guessed(self):
        for text in ['"yes"', '```yes```', 'yes because...', '']:
            with self.subTest(text=text), self.assertRaises(RoutingError):
                self.routing_graph(Model(text)).invoke({"messages": []})

    def test_concurrent_runs_do_not_share_route_values(self):
        def reply(messages):
            if messages[0].content.startswith("Only"):
                return messages[-1].content
            return messages[0].content.strip()
        graph = self.routing_graph(Model(reply))
        def run(key):
            result = graph.invoke({"messages": [HumanMessage(content=key)]})
            return result["messages"][-1].content
        keys = ["yes", "no"] * 12
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(list(pool.map(run, keys)), [key.upper() for key in keys])

    def test_async_pyfunction_and_model(self):
        (self.directory / "tools_en.py").write_text('async def prepare(state):\n    return "async material"\n', encoding="utf-8")
        model = Model()
        graph = load_graph(self.graph("# [Node] A\n- **@uses**: pyfunction:./tools_en.py:prepare\n"), model=model)
        result = asyncio.run(graph.ainvoke({"messages": []}))
        self.assertEqual([m.content for m in result["messages"]], ["async material", "answer"])
        with self.assertRaisesRegex(TypeError, "requires graph.ainvoke"):
            graph.invoke({"messages": []})

    def test_uses_overrides_do_not_implicitly_invoke_model(self):
        model = Model()
        def bind(payload, **kwargs):
            return lambda state: {"messages": [AIMessage(content="native")]}
        graph = load_graph(self.graph("# [Node] A\n- **@uses**: pyfunction:any\n"), model=model, bindings={"pyfunction": bind})
        graph.invoke({"messages": []})
        self.assertEqual(model.calls, [])

    def test_introductory_examples_execute(self):
        # Practical examples register tools/bindings or native edges in their
        # Hosts; their full CLI paths are covered by test_practical_agents.
        directories = [d for d in sorted((ROOT / "examples").glob("[0-9][0-9]-*")) if int(d.name[:2]) <= 11]
        self.assertEqual(len(directories), 11)
        for directory in directories:
            with self.subTest(example=directory.name):
                model = Model(lambda msgs: "enough" if directory.name.startswith(("03", "04")) and len([m for m in msgs if isinstance(m, AIMessage)]) == 0 else "answer")
                tools = None
                if directory.name.startswith("10"):
                    from skilledgraph.binding import load_file_object
                    model = load_file_object("./host_en.py:DemoModel", base_dir=directory)()
                    tools = [load_file_object("./host_en.py:add", base_dir=directory)]
                graph = load_graph(directory / "workflow_en.md", model=model, tools=tools)
                state = {"value": 0, "events": []} if directory.name.startswith("09") else {"messages": [HumanMessage(content="input")]}
                graph.invoke(state)

    def test_custom_overwrite_reducer_not_repaired(self):
        model = Model()
        graph = load_graph(ROOT / "examples/07-custom-state/workflow_en.md", model=model)
        result = graph.invoke({"messages": [HumanMessage(content="input")]})
        self.assertEqual([m.content for m in model.calls[1][1:]], ["answer"])
        self.assertEqual(len(result["messages"]), 1)

    def test_stream_and_checkpoint_after_routing(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command
        graph = self.routing_graph(Model(lambda msgs: "yes" if msgs[0].content.startswith("Only") else "done"),
                                   compile_kwargs={"checkpointer": InMemorySaver(), "interrupt_before": ["Yes"]})
        config = {"configurable": {"thread_id": "route"}}
        updates = list(graph.stream({"messages": []}, config, stream_mode="updates"))
        self.assertEqual(updates[0]["Decide"]["messages"][0].content, "yes")
        self.assertEqual(graph.get_state(config).next, ("Yes",))
        result = graph.invoke(None, config)
        self.assertEqual([m.content for m in result["messages"]], ["yes", "done"])


    def test_missing_messages_schema_is_build_error(self):
        from skilledgraph import BuildError
        class State(TypedDict):
            value: int
        with self.assertRaisesRegex(BuildError, "Schema with messages"):
            load_graph(self.graph("# [Node] A\nHello\n"), model=Model(), state_schema=State)

    def test_model_runtime_contract_errors(self):
        model = Model()
        model.invoke = lambda messages, config=None: "not a message"
        graph = load_graph(self.graph("# [Node] A\nHello\n"), model=model)
        with self.assertRaisesRegex(TypeError, "AIMessage"):
            graph.invoke({"messages": []})
        model.ainvoke = None
        with self.assertRaisesRegex(TypeError, "ainvoke"):
            asyncio.run(graph.ainvoke({"messages": []}))

    def test_native_model_stream_and_callbacks(self):
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        from langchain_core.callbacks import BaseCallbackHandler
        class Handler(BaseCallbackHandler):
            def __init__(self):
                self.tags = []
            def on_chat_model_start(self, serialized, messages, **kwargs):
                self.tags.extend(kwargs.get("tags", []))
        handler = Handler()
        graph = load_graph(self.graph("# [Node] A\nHello\n"), model=FakeListChatModel(responses=["abc"]))
        chunks = list(graph.stream({"messages": []}, {"callbacks": [handler], "tags": ["test-tag"]}, stream_mode="messages"))
        self.assertEqual("".join(message.content for message, metadata in chunks), "abc")
        self.assertIn("test-tag", handler.tags)

    def test_async_native_stream_and_concurrent_routes(self):
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        graph = load_graph(self.graph("# [Node] A\nHello\n"), model=FakeListChatModel(responses=["abc"]))
        async def stream():
            return [message.content async for message, metadata in graph.astream({"messages": []}, stream_mode="messages")]
        self.assertEqual("".join(asyncio.run(stream())), "abc")
        def reply(messages):
            return messages[-1].content if messages[0].content.startswith("Only") else messages[0].content
        graph = self.routing_graph(Model(reply))
        async def runs():
            return await asyncio.gather(*(graph.ainvoke({"messages": [HumanMessage(content=key)]}) for key in ["yes", "no"] * 5))
        self.assertEqual([r["messages"][-1].content for r in asyncio.run(runs())], ["YES", "NO"] * 5)

    def test_pyfunction_routes_from_model_not_material(self):
        (self.directory / "tools_en.py").write_text('def prepare(state):\n    return "not the route"\n', encoding="utf-8")
        path = self.graph("# [Node] A\n- **@uses**: pyfunction:./tools_en.py:prepare\nChoose yes\n## [Transitions]\n- yes -> @End\n")
        model = Model(" yes ")
        result = load_graph(path, model=model).invoke({"messages": []})
        self.assertEqual([m.content for m in result["messages"]], ["not the route", " yes "])
        self.assertEqual(len(model.calls), 1)

    def test_external_router_overrides_model_text_key(self):
        (self.directory / "tools_en.py").write_text('def route(state):\n    assert state["messages"][-1].content == "full answer"\n    return "yes"\n', encoding="utf-8")
        path = self.graph("# [Node] A\n- **@router**: python:./tools_en.py:route\nAnswer normally\n## [Transitions]\n- yes -> @End\n")
        model = Model("full answer")
        load_graph(path, model=model).invoke({"messages": []})
        self.assertEqual(len(model.calls), 1)
