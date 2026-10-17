# SkilledGraph

[中文](README_cn.md) | [English](README_en.md) | [Language files / 语言版本](docs/LOCALIZATION_en.md)

> **Write Prompts and flowcharts in Markdown, write data fetching and logic in plain Python functions, and compile everything into 100% native LangGraph.**

When building LLM workflows and agents, stuffing multi-paragraph prompts into Python string literals makes them painful to maintain, while graph topology gets buried under boilerplate `add_node` / `add_edge` code.

**SkilledGraph** is a lightweight Markdown DSL for personal workflows:
- **Prompts & control flow live in Markdown (`.md`)**: See every node, its exact prompt, and its outgoing transitions at a glance.
- **Data & logic stay in Python (`.py`)**: Load files, query APIs, execute tools, and validate outputs using ordinary Python functions.
- **Zero custom scheduler, 100% native LangGraph**: Workflows compile directly into standard LangGraph `StateGraph` / `CompiledStateGraph` objects—retaining full support for `MessagesState`, custom Reducers, `ToolNode`, dynamic `interrupt()`, and parallel branches.

---

## SkilledGraph in 30 Seconds

A complete tool-calling loop takes just a few lines of Markdown:

```markdown
# [Node] Assistant

Use the add tool to calculate the user's request, then answer with the result.

## [Transitions]
| Condition | Target Node | Notes |
| --- | --- | --- |
| @ToolCalls | ExecuteTools | Jump to tool execution when the model requests tool calls |
| @Otherwise | @End | Finish and output the final reply when no tools are requested |

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
```

Need to fetch local data in Python before calling the model? Add `- **@uses**: pyfunction:./tools.py:prepare`.
Need to pause mid-workflow for human confirmation? Add `- **@uses**: request_input:Approve sending this draft?`.

---

## Quick Installation & First Run

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[chat]'
```

### 1. Try It Offline (Zero API Key Required)

The repository ships with deterministic offline demo models and examples so you can test everything immediately after cloning:

```bash
# Validate workflow syntax (instant, read-only static check)
sgraph --check examples/01-assistant/workflow_en.md

# Run a complete model -> ToolNode -> final answer loop offline
sgraph examples/10-tool-calling/workflow_en.md

# Experience dynamic interrupts and interactive terminal resume
sgraph examples/11-interrupt/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

### 2. Connect a Real LLM (Interactive Setup Wizard)

Run any workflow that uses the default chat Host:

```bash
sgraph examples/01-assistant/workflow_en.md
```

On first run, an interactive setup wizard launches automatically (re-run anytime with `sgraph examples/01-assistant/workflow_en.md -- --setup`; set `SGRAPH_LANGUAGE=en` for English prompts) to collect:
- **API Base URL** (e.g., `https://api.openai.com/v1`, DeepSeek, OpenRouter, or local Ollama / LM Studio)
- **Model ID**, **API Mode** (`chat_completions` or `responses`), and **API Key** (saved securely in `~/.config/skilledgraph/host.json`, never inside your DSL files).

---

## Start Learning Here (Tutorials & DSL Handbook)

New to SkilledGraph? Follow our step-by-step human-friendly tutorials:

1. **[Tutorials Home (`docs/tutorials/README_en.md`)](docs/tutorials/README_en.md)**: Overview and learning path.
2. **[Part 1: 10-Minute Quickstart (`01-QUICKSTART_en.md`)](docs/tutorials/01-QUICKSTART_en.md)**: Installation, single-node assistant, multi-step chains, and how `MessagesState` history flows.
3. **[Part 2: Step-by-Step Practical Tutorial (`02-STEP-BY-STEP_en.md`)](docs/tutorials/02-STEP-BY-STEP_en.md)**: Master model routing, `pyfunction` material functions, `python` validation nodes, `ToolNode` loops, `request_input` interrupts, and custom `@host` scripts in 6 progressive stops.
4. **[Part 3: DSL & Python Authoring Handbook (`03-DSL-HANDBOOK_en.md`)](docs/tutorials/03-DSL-HANDBOOK_en.md)**: Complete syntax cheat sheet, side-by-side comparison of all 5 node execution modes, Python API integration, and the **Top 10 Common Pitfalls & Troubleshooting Table**.

