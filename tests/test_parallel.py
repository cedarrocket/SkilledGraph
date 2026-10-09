"""Parallel native capabilities remain accessible through SkilledGraph."""
import asyncio
from operator import add
from pathlib import Path
import tempfile
from threading import Barrier
from typing import Annotated
import unittest

try:
    from langgraph.types import Command, Send
    from langgraph.errors import InvalidUpdateError
    from typing_extensions import TypedDict
except ImportError:
    raise unittest.SkipTest("requires runtime extra")

from skilledgraph import build_graph, load_graph


class State(TypedDict):
    results: Annotated[list[str], add]
    summary: str


class ParallelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "graph.md"

    def builder(self, actions, schema=State):
        self.path.write_text("\n".join(f"# [Node] {name}\n- **@uses**: native:{name}\n" for name in actions))
        return build_graph(self.path, state_schema=schema,
                           bindings={"native": lambda payload, **kwargs: actions[payload]})

    def test_sync_parallel_and_unequal_branch_join(self):
        barrier = Barrier(2, timeout=5)
        def branch(name):
            def run(state):
                barrier.wait()  # Sequential execution would fail here.
                return {"results": [name]}
            return run
        seen = []
        def join(state):
            seen.append(sorted(state["results"]))
            return {"summary": ",".join(sorted(state["results"]))}
        builder = self.builder({"Start": lambda state: {}, "Left": branch("left"),
            "Right": branch("right"), "RightLast": lambda state: {"results": ["last"]}, "Join": join})
        builder.add_edge("Start", "Left").add_edge("Start", "Right")
        builder.add_edge("Right", "RightLast")
        builder.add_edge(["Left", "RightLast"], "Join")
        result = builder.compile().invoke({"results": []})
        self.assertEqual(seen, [["last", "left", "right"]])
        self.assertEqual(result["summary"], "last,left,right")

    def test_async_parallel(self):
        async def run():
            barrier = asyncio.Barrier(2)
            async def left(state):
                await asyncio.wait_for(barrier.wait(), timeout=5)
                return {"results": ["left"]}
            async def right(state):
                await asyncio.wait_for(barrier.wait(), timeout=5)
                return {"results": ["right"]}
            builder = self.builder({"Start": lambda state: {}, "Left": left, "Right": right})
            builder.add_edge("Start", "Left").add_edge("Start", "Right")
            result = await builder.compile().ainvoke({"results": []})
            self.assertEqual(sorted(result["results"]), ["left", "right"])
        asyncio.run(run())

    def test_native_command_send_dynamic_fan_out(self):
        def dispatch(state):
            return Command(goto=[Send("Worker", {"item": name}) for name in ("a", "b", "c")])
        def worker(state):
            return {"results": [state["item"].upper()]}
        builder = self.builder({"Dispatch": dispatch, "Worker": worker})
        self.assertEqual(sorted(builder.compile().invoke({"results": []})["results"]), ["A", "B", "C"])

    def test_parallel_same_field_without_reducer_retains_native_error(self):
        class PlainState(TypedDict):
            value: str
        builder = self.builder({"Start": lambda state: {}, "Left": lambda state: {"value": "left"},
                                "Right": lambda state: {"value": "right"}}, schema=PlainState)
        builder.add_edge("Start", "Left").add_edge("Start", "Right")
        with self.assertRaises(InvalidUpdateError):
            builder.compile().invoke({"value": "initial"})
