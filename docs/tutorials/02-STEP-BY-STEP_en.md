# Part 2: Step-by-Step Practical Tutorial

[中文](02-STEP-BY-STEP_cn.md) | [English](02-STEP-BY-STEP_en.md) | [← Previous: 10-Minute Quickstart](01-QUICKSTART_en.md) | [Tutorials Home](README_en.md) | [Next: DSL & Python Handbook →](03-DSL-HANDBOOK_en.md)

In Part 1, we chained simple prompt nodes together using `# [Node]` and `- @Default -> ...`.

Real-world agent workflows, however, require **conditional branching, reading local data, validating outputs in code, calling tools (`ToolNode`), and pausing for human confirmation (`request_input`)**.

This tutorial takes you through **6 progressive stops**. Each stop introduces a single concept and pairs directly with a runnable example in `examples/`.

---

## Stop 1: Let the Model Choose the Path (Model Text Routing)

**Scenario**: A user submits a request. First, an `Evaluate` node checks if there is enough information. If yes, jump to `Report`; if not, jump to `RequestMore` to ask follow-up questions.

When an ordinary prompt node's `## [Transitions]` uses **named route keys** instead of `@Default`, SkilledGraph automatically enables **default model text routing**:

### Style A: List format (see `examples/03-routing-list/workflow_en.md`)

```markdown
# [Node] Evaluate

Determine whether the user's input is sufficient to write a complete report.
Reply with ONLY one of the following route keys—no punctuation or explanation:
- enough
- insufficient

## [Transitions]
- enough -> Report
- insufficient -> RequestMore

# [Node] Report

Generate a complete analysis report from the available information.

## [Transitions]
- @Default -> @End

# [Node] RequestMore

Politely explain what information is missing and ask the user to provide it.

## [Transitions]
- @Default -> @End
```

### Style B: Table format (see `examples/04-routing-table/workflow_en.md`)

If you want to document why each branch exists for human readers, write `## [Transitions]` as a Markdown pipe table:

```markdown
## [Transitions]
| Route Key | Target Node | Notes (for humans, ignored at runtime) |
| --- | --- | --- |
| enough | Report | Material is sufficient; write the report |
| insufficient | RequestMore | Material is missing; ask the user |
```

> **Key Rules (Avoid Common Pitfalls)**:
> 1. **List OR Table, never both**: A single `## [Transitions]` block must use either a list or a single table. In a table, the first two columns are the route key and target node; column 3 and beyond are free-form human notes.
> 2. **Exact key matching**: Without a Python `@router`, SkilledGraph strips outer whitespace from the model's reply (`reply.text.strip()`) and looks it up directly in the table. It does **not** regex-search inside a paragraph or strip quotes/code fences. Your prompt must instruct the model to **output only the exact key**.
> 3. **`@Default` is NOT a fallback**: You cannot mix `@Default` with named keys in the same transition table. If the model outputs an unknown word, execution raises a `RoutingError` immediately rather than silently taking a wrong path.

---

## Stop 2: Feed Python Data into a Model Node (`pyfunction`)

**Scenario**: You want the LLM to summarize today's invoices, but those records live in a local file or database. You want a Python function to fetch the data, and then let the node's Markdown prompt analyze it.

That is exactly what `- **@uses**: pyfunction:FILE:FUNCTION` does! (See `examples/06-pyfunction/`)

### 1. Write `tools_en.py` (supply the material)

```python
def prepare(state) -> str:
    # Receives current graph State; returns material to feed the model
    # (str, dict, list, or native LangChain BaseMessage)
    return "Record A: amount 12. Record B: amount 8."
```

### 2. Write `workflow_en.py` / `workflow_en.md` (combine material & prompt)

```markdown
# [Node] Analyze
- **@uses**: pyfunction:./tools_en.py:prepare

>>> Lines starting with >>> at column 1 are author notes—never sent to the model!

Calculate the total amount from the supplied records and explain the steps.

## [Transitions]
- @Default -> @End
```

### What does `pyfunction` do under the hood?

When `Analyze` runs, SkilledGraph executes 5 steps automatically:
1. Calls `prepare(state)` and gets `"Record A: amount 12. Record B: amount 8."`.
2. Wraps that return value into a `HumanMessage` (dicts/lists are serialized to JSON text; native `BaseMessage` objects keep their exact role and metadata).
3. Assembles the model input sequence:
   `[SystemMessage(node prompt), ...existing history..., HumanMessage(new material)]`
4. **Calls the LLM once** to get an `AIMessage` reply.
5. Appends **`[new material message, AI reply]`** into `State.messages`!

Run Example 06 offline to see it in action:
```bash
printf 'Please analyze\n' | sgraph examples/06-pyfunction/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```
You will see that the model received **3 input messages** (1 system prompt + 1 user input + 1 material message from `prepare`)!

