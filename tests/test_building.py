"""Native runtime integration tests. Install .[runtime] to run these."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

from skilledgraph import BindingError, BuildError, RoutingError, build_graph, load_graph, parse_graph

HAS_RUNTIME = importlib.util.find_spec("langgraph") is not None
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_RUNTIME, "requires runtime extra")
class BuildingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.write("tools.py", '''
            from typing_extensions import TypedDict
            from typing import Annotated
            from operator import add
            class State(TypedDict):
                value: int
                events: Annotated[list[str], add]
            def step(state):
                return {"value": state["value"] + 1, "events": ["step"]}
            def route(state):
                return "yes" if state["value"] == 1 else "no"
        ''')

    def write(self, name, content):
        path = self.directory / name
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
        return path

    def graph(self, content=None):
        return self.write("graph.md", content or '''
            # [Config]
            - **@state**: python:./tools.py:State
            # [Node] Step
            - **@uses**: python:./tools.py:step
            Body is ignored by native python.
            ## [Transitions]
            - @Default -> @End
        ''')

    def conditional(self, route="route"):
        return self.graph(f'''
            # [Config]
            - **@state**: python:./tools.py:State
            # [Node] Step
            - **@uses**: python:./tools.py:step
            - **@router**: python:./tools.py:{route}
            ## [Transitions]
            | Key | Target |
            | --- | --- |
            | yes | @End |
            | no | Again |
            # [Node] Again
            - **@uses**: python:./tools.py:step
            ## [Transitions]
            - @Default -> @End
        ''')

    def test_state_only_example(self):
        graph = load_graph(ROOT / "examples/09-state-only/workflow.md")
        self.assertEqual(graph.invoke({"value": 0, "events": []}),
                         {"value": 2, "events": ["incremented", "doubled"]})

    def test_native_goto_and_dsl_edge_both_run(self):
        graph = load_graph(ROOT / "examples/08-native-jump/workflow.md")
        result = graph.invoke({"messages": []})
        self.assertEqual({m.id for m in result["messages"]}, {"process", "report", "extra"})

    def test_raw_builder_and_schema(self):
        from langgraph.graph import StateGraph, END
        builder = build_graph(parse_graph(self.graph()))
        self.assertIsInstance(builder, StateGraph)
        builder.add_node("Native", lambda state: {"events": ["native"]})
        builder.add_edge("Step", "Native")
        builder.add_edge("Native", END)
        self.assertEqual(builder.compile().invoke({"value": 0, "events": []})["events"], ["step", "native"])

    def test_router_sees_merged_state(self):
        graph = load_graph(self.conditional())
        self.assertEqual(graph.invoke({"value": 0, "events": ["before"]}),
                         {"value": 1, "events": ["before", "step"]})
        self.assertEqual(graph.invoke({"value": 2, "events": []})["value"], 4)

    def test_bad_router_values_are_not_normalized(self):
        for value in [" yes ", "Again", None, ["yes"], {"yes": True}, 1]:
            with self.subTest(value=value):
                def bind(payload, **kwargs):
                    return lambda state: value
                spec = parse_graph(self.conditional())
                # Override python for both slots; schema import must remain independent.
                def dispatch(payload, **kwargs):
                    if payload.endswith(":step"):
                        return lambda state: {"value": 1}
                    return bind(payload, **kwargs)
                graph = load_graph(spec, bindings={"python": dispatch})
                with self.assertRaises(RoutingError) as error:
                    graph.invoke({"value": 0, "events": []})
                self.assertIn("Step", str(error.exception))
                self.assertIn("legal keys", str(error.exception))
                self.assertEqual(error.exception.diagnostic.phase, "run")

    def test_native_async_config_runtime_and_router(self):
        self.write("tools.py", '''
            from typing_extensions import TypedDict
            from langchain_core.runnables import RunnableConfig
            from langgraph.runtime import Runtime
            class State(TypedDict):
                value: int
            async def step(state: State, config: RunnableConfig, runtime: Runtime):
                return {"value": config["configurable"]["number"] + runtime.context["offset"]}
            async def route(state: State, config: RunnableConfig, runtime: Runtime):
                assert config["configurable"]["number"] == 3
                assert runtime.context["offset"] == 4
                return "yes" if state["value"] == 7 else "no"
        ''')
        graph = load_graph(self.conditional(), context_schema=dict)
        result = asyncio.run(graph.ainvoke({"value": 0}, {"configurable": {"number": 3}}, context={"offset": 4}))
        self.assertEqual(result, {"value": 7})

    def test_router_dataclass_input_schema_is_preserved(self):
        self.write("tools.py", '''
            from dataclasses import dataclass
            from typing_extensions import TypedDict
            class State(TypedDict):
                value: int
            @dataclass
            class RouterState:
                value: int
            def step(state: State):
                return {"value": 1}
            def route(state: RouterState):
                return "yes" if state.value == 1 else "no"
        ''')
        self.assertEqual(load_graph(self.conditional()).invoke({"value": 0}), {"value": 1})

    def test_schema_override_skips_file_and_host(self):
        from typing_extensions import TypedDict
        class State(TypedDict):
            value: int
        path = self.graph('''
            # [Config]
            - **@state**: python:./absent.py:State
            - **@host**: python:./also_absent.py:main
            # [Node] Step
            - **@uses**: custom:any payload
        ''')
        def binder(payload, *, base_dir, node, model):
            self.assertEqual(payload, "any payload")
            self.assertEqual(base_dir, self.directory)
            self.assertEqual(node.name, "Step")
            self.assertIs(model, sentinel)
            return lambda state: {"value": state["value"] + 1}
        sentinel = object()
        builder = build_graph(path, state_schema=State, bindings={"custom": binder}, model=sentinel)
        self.assertIs(builder.state_schema, State)
        self.assertEqual(builder.compile().invoke({"value": 5}), {"value": 6})
        with self.assertRaises(BindingError):
            build_graph(path, state_schema=None, bindings={"custom": binder})

    def test_native_schema_parameters_and_overwrite(self):
        from typing_extensions import TypedDict
        class State(TypedDict):
            value: int
            events: list[str]
        class Input(TypedDict):
            value: int
            events: list[str]
        class Output(TypedDict):
            value: int
        class Context(TypedDict):
            extra: int
        builder = build_graph(self.graph(), state_schema=State, input_schema=Input,
                              output_schema=Output, context_schema=Context)
        self.assertIs(builder.input_schema, Input)
        self.assertIs(builder.output_schema, Output)
        self.assertIs(builder.context_schema, Context)
        self.assertEqual(builder.compile().invoke({"value": 0, "events": ["before"]}), {"value": 1})
        graph = load_graph(self.graph(), state_schema=State)
        self.assertEqual(graph.invoke({"value": 0, "events": ["before"]})["events"], ["step"])

    def test_invalid_file_schema_not_repaired(self):
        self.write("tools.py", "State = None\ndef step(state):\n    return {}\n")
        with self.assertRaises(BindingError):
            build_graph(self.graph())

    def test_partial_registry_keeps_builtin(self):
        result = load_graph(self.graph(), bindings={"other": lambda *a, **kw: None}).invoke({"value": 0, "events": []})
        self.assertEqual(result["value"], 1)

    def test_unknown_backend_never_falls_back(self):
        path = self.graph("# [Node] A\n- **@uses**: absent:./tools.py:step\n")
        with self.assertRaisesRegex(BindingError, "Unknown Hardcode"):
            build_graph(path)

    def test_build_does_not_invoke_objects(self):
        self.write("tools.py", 'def factory():\n    raise AssertionError("must not run")\n')
        path = self.graph("# [Node] A\n- **@uses**: python:./tools.py:factory\n")
        build_graph(path)

    def test_bad_file_references(self):
        for ref in ["tools.py:step", "package.module:step", "~/tools.py:step", "./tools.py:step.x", "./tools.py:step()", "./tools.py:", "./missing.py:step", "./tools.py:missing", "./tools.py:__name__"]:
            with self.subTest(ref=ref):
                path = self.graph(f"# [Node] A\n- **@uses**: python:{ref}\n")
                with self.assertRaises(BindingError) as error:
                    build_graph(path)
                self.assertIsNotNone(error.exception.__cause__)
                self.assertEqual(error.exception.diagnostic.span.path, path)

    def test_import_failure_cleanup_and_retry(self):
        from skilledgraph.binding import load_file_object
        self.write("broken.py", 'raise RuntimeError("import failed")\n')
        with self.assertRaisesRegex(RuntimeError, "import failed"):
            load_file_object("./broken.py:run", base_dir=self.directory)
        self.write("broken.py", 'def run(state):\n    return {"fixed": True}\n')
        self.assertEqual(load_file_object("./broken.py:run", base_dir=self.directory)({}), {"fixed": True})

    def test_file_paths_spaces_colons_absolute_and_cache(self):
        from skilledgraph.binding import load_file_object
        path = self.write("a file:tools.py", '''
            from __future__ import annotations
            from dataclasses import dataclass
            @dataclass
            class State:
                value: int = 1
        ''')
        cwd = Path.cwd()
        first = load_file_object("./a file:tools.py:State", base_dir=self.directory)
        second = load_file_object(str(path) + ":State", base_dir=Path("/"))
        self.assertIs(first, second)
        self.assertEqual(first().value, 1)
        self.assertEqual(Path.cwd(), cwd)
        with ThreadPoolExecutor(max_workers=4) as pool:
            objects = list(pool.map(lambda _: load_file_object(str(path) + ":State", base_dir=Path("/")), range(8)))
        self.assertTrue(all(obj is first for obj in objects))

    def test_same_basename_modules_do_not_collide(self):
        from skilledgraph.binding import load_file_object
        (self.directory / "nested").mkdir()
        self.write("nested/tools.py", "State = 'different'\n")
        self.assertNotEqual(load_file_object("./tools.py:State", base_dir=self.directory),
                            load_file_object("./nested/tools.py:State", base_dir=self.directory))

    def test_conditional_python_requires_router(self):
        path = self.graph('''
            # [Node] A
            - **@uses**: python:./tools.py:step
            ## [Transitions]
            - yes -> @End
        ''')
        with self.assertRaisesRegex(BuildError, "needs @router"):
            build_graph(path)

    def test_router_without_condition_is_diagnosed(self):
        path = self.graph('''
            # [Node] A
            - **@uses**: python:./tools.py:step
            - **@router**: python:./tools.py:route
        ''')
        with self.assertRaisesRegex(BuildError, "requires a conditional"):
            build_graph(path)

    def test_native_interrupt_resume_compile_kwargs(self):
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import Command
        self.write("tools.py", '''
            from typing_extensions import TypedDict
            from langgraph.types import interrupt
            class State(TypedDict):
                value: int
            def step(state):
                return {"value": interrupt("number?")}
        ''')
        graph = load_graph(self.graph(), compile_kwargs={"checkpointer": InMemorySaver(), "name": "test-graph"})
        config = {"configurable": {"thread_id": "test"}}
        first = graph.invoke({"value": 0}, config)
        self.assertEqual(first["__interrupt__"][0].value, "number?")
        self.assertEqual(graph.invoke(Command(resume=9), config)["value"], 9)
        self.assertEqual(graph.name, "test-graph")

    def test_native_exceptions_not_swallowed(self):
        def bind(*args, **kwargs):
            def action(state):
                raise RuntimeError("business error")
            return action
        graph = load_graph(self.graph(), bindings={"python": bind})
        with self.assertRaisesRegex(RuntimeError, "business error"):
            graph.invoke({"value": 0, "events": []})

    def test_compile_errors_have_cause(self):
        with self.assertRaises(BuildError) as error:
            load_graph(self.graph(), compile_kwargs={"not_a_compile_argument": True})
        self.assertEqual(error.exception.diagnostic.phase, "compile")
        self.assertIsInstance(error.exception.__cause__, TypeError)

    def test_missing_model_fails_explicitly(self):
        with self.assertRaisesRegex(BuildError, "requires a model"):
            build_graph(self.graph("# [Node] A\nHello\n"))
        with self.assertRaisesRegex(BindingError, "requires a model"):
            build_graph(self.graph("# [Node] A\n- **@uses**: pyfunction:./tools.py:step\n"))

    def test_parser_import_remains_runtime_free(self):
        script = "import sys; from skilledgraph import parse_graph; parse_graph(sys.argv[1]); assert not any(k.startswith(('langgraph', 'langchain')) for k in sys.modules)"
        subprocess.run([sys.executable, "-c", script, str(self.graph())], check=True)


if __name__ == "__main__":
    unittest.main()
