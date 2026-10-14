# SkilledGraph Tutorials & DSL Authoring Guide

[中文](README_cn.md) | [English](README_en.md)

Welcome to the SkilledGraph Tutorials!

If you have opened `docs/standard/v0.1/`, you might feel like reading a strict compiler specification—packed with EBNF rules, byte offsets, ownership boundaries, and "MUST / MUST NOT" clauses. As an **engineering standard and language contract**, it does its job well; as a **human-friendly tutorial**, it is far too dense for newcomers.

This `docs/tutorials/` directory is written specifically for **users and workflow authors**. We skip the compiler jargon and use visual diagrams, runnable examples, and plain language to help you master SkilledGraph quickly.

---

## SkilledGraph in One Sentence

> **Write Prompts and flowcharts in Markdown, write data fetching and logic in plain Python functions, and compile everything into 100% native LangGraph.**

In traditional agent development, long prompts are buried inside Python string literals, and graph wiring is scattered across boilerplate `add_node` / `add_edge` calls. With SkilledGraph:
- **What the workflow looks like & what the Prompts say** → Lives cleanly in a `.md` file, readable at a glance.
- **How data is loaded, APIs are called, and outputs are validated** → Lives in companion `.py` files as ordinary Python functions.
- **State management, checkpointing, interrupts, and parallel scheduling** → 100% native LangGraph under the hood—no reinvented wheels.

---

## Learning Path

Whether you are trying SkilledGraph for the first time or building a multi-step agent, follow these three guides in order:

### 1. [10-Minute Quickstart (01-QUICKSTART_en.md)](01-QUICKSTART_en.md)
**Best for**: First-time users who want to understand the mental model and run their first workflow right away.
- Installation & zero-API-key offline test run
- The 3 core building blocks (`Node`, `Transitions`, `State`)
- Writing your first single-node assistant and two-node pipeline
- Connecting a real LLM (interactive setup wizard, OpenAI-compatible APIs, DeepSeek, or local models)

### 2. [Step-by-Step Practical Tutorial (02-STEP-BY-STEP_en.md)](02-STEP-BY-STEP_en.md)
**Best for**: Developers ready to connect Python code, conditional branches, tools, and human-in-the-loop interrupts.
- **Stop 1: Conditional Branching & Model Routing** — Let the LLM choose the next path
- **Stop 2: Feeding Data with `pyfunction`** — Run Python to gather material before calling the model
- **Stop 3: Hard Logic with `python` Nodes + `@router`** — Custom `State`, exact validation, and bounded retry loops
- **Stop 4: Tool Calling (`ToolNode`)** — Build an explicit ReAct tool execution loop
- **Stop 5: Human-in-the-Loop (`request_input`)** — Pause mid-graph to ask the user, then resume seamlessly
- **Stop 6: Beyond the Default Chat Prompt (`@host`)** — Write a 10-line custom Host to control inputs and outputs

### 3. [DSL & Python Authoring Handbook (03-DSL-HANDBOOK_en.md)](03-DSL-HANDBOOK_en.md)
**Best for**: Day-to-day reference while authoring workflows.
- Complete Markdown DSL syntax cheat sheet (headers, 4 `@` settings, 2 transition styles, reserved markers)
- Side-by-side comparison of all 5 node execution modes (Default Prompt vs `pyfunction` vs `python` vs `request_input` vs `monty`)
- How `State` and message history (`MessagesState`) actually flow between nodes
- Python API integration (`parse_graph` / `build_graph` / `load_graph` and mixing native LangGraph edges)
- Top 10 Common Pitfalls & Troubleshooting Table

---

## How the Documentation Fits Together

| Directory | Purpose | When to read it? |
| --- | --- | --- |
| **`docs/tutorials/` (You are here)** | **Beginner Tutorials & Practical DSL Handbook** | Learning how to write `.md` workflows and `.py` companions, daily syntax lookup, troubleshooting |
| [`examples/`](../../examples/README_en.md) | **18 Runnable Official Examples** | Copying ready-made templates (CSV auditing, local note QA, parallel code review, etc.) |
| [`docs/development/USAGE_en.md`](../development/USAGE_en.md) | **CLI & Environment Variable Reference** | Checking `sgraph` flags, `SGRAPH_*` environment variables, and setup wizard details |
| [`docs/standard/v0.1/`](../standard/v0.1/README_en.md) | **Normative Language Spec & Whitepaper** | Modifying SkilledGraph internals, building custom execution backends, or verifying edge-case contracts |

Ready to dive in? Start with **[Part 1: 10-Minute Quickstart (01-QUICKSTART_en.md)](01-QUICKSTART_en.md)**!
