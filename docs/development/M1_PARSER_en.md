# M1: Read-only Parser Prototype

> Non-normative stage report. Current support and commands: [status](STATUS_en.md), [usage](USAGE_en.md).

Date: 2026-10-09. Scope: file → GraphSpec/diagnostics, without binding, graph execution, model calls, or Host.

## 1. Usage

Install from repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests
```

At this stage there was no CLI subcommand, but Python parsing was available:

```python
from skilledgraph import parse_graph, ParseError
try:
    graph = parse_graph("examples/01-assistant/workflow_en.md")
except ParseError as error:
    print(error)  # file, line, column, phase, code, cause
else:
    print(graph.entry)
    for node in graph.nodes:
        print(node.name, node.prompt, node.setting("uses"))
```

Input paths are cwd-relative; GraphSpec.path/source positions are absolute. References remain text; M1 does not resolve script paths.

## 2. Modules and dependencies

| Module | Responsibility |
| --- | --- |
| api | UTF-8 reading and parse_graph |
| spec | frozen dataclasses/tuples |
| diagnostics | Diagnostic/ParseError |
| parsing/source | original text, newline normalization, positions |
| parsing/markdown | containers, directive override, strict fences |
| parsing/parser | regions/scopes, settings/descriptions, immutable IR |
| parsing/transitions | list/table records and original extra cells |
| parsing/validation | names, duplicates, targets, Default mixing |

Pinned markdown-it-py 3.0.0 supplies CommonMark block context and table extension. DSL rules precede GFM headers and activate only at allowed physical positions. Fence handling retains native containers and rejects missing closure. See [extension architecture](https://markdown-it-py.readthedocs.io/en/latest/architecture.html).

No rendering, rendered-tree reconstruction, or inline unescaping. Project normalizes newlines and bypasses additional library character normalization. Original table columns follow GFM escaped-pipe boundaries, retaining backslashes and extra cells beyond header count.

Tests use stdlib unittest; no LangGraph, model library, or user-file dependencies for parsing.

## 3. Data and locations

GraphSpec retains path/source_text/preamble/preamble_span/descriptions/config/nodes; entry is first name. NodeSpec retains settings/body/descriptions/transitions and whole/header/body spans. Setting retains key/value/raw/value_span. Transition retains fields/raw/spans/extra_cells; block retains form/raw/header/separator. source_slice(span) reads original text.

Lines/columns are one-based, offsets zero-based Unicode characters, not bytes. Half-open spans refer to decoded original text, accounting for CRLF/CR lengths; body independently normalizes LF. Tabs count one character, not display width.

These are prototype choices, explicitly revisable. IR contains no model/functions/State/runtime objects.

## 4. Diagnostics

ParseError.diagnostic exposes phase read/parse/validate, code/message/span. Codes identify current implementation, not additional frozen language. No exhaustive error collection or ordering promise; valid parse returns complete IR.

Invalid UTF-8 gets read diagnostic at decoded prefix. Filesystem failures preserve OSError. Binding-specific problems—unknown backend, missing file, python body, invalid router combinations—are not arbitrarily rejected by syntax.

## 5. Verification

Python 3.14.4, markdown-it-py 3.0.0; offline editable installation using existing system-visible dependencies:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m unittest discover -s tests -v
```

79 passed: all 45 manifest accept/reject/projection/reason cases, inventory, positions, original text, CR/CRLF, missing final newline, container fences, raw HTML, extra GFM cells, keyword precedence, import isolation, parallel parsing, and nine complete examples.

Sensitive fixture bytes remained unchanged. References to side-effectful modules were not executed; parser imported neither LangGraph nor LangChain. Editable build/install succeeded.

Not run: full CommonMark conformance suite or Python 3.11–3.13 matrix. Binding/model/native runtime was not yet verified; M1 alone was not an end-to-end claim.