---

## 19 Runnable Examples & Practical Agents

Browse [`examples/`](examples/README_en.md) for runnable workflows ranging from a 6-line assistant to multi-step production patterns (all practical agents support `--demo` offline mode):

- **Core Building Blocks (`01` ~ `11`)**: Single-node chat, multi-step chains, list/table routing, Python routers, `pyfunction` material injection, custom State Reducers, native `Command.goto`, state-only computation, [tool calling (`10-tool-calling`)](examples/10-tool-calling/workflow_en.md), and [human interrupts (`11-interrupt`)](examples/11-interrupt/workflow_en.md).
- **5 Practical Engineering Agents (`12` ~ `16`)**: Local note QA with citation checks, CSV metric auditor, human-approved email drafting, 3-way parallel code review, and dynamic `Send` batch document digest (see [practical agents acceptance](docs/development/PRACTICAL_AGENTS_ACCEPTANCE_en.md)).
- **Advanced State & Concurrency (`17` ~ `18`)**: [Looping ReAct with memory compaction](examples/17-react-memory/README_en.md) and [concurrent reducer lab](examples/18-reducer-lab/README_en.md) (see [reducer acceptance](docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md)).
- **Subgraph reuse (`19`)**: [Reusable review graphs and hierarchical execution traces](examples/19-subgraphs/README_en.md), with an offline demo.
- **Terminal Coding Agent ([`sgraph_agent`](sgraph_agent/README_en.md))**: A persistent multi-turn ReAct terminal agent featuring Responses API support, file/Bash/Monty tools, per-call approval prompts, and automatic context compaction (install `skilledgraph[agent]` and run `sgraph-agent-en`; see [acceptance report](docs/development/SGRAPH_AGENT_ACCEPTANCE_en.md)).

---

## Using SkilledGraph as a Python Library

In addition to the `sgraph` CLI launcher, you can embed `.md` workflows directly into any Python application with 3 public functions:

```python
from langchain_core.messages import HumanMessage
from skilledgraph import parse_graph, build_graph, load_graph

# 1. Read-only static parse (never imports Python files)
spec = parse_graph("examples/01-assistant/workflow_en.md")

# 2. Build a native LangGraph StateGraph builder (customize with builder.add_edge, etc.)
builder = build_graph(spec, model=my_model)

# 3. Compile directly to a native CompiledStateGraph and run invoke / ainvoke / stream
graph = load_graph(spec, model=my_model, tools=my_tools)
result = graph.invoke({"messages": [HumanMessage(content="Hello!")]})
```

---

## Documentation Map

| What are you looking for? | Where to go |
| --- | --- |
| **Beginner onboarding, visual guides & troubleshooting** | **[Tutorials & DSL Handbook (`docs/tutorials/`)](docs/tutorials/README_en.md)** |
| **CLI flags, environment variables & setup wizard** | [Usage Guide (`docs/development/USAGE_en.md`)](docs/development/USAGE_en.md), [Standard Chat Host](examples/chat-host/README_en.md) |
| **Copy-pasteable runnable workflow templates** | [19 Official Examples (`examples/`)](examples/README_en.md) |
| **Normative compiler grammar & implementation contracts** | [v0.1 Standards](docs/standard/v0.1/README_en.md): [Language Spec](docs/standard/v0.1/LANGUAGE_SPEC_en.md), [Implementation Whitepaper](docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md), [Development Guide](docs/standard/v0.1/DEVELOPMENT_GUIDE_en.md) |
| **Test status, live model evidence & platform reports** | [Documentation Index](docs/README_en.md), [Project Status](docs/development/STATUS_en.md), [Tool Completion](docs/development/TOOLS_COMPLETION_en.md), [Language Fixtures](tests/fixtures/language/README_en.md), [Windows Report](docs/development/WINDOWS_ACCEPTANCE_en.md) |

## License

Copyright 2026 cedarrocket and contributors.

Licensed under the [Apache License 2.0](LICENSE).
