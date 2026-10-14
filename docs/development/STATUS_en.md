# Current Implementation and Acceptance Scope

Updated: 2026-10-09. Version 0.1.0.dev0. Contracts: [standards](../standard/v0.1/README_en.md); installation/run: [usage](USAGE_en.md).

## Implemented

- Read-only Markdown parsing, exact body, source diagnostics.
- parse_graph/build_graph/load_graph returning native Builder/compiled graph.
- Prompt, python/pyfunction, router, native State/reducer integration.
- ToolNode, tool selection, signal routing, complete tool loops.
- sgraph and independent [chat Host](../../examples/chat-host/README_en.md): one-shot execution, connection wizard, editing, dynamic resume.
- Optional monty, and continuing [sgraph_agent](../../sgraph_agent/README_en.md).

18 workflows plus standard Host cover chains, conditions, tools, approval, native parallel/Send, and custom reducers. Native Python implements parallelism; no DSL fan-out syntax.

## Evidence

The preceding complete Linux regression passed 273 unittest checks. It covers native execution, messages/reducers, parallel/async, resume, tools, and Host separation. Scripted models validate contracts, not intelligence.

| Scope | Report |
| --- | --- |
| Windows / Python 3.14 | [Windows](WINDOWS_ACCEPTANCE_en.md) |
| parsing/binding/execution | [M1](M1_PARSER_en.md), [M2](M2_BUILDING_en.md), [M3–M5](M3_M5_COMPLETION_en.md) |
| tools/local MCP | [tools](TOOLS_COMPLETION_en.md), [MCP](MCP_ACCEPTANCE_en.md) |
| Host/connections | [interrupt](HOST_INTERRUPT_ACCEPTANCE_en.md), [setup](HOST_SETUP_ACCEPTANCE_en.md), [separation](CHAT_HOST_SEPARATION_en.md) |
| real providers | [DeepSeek](DEEPSEEK_ACCEPTANCE_en.md), [OpenCode Go](OPENCODE_GO_ACCEPTANCE_en.md) |
| practical workflows | [five agents](PRACTICAL_AGENTS_ACCEPTANCE_en.md), [reducers](ADVANCED_REDUCERS_ACCEPTANCE_en.md), [parallel](PARALLEL_ACCEPTANCE_en.md) |
| terminal agent | [sgraph_agent](SGRAPH_AGENT_ACCEPTANCE_en.md) |

Reports/JSON preserve successive results, including failures and corrections. Earlier paths/features/dependencies/test totals are dated snapshots; use this page and usage for current entry points.

## Boundaries

- Personal scripting tool; not all LangGraph features/models/deployments are verified.
- Basic Host starts fresh; persistent conversation uses sgraph_agent/custom Host.
- No module references, file-level backend settings, output Schema, model maps, or parallel DSL.
- Local stdio MCP was offline-tested on Windows/Python 3.14; newly configured Linux/macOS CI awaits actual runs. Remote MCP is unverified. sgraph_agent currently requires POSIX file/process functionality.
- Compaction is lossy; in-memory checkpoint does not guarantee process-independent recovery.
- Approval is not a Bash OS sandbox; retry/resume does not ensure exactly-once external effects.
- Some adapters rely on pinned private APIs; upgrade needs reverification.