---

## Stop 3: Pure Python Nodes, Custom State & Code Routers (`python` + `@router` + `@state`)

**Scenario**: Some steps don't need an LLM at all—like checking input validity, verifying math in a model's draft, or incrementing a retry counter—and then routing based on the updated `State`.

Here we combine three directives (see `examples/05-python-router/`):
- **`- **@state**` in `# [Config]`**: Declares a custom LangGraph `State` schema.
- **`- **@uses**: python:...` in a node**: Hands execution entirely to your Python callable (**no automatic LLM call**).
- **`- **@router**: python:...` in a node**: Reads the merged `State` after the node finishes and returns a route key string.

Let's look at the 3 files working together:

### 1. Define the State schema (`state_en.py`)
Subclass `MessagesState` to keep `messages` history while adding a `status` field:
```python
from langgraph.graph import MessagesState

class State(MessagesState):
    status: str
```

### 2. Write the node callable and router (`tools_en.py`)
```python
from langchain_core.messages import AIMessage

# 1. Node action (@uses): receives State, returns a State update dict
def inspect(state):
    status = "ready" if state["messages"] else "missing"
    text = "Input received." if status == "ready" else "No input received."
    return {"status": status, "messages": [AIMessage(content=text)]}

# 2. Router function (@router): reads merged State, returns a route key string
def route(state) -> str:
    return state["status"]
```

### 3. Write the workflow (`workflow_en.md`)
```markdown
# [Config]
- **@state**: python:./state_en.py:State

# [Node] Inspect
- **@uses**: python:./tools_en.py:inspect
- **@router**: python:./tools_en.py:route

>>> Code updates status; router reads merged State; no automatic model call here.

## [Transitions]
- ready -> Report
- missing -> RequestMaterial

# [Node] Report

Generate a concise report from the input and inspection result in history.

## [Transitions]
- @Default -> @End

# [Node] RequestMaterial

Ask the user to provide material for analysis.

## [Transitions]
- @Default -> @End
```

### The Golden Execution Order (Crucial!):
On node `Inspect`, execution strictly follows:
> **`inspect(state)` runs & returns update dict** ➔ **LangGraph Reducers merge the update into `State`** ➔ **`route(state)` reads the newly merged `State`** ➔ **returns `"ready"` or `"missing"`** ➔ **table lookup jumps to target node**.

> **Important Reminders**:
> - `route(state)` must return the **route key on the left** (`"ready"`), never the target node name on the right (`"Report"`).
> - Any `python:...` node with conditional transitions (non-`@Default`) **must** declare an explicit `@router`.

---

## Stop 4: Give the Model Hands — Tool Calling Loop (`ToolNode`)

**Scenario**: The model needs to call a calculator, search local notes, or query an API, inspect the tool output, and then answer the user (a standard ReAct loop).

In SkilledGraph, tool calling is not hidden behind an opaque agent wrapper—it is **an explicit, readable graph loop** (see `examples/10-tool-calling/`):

```text
                  Tool calls requested (@ToolCalls)
   +-------------+ ----------------------------> +--------------+
   |  Assistant  |                               | ExecuteTools |
   |  (# [Node]) | <---------------------------- | (#[ToolNode])|
   +-------------+    Unconditional (@Default)   +--------------+
         |
         | No tool calls; final answer ready (@Otherwise)
         v
       @End
```

### Look at `examples/10-tool-calling/workflow_en.md`:

```markdown
# [Config]
- **@host**: python:./host_en.py:main

# [Node] Assistant

Use the add tool to calculate the user's request, then answer with the result.

## [Transitions]
| Condition | Target |
| --- | --- |
| @ToolCalls | ExecuteTools |
| @Otherwise | @End |

# [ToolNode] ExecuteTools
- **@tools**: [add]

## [Transitions]
- @Default -> Assistant
```

### Four Essentials of Tool Calling:

1. **Dedicated `# [ToolNode] Name` header**:
   Use `# [ToolNode]`, not `# [Node]`. Inside it, declare `- **@tools**: [tool1, tool2]` or `- **@tools**: all` (which selects all tools passed to `build_graph`/`load_graph`).
2. **Two built-in routing signals (`@ToolCalls` and `@Otherwise`)**:
   - `@ToolCalls`: Matches automatically when the last message in merged `State.messages` is an `AIMessage` with non-empty `tool_calls`.
   - `@Otherwise`: Matches as a fallback when no tool calls were requested (the model produced its final text reply).
3. **Explicit return edge**:
   `ToolNode` does not magically jump back to the caller. You write `- @Default -> Assistant` so the resulting `ToolMessage` returns to `Assistant`.
