# SkilledGraph

[中文](README_cn.md) | [English](README_en.md) | [Language files / 语言版本](docs/LOCALIZATION_en.md)

SkilledGraph is a Markdown DSL for personal scripts: describe LLM nodes and transitions in a few lines, use external Python for code, and retain custom Hosts and native LangGraph for advanced work.

Current development follows the **[v0.1 standard documents](docs/standard/v0.1/README_en.md)**. The agreed scope is implemented and deterministically verified: parsing, native graph construction, Prompt, python/pyfunction, routers, native State/reducers, and sgraph. The earlier complete regression passed 273 checks; DeepSeek and local MCP have controlled acceptance results. Platform coverage is qualified in the [Windows report](docs/development/WINDOWS_ACCEPTANCE_en.md), not implied for every application.

- [Language specification](docs/standard/v0.1/LANGUAGE_SPEC_en.md): exact syntax, extraction, control flow, diagnostics.
- [Implementation whitepaper](docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md): architecture, API, binding, default policies, extensions.
- [Development guide](docs/standard/v0.1/DEVELOPMENT_GUIDE_en.md): contribution and acceptance requirements.
- [Examples](examples/README_en.md), [fixtures](tests/fixtures/language/README_en.md).

Start with [usage](docs/development/USAGE_en.md) and examples. Contributors should read standards and [status](docs/development/STATUS_en.md). Standards define contracts; reports describe measured scope. See [document categories](docs/README_en.md).

## Tool calling

Run `python -m skilledgraph examples/10-tool-calling/workflow_en.md` for an offline model/tool loop with a real addition tool. See the standard and [tool acceptance](docs/development/TOOLS_COMPLETION_en.md).

## First-run connection setup

Basic chat Host is an independent [example](examples/chat-host/README_en.md) in examples/chat-host/src/sgraph_chat_host; DSL core remains src/skilledgraph. Without @host, sgraph lazily chooses it.

Install skilledgraph[chat], then run `sgraph examples/01-assistant/workflow_en.md`. Without an explicit model or saved profile, an interactive wizard gathers base URL, model ID, key, API mode, and optional headers. It supports English/Chinese; set SGRAPH_LANGUAGE=en to request English. Reconfigure with `sgraph examples/01-assistant/workflow_en.md -- --setup`. Credentials stay in user config, not DSL; see usage.

## Practical agents

Five runnable examples cover local-note QA, CSV auditing, approved email drafts, parallel review, and dynamic summaries. Each supports --demo offline. First three mostly use DSL flow; last two use native parallel APIs. See [index](examples/README_en.md) and [acceptance](docs/development/PRACTICAL_AGENTS_ACCEPTANCE_en.md).

Advanced State/reducers: [looping ReAct and compaction](examples/17-react-memory/README_en.md), [concurrent reducer lab](examples/18-reducer-lab/README_en.md), [results](docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md).

## Terminal agent

[sgraph_agent](sgraph_agent/README_en.md) provides continuing ReAct sessions, Responses, file/Bash/Monty tools, per-call permission, and graph-driven compaction. Install skilledgraph[agent]; English entry is sgraph-agent-en, original sgraph-agent remains compatible. See its README and [acceptance](docs/development/SGRAPH_AGENT_ACCEPTANCE_en.md).

## Languages

Chinese files use _cn and English files _en before the extension. Unsuffixed entries remain compatible. Unicode/byte fixtures and original model response JSON retain their evidence; see the localization guide for testing and exceptions.

## License

Copyright 2026 cedarrocket and contributors.

Licensed under [Apache License 2.0](LICENSE).
