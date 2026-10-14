# SkilledGraph v0.1 Development and Acceptance Guide

Updated: 2026-10-09. This guide is for contributors and adds no language features. Behavior is defined by the [language specification](LANGUAGE_SPEC_en.md) and [implementation whitepaper](IMPLEMENTATION_WHITEPAPER_en.md). Verified scope and limitations are in [status](../../development/STATUS_en.md).

## Code responsibilities

| Directory | Responsibility |
| --- | --- |
| src/skilledgraph/parsing/ | Markdown context, read-only parsing, static validation |
| src/skilledgraph/ | GraphSpec, diagnostics, binding, execution policies, native building, thin launcher |
| examples/chat-host/ | independent Host, connections, terminal, setup |
| examples/01-* through examples/18-* | runnable workflows and native extensions |
| sgraph_agent/ | continuing ReAct application, permissions, tools, context |
| tests/ | fixtures, offline checks, opt-in live tests |

Core APIs return native LangGraph objects, not a second runtime. Host/backend application policies must not become implicit syntax. State/reducers stay native; removed fields or reducers are not restored automatically.

## Environment and tests

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[chat,agent,mcp]'
.venv/bin/python -m unittest discover -s tests -v
```

PowerShell uses the same dependencies and test entry:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[chat,agent,mcp]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests/mcp_demo/check_en.py --output .local-docs/mcp-results.json
```

[CI](../../../.github/workflows/tests.yml) runs offline checks and local stdio MCP on Ubuntu/macOS/Windows with Python 3.11/3.14. UTF-8 mode is disabled to expose implicit encoding. Tests explicitly use UTF-8; subprocesses producing Unicode use UTF-8 mode and decoding. No live model services run in CI.

.gitattributes fixes language-fixture Markdown to LF; crlf.md and its localized copies preserve literal CRLF. Runtime-generated LF/CRLF inputs must parse equivalently without modifying bytes.

Windows skips agent cases requiring POSIX file APIs and two PTY cases. Agent connection/request/CLI-help checks still run. Skips mean unverified functionality, not Windows agent support. Core parsing/building/execution and ordinary Host tests are not OS-skipped.

Parser-only installation is `-e .`; native execution uses runtime extra. Full optional checks need corresponding dependencies; a skip is not a pass. Ordinary tests use scripted models and temporary data, not keys. Live services require explicit invocation; see [live instructions](../../../tests/live/README_en.md).

## Contracts to preserve

- Parsing does not import code, build graphs, or read model configuration; preserve original text/body/positions.
- No implicit Config, sequential edges, or end edges. Check forward targets after all nodes are read.
- Resolve references against graph directory, not by changing cwd; no guessing/fallback.
- API/file/default precedence follows whitepaper; do not import unselected references.
- @uses owns execution; no additional invoke. Backends decide body use.
- Prompt/pyfunction preserve invocation count, normalization, and incremental updates.
- Router reads merged State; tool conditions follow specified priority.
- Native Command and static edges both apply; no default table-boundary prohibition; End does not cancel branches.
- API never starts Host; only default CLI lazily selects standard Host.
- Native State/reducers, config/runtime, sync/async, and interrupt remain available.

## Verification focus

Parser changes need context boundaries, positions, exact body, forward references, tables/lists, [fixtures](../../../tests/fixtures/language/README_en.md), and manifest. Never format CRLF fixture bytes or prompt-extraction trailing spaces.

Binding/execution changes need inputs/results, call counts, incremental updates, import caching, and failure behavior. Async/parallel/Send/reducer/interrupt changes need actual native execution; parse success is insufficient.

Host changes need graph path/argv, terminal/pipe input, configuration precedence, ID-based resume, cancellation, and exit codes. Interrupt replay can rerun nodes; authors own side effects and recovery safety.

Tool changes must distinguish model declarations from ToolNode executable tools, preserving call IDs, sync/async, and resource lifetimes. Host manages MCP, not DSL credentials/transport settings.

Packaging changes need wheel contents, outside-repository imports, CLI, and data files. Host separation is checked by test_host_boundary.

## Changes and reporting

Run checks appropriate to the change; record commands, results, and missing coverage. Scripted models verify execution contracts, not intelligence. Finite live samples do not certify all models/material/platforms.

Semantic changes require matching specification/example/test updates. Deferred modules, output Schema, or file-level backends must not be silently accepted. Prefer native Python extensions over a keyword for every application demand.