4. **Where are the Python tool functions defined? In the Host!**
   Markdown only names `[add]`. The actual `@tool` function and `base_model.bind_tools([add])` are supplied by the Host when calling `load_graph(graph_path, model=bound_model, tools=[add])`.

Run Example 10 offline right now:
```bash
sgraph examples/10-tool-calling/workflow_en.md
```
Output:
```text
human: What is 2 + 3?
ai: 
tool: 5
ai: The result is 5
```

---

## Stop 5: Pause Mid-Execution for Human Input (`request_input`)

**Scenario**: Your agent drafted an email or needs clarification from the user. It should **pause (Interrupt)** mid-workflow, prompt the human in the terminal, and resume as soon as the human replies.

You don't even need a Python file for this! Use the built-in `request_input` backend (see `examples/11-interrupt/workflow_en.md`):

```markdown
# [Node] AskUser
- **@uses**: request_input:Please specify your preferred output format, e.g., short list.

## [Transitions]
- @Default -> Report

# [Node] Report
Respond according to the user's supplemental information.

## [Transitions]
- @Default -> @End
```

### How it works:
1. When execution reaches `AskUser`, it does **not** call the LLM. Instead, it triggers LangGraph's native `interrupt("Please specify...")`.
2. The standard terminal Host prints the prompt and shows `Resume>` to wait for keyboard input.
3. Once you type `"Markdown table"` and press Enter, execution resumes from the checkpoint.
4. `AskUser` wraps your reply into a new `HumanMessage("Markdown table")`, appends it to `State.messages`, and transitions to `Report`!
5. Need a multi-line prompt? Pass a JSON string on a single physical line:
   `- **@uses**: request_input:"Please provide:\n1. Target audience\n2. Word count"`

Try it interactively in your terminal (no API key needed):
```bash
sgraph examples/11-interrupt/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

---

## Stop 6: Write Your Own `@host` for Full Control

Why do some workflows omit `@host` while others declare `- **@host**: python:./host_en.py:main`?

- **Without `@host`**: `sgraph` uses the built-in chat Host (`sgraph_chat_host`), which reads one user message from the terminal, runs the graph once, prints AI replies, and exits.
- **When should you write a custom `@host`?**
  1. Your graph uses custom initial `State` fields (e.g., `{"value": 0, "events": []}` or file paths).
  2. Your graph uses `ToolNode` and needs `tools=[...]` and `model.bind_tools(...)`.
  3. You want custom CLI flags (`--demo`, `--input`) or custom output formatting.

### A custom Host is just a 10-line Python function!

Every Host entry is a synchronous Python function with the signature `main(graph_path: Path, argv: list[str]) -> int | None` (see `examples/09-state-only/host_en.py`):

```python
from pathlib import Path
from skilledgraph import load_graph

def main(graph_path: Path, argv: list[str]) -> int | None:
    # 1. Compile the Markdown workflow (pass model=..., tools=... if needed)
    graph = load_graph(graph_path)
    
    # 2. Invoke the native LangGraph object with your initial State
    result = graph.invoke({"value": 0, "events": []})
    
    # 3. Handle or print the output however you like
    print(result)
    return 0
```

Link it at the top of `workflow.md`:
```markdown
# [Config]
- **@host**: python:./host_en.py:main
- **@state**: python:./state_en.py:State
```

When you run `sgraph workflow.md -- --my-arg 123`, `sgraph` passes the absolute `Path` of `workflow.md` as `graph_path` and `["--my-arg", "123"]` as `argv`.

---

## Where to Go Next: Explore the Practical Agent Examples!

You now know all the core building blocks of SkilledGraph! To see how they combine into real-world applications, check out `examples/12-*` through `18-*` (all of which support `--demo` for offline execution):

1. **[12-evidence-assistant](../../examples/12-evidence-assistant/README_en.md)**: Local note QA (`ToolNode` search loop + `python` citation verification + bounded retry).
2. **[13-csv-auditor](../../examples/13-csv-auditor/README_en.md)**: CSV report auditor (`pyfunction` exact metrics injection + `python` numeric verification).
3. **[14-email-assistant](../../examples/14-email-assistant/README_en.md)**: Email triage & drafting (model classification + `request_input` human approval + file saving).
4. **[15-parallel-code-review](../../examples/15-parallel-code-review/README_en.md)** & **[16-batch-digest](../../examples/16-batch-digest/README_en.md)**: Use `build_graph()` to attach native parallel branches and dynamic `Send` Map-Reduce workers.

Whenever you need a quick syntax lookup or hit an error message while authoring your own graphs, flip to **[Part 3: DSL & Python Authoring Handbook (03-DSL-HANDBOOK_en.md)](03-DSL-HANDBOOK_en.md)**.
