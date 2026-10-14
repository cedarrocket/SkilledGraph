"""Specification-driven acceptance and boundary tests for the M1 parser."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import builtins
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from skilledgraph import ParseError, parse_graph


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/language"
MANIFEST = json.loads((FIXTURES / "manifest_en.json").read_text(encoding="utf-8"))
ERRORS = {
    "no-node": "graph.empty", "node-no-name": "node.name", "node-invalid-name": "node.name",
    "node-duplicate": "node.duplicate", "config-duplicate": "config.duplicate",
    "config-after-node": "config.scope", "implicit-config": "setting.scope",
    "node-file-setting": "setting.scope", "config-node-setting": "setting.scope",
    "setting-unknown": "setting.unknown", "setting-empty": "setting.empty",
    "setting-duplicate": "setting.duplicate", "setting-no-colon": "setting.syntax",
    "setting-unclosed-bold": "setting.syntax", "fence-unclosed": "fence.unclosed",
    "transitions-empty": "transitions.empty", "transitions-duplicate": "transitions.duplicate",
    "transitions-prose": "transitions.list_record", "transitions-description": "transitions.content",
    "transitions-setting": "transitions.content", "end-shorthand": "transitions.format",
    "route-unknown-target": "route.unknown_target", "route-duplicate": "route.duplicate",
    "route-default-mixed": "route.default_mixed", "route-unknown-special": "route.key",
    "route-end-key": "route.key", "route-default-target": "route.target",
    "route-styled-name": "route.key", "table-no-data": "table.empty",
    "table-missing-target": "table.columns", "table-blank-resume": "table.discontinuous",
    "table-second-table": "table.discontinuous", "formats-mixed": "transitions.list_record",
}


def projection(graph, include_config=False):
    value = {"entry": graph.entry, "nodes": [
        {"name": node.name, "prompt": node.prompt,
         "settings": {item.key: item.value for item in node.settings},
         "descriptions": [item.text for item in node.descriptions],
         "transitions": None if node.transitions is None else [
             [item.key, item.target] for item in node.transitions.records],
         } for node in graph.nodes]}
    if include_config:
        value["config"] = {item.key: item.value for item in graph.config.settings}
    return value


class ManifestTests(unittest.TestCase):
    def test_manifest_inventory(self):
        declared = {case["file"] for case in MANIFEST["cases"]}
        present = {path.relative_to(FIXTURES).as_posix() for folder in ("valid", "invalid")
                   for path in (FIXTURES / folder).glob("*_en.md")}
        self.assertEqual(declared, present)
        self.assertEqual(len(declared), len(MANIFEST["cases"]))


def manifest_test(case):
    def run(self):
        path = FIXTURES / case["file"]
        if case["accept"]:
            graph = parse_graph(path)
            self.assertEqual(projection(graph, "config" in case["expected"]), case["expected"])
        else:
            with self.assertRaises(ParseError) as error:
                parse_graph(path)
            diagnostic = error.exception.diagnostic
            self.assertEqual(diagnostic.code, ERRORS[case["id"]])
            self.assertEqual(diagnostic.span.path, path)
            self.assertGreaterEqual(diagnostic.span.start.line, 1)
            self.assertIn(str(path), str(error.exception))
    return run


for _case in MANIFEST["cases"]:
    setattr(ManifestTests, "test_" + _case["id"].replace("-", "_"), manifest_test(_case))


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "workflow_en.md"

    def parse(self, source):
        self.path.write_bytes(source.encode("utf-8") if isinstance(source, str) else source)
        return parse_graph(self.path)

    def error(self, source, code):
        with self.assertRaises(ParseError) as caught:
            self.parse(source)
        self.assertEqual(caught.exception.diagnostic.code, code)
        return caught.exception.diagnostic

    def test_source_offsets_keep_mixed_newlines_and_unicode(self):
        source = "前言é\r\n# [Config]\r- **@state**: python:./缺少.py:S  \n# [Node] 甲\r\n第一行  \r第二行"
        graph = self.parse(source)
        self.assertEqual(graph.source_text, source)
        self.assertEqual(graph.preamble, "前言é\r\n")
        self.assertEqual(graph.nodes[0].prompt, "第一行  \n第二行")
        self.assertEqual(graph.nodes[0].header_span.start.line, 4)
        self.assertEqual(graph.nodes[0].header_span.start.column, 1)
        self.assertEqual(graph.nodes[0].header_span.start.offset, source.index("# [Node]"))
        value_span = graph.config.settings[0].value_span
        self.assertEqual(graph.source_slice(value_span), "python:./缺少.py:S")
        self.assertEqual(graph.nodes[0].span.end.offset, len(source))
        self.assertEqual(graph.nodes[0].span.end.line, 6)
        self.assertEqual(graph.nodes[0].span.end.column, 4)

    def test_cr_and_no_terminal_newline(self):
        graph = self.parse("# [Node] A\r正文\r## [Transitions]\r- @Default -> @End")
        self.assertEqual(graph.nodes[0].prompt, "正文")
        record = graph.nodes[0].transitions.records[0]
        self.assertEqual(graph.source_slice(record.target_span), "@End")
        self.assertEqual(record.target_span.start.line, 4)

    def test_invalid_utf8_has_read_diagnostic(self):
        diagnostic = self.error(b"# [Node] A\r\n\xff", "source.encoding")
        self.assertEqual(diagnostic.phase, "read")
        self.assertEqual(diagnostic.span.start.line, 2)

    def test_empty_file(self):
        diagnostic = self.error("", "graph.empty")
        self.assertEqual(diagnostic.span.start.offset, 0)

    def test_missing_input_propagates_filesystem_error(self):
        with self.assertRaises(FileNotFoundError):
            parse_graph(self.path)

    def test_references_are_opaque_and_never_loaded(self):
        marker = self.path.parent / "imported.txt"
        script = self.path.parent / "dangerous.py"
        script.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('imported')\n", encoding="utf-8")
        source = """# [Config]
