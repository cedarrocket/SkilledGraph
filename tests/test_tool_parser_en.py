"""Tool syntax stays usable without LangGraph or executable imports."""
from pathlib import Path
import tempfile
import unittest
from skilledgraph import parse_graph, ParseError


class ToolParserTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.md"
            path.write_text(text, encoding="utf-8")
            return parse_graph(path)

    def test_kind_source_and_table(self):
        spec = self.parse("# [ToolNode] Exec\n- **@tools**: [a, b]\nignored body\n## [Transitions]\n| key | target | notes |\n| --- | --- | --- |\n| @Otherwise | @End | anything |\n")
        node = spec.nodes[0]
        self.assertEqual((node.kind, node.name, node.prompt), ("ToolNode", "Exec", "ignored body"))
        self.assertEqual(spec.source_slice(node.header_span), "# [ToolNode] Exec")
        self.assertEqual(node.transitions.records[0].key, "@Otherwise")

    def test_selection_errors(self):
        for value in ("list:[a,b]", "[a,]", "[a,a]", '["a"]', "[a b]", "[a.b]", "ALL"):
            with self.subTest(value=value), self.assertRaises(ParseError):
                self.parse(f"# [ToolNode] Exec\n- **@tools**: {value}\n")

    def test_scopes_and_required_setting(self):
        for text in (
            "# [ToolNode] Exec\n",
            "# [Node] A\n- **@tools**: all\n",
            "# [Config]\n- **@tools**: all\n# [Node] A\n",
            "# [ToolNode] Exec\n- **@tools**: all\n- **@uses**: python:./a.py:run\n",
            "# [ToolNode] Exec\n- **@tools**: all\n- **@tools**: []\n",
        ):
            with self.subTest(text=text), self.assertRaises(ParseError):
                self.parse(text)

    def test_shared_name_namespace(self):
        with self.assertRaises(ParseError):
            self.parse("# [Node] A\n# [ToolNode] A\n- **@tools**: []\n")

    def test_special_keys_and_default_exclusive(self):
        for key in ("@ToolCalls", "@Otherwise"):
            spec = self.parse(f"# [Node] A\n## [Transitions]\n- {key} -> @End\n")
            self.assertEqual(spec.nodes[0].transitions.records[0].key, key)
            with self.assertRaises(ParseError):
                self.parse(f"# [Node] A\n## [Transitions]\n- @Default -> @End\n- {key} -> @End\n")

    def test_protected_heading(self):
        spec = self.parse("# [Node] A\n\n```md\n# [ToolNode] B\n```\n\n> # [ToolNode] C\n")
        self.assertEqual(len(spec.nodes), 1)
        self.assertIn("# [ToolNode] B", spec.nodes[0].prompt)
