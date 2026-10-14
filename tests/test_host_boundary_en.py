"""The DSL API and explicit Host selection must not load the chat example."""

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


class HostBoundaryTests(unittest.TestCase):
    def test_core_runs_with_chat_host_imports_blocked(self):
        try:
            import langgraph
        except ImportError:
            self.skipTest("requires runtime extra")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "actions_en.py").write_text(
                "from typing_extensions import TypedDict\n"
                "class State(TypedDict):\n    value: int\n"
                "def run(state):\n    return {'value': state['value'] + 1}\n"
                "def host(path, argv):\n    return 7\n", encoding="utf-8",
            )
            graph = path / "workflow_en.md"
            graph.write_text(
                "# [Config]\n"
                "- **@host**: python:./actions_en.py:host\n"
                "- **@state**: python:./actions_en.py:State\n"
                "# [Node] Calculate\n"
                "- **@uses**: python:./actions_en.py:run\n"
                "## [Transitions]\n- @Default -> @End\n", encoding="utf-8",
            )
            script = """
import importlib.abc
import sys
class BlockChatHost(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'sgraph_chat_host' or fullname.startswith('sgraph_chat_host.'):
            raise AssertionError('DSL core tried to import chat Host: ' + fullname)
sys.meta_path.insert(0, BlockChatHost())
from skilledgraph import parse_graph, build_graph, load_graph
from skilledgraph.cli import launch
path = sys.argv[1]
assert parse_graph(path).entry == 'Calculate'
assert launch(['--check', path]) == 0
assert launch([path]) == 7
assert build_graph(path).compile().invoke({'value': 0})['value'] == 1
assert load_graph(path).invoke({'value': 2})['value'] == 3
"""
            result = subprocess.run(
                [sys.executable, "-c", script, str(graph)],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