- **@host**: python:./dangerous.py:host
- **@state**: python:./dangerous.py:State
# [Node] A
- **@uses**: python:./dangerous.py:run
- **@router**: python:./dangerous.py:route
## [Transitions]
- yes -> @End
"""
        original_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name.startswith(("langgraph", "langchain", "dangerous")):
                raise AssertionError(f"Execution dependency imported: {name}")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded):
            graph = self.parse(source)
        self.assertFalse(marker.exists())
        self.assertEqual(graph.nodes[0].setting("uses"), "python:./dangerous.py:run")
        graph = self.parse("# [Node] A\n- **@uses**: custom:arbitrary payload:call(x)")
        self.assertEqual(graph.nodes[0].setting("uses"), "custom:arbitrary payload:call(x)")

    def test_config_description_and_prose_remain_available(self):
        graph = self.parse("intro\n>>> 前言\n# [Config]\n>>> 配置\nmore prose\n- **@host**: opaque\n# [Node] A\nbody")
        self.assertEqual(graph.preamble_descriptions[0].text, "前言")
        self.assertEqual(graph.config.descriptions[0].text, "配置")
        self.assertIn("more prose", graph.config.raw)
        self.assertEqual(graph.config.setting("host"), "opaque")
        self.assertIsNone(graph.config.setting("state"))
        with self.assertRaises(FrozenInstanceError):
            graph.nodes[0].prompt = "changed"

    def test_settings_among_ordinary_list_items(self):
        graph = self.parse("# [Node] A\n- ordinary\n- **@uses**: python:./x.py:f\n- other\n- **@router**: python:./x.py:r")
        self.assertEqual(graph.nodes[0].prompt, "- ordinary\n\n- other")
        self.assertEqual(len(graph.nodes[0].settings), 2)

    def test_description_does_not_capture_next_line(self):
        graph = self.parse("# [Node] A\n>>>  comment\nnext line\n>>>\nlast")
        self.assertEqual(graph.nodes[0].prompt, "next line\n\nlast")
        self.assertEqual([d.text for d in graph.nodes[0].descriptions], [" comment", ""])

    def test_literal_contexts_in_nested_containers(self):
        body = "> ```md\n> # [Node] Quoted\n> >>> literal\n> ```\n\n- item\n  ~~~\n  # [Node] Listed\n  - **@bad**: literal\n  ~~~\n\n    # [Node] Indented\n\n   # [Node] ThreeSpaces"
        graph = self.parse("# [Node] A\n" + body)
        self.assertEqual([n.name for n in graph.nodes], ["A"])
        self.assertEqual(graph.nodes[0].prompt, body)

    def test_nested_unclosed_fences_are_diagnosed(self):
        for body in ("> ```\n> body\n\n# [Node] B", "- ~~~\n  body\n# [Node] B"):
            with self.subTest(body=body):
                diagnostic = self.error("# [Node] A\n" + body, "fence.unclosed")
                self.assertEqual(diagnostic.span.start.line, 2)

    def test_longer_closing_fence_and_tilde_info(self):
        graph = self.parse("# [Node] A\n~~~ `info`\n# [Node] Literal\n~~~~\n# [Node] B\nend")
        self.assertEqual([n.name for n in graph.nodes], ["A", "B"])

    def test_fence_with_suffix_is_not_a_closer(self):
        self.error("# [Node] A\n```\n```suffix", "fence.unclosed")

    def test_unclosed_html_is_preserved_without_comment_filtering(self):
        body = "<!--\n# [Node] Literal\n- **@unknown**: literal"
        graph = self.parse("# [Node] A\n" + body)
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].prompt, body)

    def test_html_block_protects_markers(self):
        body = "<div>\n# [Node] Literal\n>>> literal\n</div>"
        graph = self.parse("# [Node] A\n" + body + "\n\n# [Node] B\ntext")
        self.assertEqual([n.name for n in graph.nodes], ["A", "B"])
        self.assertEqual(graph.nodes[0].prompt, body)

    def test_ordinary_headings_and_escapes_are_not_reparsed(self):
        body = "# [node] literal\n# [Graph]\n\\# [Node] Escaped\n`# [Node] Inline`\n&amp;\n\x00"
        graph = self.parse("# [Node] A\n" + body)
        self.assertEqual(graph.nodes[0].prompt, body)

    def test_table_raw_cells_include_extra_and_escaped_pipes(self):
        graph = self.parse("# [Node] A\n## [Transitions]\n|k|t|note|\n|-|-|-|\n|yes|@End| a\\|b |`c\\|d`| >>> text |\n")
        table = graph.nodes[0].transitions
        record = table.records[0]
        self.assertEqual(record.extra_cells, (" a\\|b ", "`c\\|d`", " >>> text "))
        self.assertEqual(graph.source_slice(record.key_span), "yes")
        self.assertEqual(graph.source_slice(table.span), table.raw)
        self.assertEqual(table.table_header, ("k", "t", "note"))

    def test_table_header_labels_do_not_execute(self):
        graph = self.parse("# [Node] A\n## [Transitions]\nany **text** | whatever\n- | -\nready | @End")
        self.assertEqual(graph.nodes[0].transitions.records[0].key, "ready")

    def test_gfm_header_detection_cannot_swallow_dsl_markers(self):
        graph = self.parse("# [Node] A\n- **@uses**: custom:a|b\n---|---\n>>> note|more\n---|---")
        self.assertEqual(graph.nodes[0].setting("uses"), "custom:a|b")
        self.assertEqual(graph.nodes[0].descriptions[0].text, "note|more")
        self.assertEqual(graph.nodes[0].prompt, "---|---\n\n---|---")
        self.error("# [Node] A\n# [Node] Bad|Name\n---|---", "node.name")

    def test_names_made_of_hyphens_are_valid_table_data(self):
        graph = self.parse("# [Node] A\n## [Transitions]\nk|t\n-|-\n---|---\n# [Node] ---\nbody")
        self.assertEqual(graph.nodes[0].transitions.records[0].target, "---")

    def test_blank_lines_in_lists_are_allowed(self):
        graph = self.parse("# [Node] A\n## [Transitions]\n\n- yes -> @End\n\n- no -> A\n")
        self.assertEqual(len(graph.nodes[0].transitions.records), 2)

    def test_table_separator_column_count_and_styled_values(self):
        self.error("# [Node] A\n## [Transitions]\na|b\n-|-|-\nx|@End", "table.delimiter")
        self.error("# [Node] A\n## [Transitions]\na|b\n-|-\nx|`@End`", "route.target")

    def test_indented_table_is_invalid(self):
        self.error("# [Node] A\n## [Transitions]\n k|t\n -|-\n yes|@End", "transitions.format")

    def test_escaped_pipe_is_not_an_execution_column(self):
        self.error("# [Node] A\n## [Transitions]\nk|t\n-|-\nyes\\|@End", "table.columns")

    def test_forward_edges_end_aliases_and_disconnected_nodes(self):
        graph = self.parse("# [Node] A\n## [Transitions]\n- Default -> END\n# [Node] END\nbody\n# [Node] Unreachable")
        record = graph.nodes[0].transitions.records[0]
        self.assertEqual((record.key, record.target), ("Default", "END"))
        self.assertIsNone(graph.nodes[2].transitions)

    def test_unsupported_execution_and_router_combinations_are_not_syntax_errors(self):
        graph = self.parse("# [Node] A\n- **@uses**: nonexistent:foo\n- **@router**: arbitrary\n正文")
        self.assertEqual(graph.nodes[0].prompt, "正文")

    def test_reserved_header_suffixes_are_invalid(self):
        self.error("# [Node] A ###", "node.name")
        self.error("# [Node]A", "node.name")
        self.error("# [Config] tail\n# [Node] A", "config.syntax")
        self.error("# [Node] A\n## [Transitions] tail", "transitions.syntax")

    def test_unicode_categories_are_exact(self):
        graph = self.parse("# [Node] 步骤-Ⅳ_١\ntext")
        self.assertEqual(graph.entry, "步骤-Ⅳ_١")
        self.error("# [Node] e\u0301", "node.name")
        self.error("#\u00a0[Node] A", "graph.empty")

    def test_transition_scope_before_node(self):
        self.error("## [Transitions]\n- @Default -> @End\n# [Node] A", "transitions.scope")

    def test_reference_quotes_are_preserved(self):
        graph = self.parse('# [Node] A\n- **@uses** :  "custom: value" \t')
        setting = graph.nodes[0].settings[0]
        self.assertEqual(setting.value, '"custom: value"')
        self.assertEqual(graph.source_slice(setting.value_span), setting.value)

    def test_no_state_leaks_between_parallel_parses(self):
        paths = sorted((FIXTURES / "valid").glob("*.md"))
        sequential = [parse_graph(path) for path in paths]
        with ThreadPoolExecutor(max_workers=4) as pool:
            parallel = list(pool.map(parse_graph, paths))
        self.assertEqual(parallel, sequential)

    def test_all_complete_examples_parse(self):
        paths = sorted((ROOT / "examples").glob("*/workflow_en.md"))
        self.assertEqual(len(paths), 19)  # 18 workflows plus the standard chat Host example.
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(parse_graph(path).nodes)

    def test_lf_and_crlf_inputs_preserve_bytes_and_parse_equally(self):
        source = (FIXTURES / "valid" / "prompt-extraction_en.md").read_bytes()
        lf = source.replace(b"\r\n", b"\n")
        with tempfile.TemporaryDirectory() as directory:
            graphs = []
            for name, data in (("lf", lf), ("crlf", lf.replace(b"\n", b"\r\n"))):
                path = Path(directory) / (name + ".md")
                path.write_bytes(data)
                graphs.append(projection(parse_graph(path)))
                self.assertEqual(path.read_bytes(), data)
            self.assertEqual(graphs[0], graphs[1])

    def test_sensitive_fixture_bytes_are_unchanged_by_parsing(self):
        for name in ("crlf", "prompt-extraction"):
            path = FIXTURES / "valid" / (name + ".md")
            original = path.read_bytes()
            parse_graph(path)
            self.assertEqual(path.read_bytes(), original)
            if name == "crlf":
                self.assertIn(b"\r\n", original)
            else:
                self.assertIn(b"  \n", original)


if __name__ == "__main__":
    unittest.main()
