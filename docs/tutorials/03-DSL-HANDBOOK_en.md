# Part 3: DSL & Python Authoring Handbook (Cheat Sheet)

[中文](03-DSL-HANDBOOK_cn.md) | [English](03-DSL-HANDBOOK_en.md) | [← Previous: Step-by-Step Tutorial](02-STEP-BY-STEP_en.md) | [Tutorials Home](README_en.md)

This handbook is your **day-to-day desk reference** when authoring SkilledGraph workflows. It distills the formal language specification in `docs/standard/v0.1/` into visual syntax cards, comparison tables, code templates, and a troubleshooting guide.

---

## 1. Anatomy of a DSL File at a Glance

Every `.md` workflow file consists of **an optional preamble + an optional `# [Config]` + one or more `# [Node]` / `# [ToolNode]` blocks**:

```markdown
Optional file preamble (before the first directive header).
The preamble does not belong to any node and is never sent to the model.

# [Config]
- **@host**: python:./host.py:main
- **@state**: python:./actions.py:State

# [Node] Step1
- **@uses**: pyfunction:./actions.py:load_data
- **@router**: python:./actions.py:decide_next

>>> Author note (starts with >>> at column 1). Never sent to the LLM.

This is Step1's node prompt body.
It can contain paragraphs, lists, or closed Markdown code fences:
```markdown
# [Node] FakeNode inside a closed code fence is treated as literal prompt text!
```

## [Transitions]
| Route Key | Target Node | Notes |
| --- | --- | --- |
| ok | Step2 | Data looks good; proceed |
| need_tool | RunTools | Execute requested tools |

# [ToolNode] RunTools
- **@tools**: [search, calculate]

## [Transitions]
- @Default -> Step1

# [Node] Step2
Write the final conclusion based on the conversation history.

## [Transitions]
- @Default -> @End
```

### Four Golden Structural Rules:
1. **Start at column 1**: All `# [Config]`, `# [Node]`, `# [ToolNode]`, `## [Transitions]`, `- **@KEY**: VALUE`, and `>>>` notes **must start at physical column 1** (no leading indentation).
2. **Strictly case-sensitive**: `# [Node] A` is a node, whereas `# [node] A` is treated as an ordinary Markdown heading! `@Default`, `@End`, `@ToolCalls`, and `@Otherwise` are also case-sensitive.
3. **Entry point & order**: The **first node declared in the file** is always the entry point (`START -> first node`). Node order does **not** create implicit edges—all transitions must be declared in `## [Transitions]`.
4. **`Transitions` comes last**: Each node may have at most one `## [Transitions]` block, and it must be the last section of that node. Do not place prompts, `>>>` notes, or `- **@uses**` below `## [Transitions]`.

---

## 2. The Settings (`@KEY`) Cheat Sheet

Settings always use the exact syntax `- **@KEY**: VALUE` (note `**@` together and the colon outside the bold markers).

Allowed keys depend strictly on the scope:

| Setting | Allowed Scope | Format Examples | Purpose |
| --- | --- | --- | --- |
| **`@host`** | `# [Config]` | `- **@host**: python:./host.py:main` | Python entry function invoked when running `sgraph workflow.md`. Defaults to the standard chat Host if omitted. |
| **`@state`** | `# [Config]` | `- **@state**: python:./state.py:State` | Native LangGraph `State` Schema (`TypedDict` or `MessagesState` subclass). Defaults to `MessagesState` if omitted. |
| **`@uses`** | `# [Node]` | `- **@uses**: pyfunction:./a.py:fn`<br>`- **@uses**: python:./a.py:fn`<br>`- **@uses**: request_input:Prompt`<br>`- **@uses**: monty:./calc.py` | Selects the execution backend for the node. If omitted, the node calls the chat model once with its prompt body. |
| **`@router`** | `# [Node]` or `# [ToolNode]` | `- **@router**: python:./a.py:route`<br>`- **@router**: monty:./route.py` | Callable executed after the node's State update is merged; returns a route key string. |
| **`@tools`** | **`# [ToolNode]` ONLY (Required)** | `- **@tools**: all`<br>`- **@tools**: [add, search_notes]` | Selects which Host-supplied tools this `ToolNode` executes (unquoted names, no trailing comma). **Not allowed in `# [Node]`.** |

> **Tip**: Writing `- **Important**: note` or `- @uses: xxx` (without bold) in a node body is treated as ordinary prompt text. However, starting a top-level list item with `- **@` triggers strict directive validation—typos like `- **@model**: gpt-4` raise an immediate `ParseError` instead of silently leaking into your prompt!

---

## 3. Side-by-Side Comparison of All 5 Node Execution Modes

What a `# [Node]` does is determined by its `- **@uses**` setting:

| Mode | `@uses` Syntax | Calls LLM Automatically? | How is Node Prompt Body Handled? | What does Python Receive & Return? | Best Used When... |
| --- | --- | --- | --- | --- | --- |
| **1. Default Prompt Node** | *(Omit `@uses`)* | **Yes (once)** | Sent as `SystemMessage` for this call (not saved in history) | No Python function needed. Sends `[SystemMessage(body), ...history]` to model; appends `AIMessage` reply to `messages`. | Chatting, summarizing, translating, or classifying via model text routing. |
| **2. Material Function (`pyfunction`)** | `pyfunction:./file.py:fn` | **Yes (once)** | Sent as `SystemMessage` for this call (not saved in history) | **Input**: `state`<br>**Return**: Material (`str`/`dict`/`list`/`BaseMessage`), **NOT a State update dict**. Material becomes a `HumanMessage`; both material and AI reply are appended to `messages`. | Fetching local files, database rows, or computed metrics in Python right before prompting the LLM. |
| **3. Native Code Node (`python`)** | `python:./file.py:fn` | **No** | Ignored by builtin runner (custom bindings can read `node.prompt`) | **Input**: `state` (plus optional native `config`/`runtime`)<br>**Return**: Native LangGraph State update dict (e.g. `{"count": 1}`) or `Command`. | Deterministic validation, regex parsing, updating counters/status fields, pure code steps. |
| **4. Interactive Prompt (`request_input`)** | `request_input:Prompt text` | **No** | Ignored | No Python function needed. Calls native `interrupt(prompt)`; resumed string becomes a new `HumanMessage`. | Pausing mid-workflow to ask the user for missing details or approval. |
| **5. Sandbox Expression (`monty`)** | `monty:./script.py` *(No `:entry`)* | **No** | Ignored | Reads JSON-compatible `state` variable; **the final expression in the file** is the returned State update dict (or route key string for `@router`). | Resource-capped (32 MiB RAM, 1s timeout), file/network-isolated pure data transformations. |

### Golden Rules for File References (`python:FILE:ENTRY` / `pyfunction:FILE:ENTRY`):
1. **`FILE` must start with `./`, `../`, or be an OS-native absolute path**. Bare filenames (`python:tools.py:run`) and dotted module paths (`python:pkg.tools:run`) are invalid—always write `python:./tools.py:run`.
2. **Relative paths always resolve against the directory containing the `.md` file**, regardless of your shell's current working directory.
3. **`ENTRY` must be a simple identifier** (no parentheses like `:create()` or dotted attributes).

---

## 4. Routing & `## [Transitions]` Complete Guide

### 4.1 Two Formats (List OR Table, Never Mixed)

**List format**:
```markdown
## [Transitions]
- pass -> Publish
- fail -> Rewrite
```

**Table format** (columns 3+ are free-form human documentation):
```markdown
## [Transitions]
| Route Key | Next Node | Condition Description (Ignored at runtime) |
| --- | --- | --- |
| pass | Publish | Validation passed; publish report |
| fail | Rewrite | Errors found; send back for revision |
```

### 4.2 Four Reserved `@` Markers

| Marker | Position | Meaning & Constraints |
| --- | --- | --- |
| **`@Default`** | Route Key (Left / Col 1) | **Single unconditional edge**. Always jumps to the target. **Cannot be mixed with any other route keys** (it is NOT an `else` fallback!). |
| **`@End`** | Target (Right / Col 2) | Ends the current workflow path (maps to LangGraph `END`). Cannot be abbreviated as `- @End`; write `- @Default -> @End`. |
| **`@ToolCalls`** | Route Key (Left / Col 1) | Matches when the last message in merged `State.messages` is an `AIMessage` with non-empty `tool_calls` (highest priority; skips `@router`). |
| **`@Otherwise`** | Route Key (Left / Col 1) | **True conditional fallback (`else`)**. Matches when neither `@ToolCalls` nor any ordinary route key matched. |

### 4.3 How Conditional Route Keys Are Resolved (Decision Flow)

```text
Node finishes execution & output is merged into State by Reducers
                               |
                               v
  [Is @ToolCalls in the table AND last AIMessage has tool_calls?]
         | Yes                                   | No
         v                                       v
  Jump to @ToolCalls target           [Does node declare - **@router**?]
                                         | Yes                   | No
                                         v                       v
                               Call router(state) to    [Is it a Default Prompt or pyfunction node?]
                               get route key string       | Yes                   | No (e.g. python node)
                                         \                v                       v
                                          \     Use reply.text.strip()     BuildError at build time!
                                           \        as route key           (@router is required)
                                            \            /
                                             v          v
                                     [Does route key match a table row?]
                                         | Yes           | No
                                         v               v
                                  Jump to target   [Is @Otherwise in the table?]
                                                     | Yes           | No
                                                     v               v
                                              Jump to @Otherwise  Raise RoutingError!
```

---

## 5. `State`, Message History & Reducers

### 5.1 Default State: `MessagesState`
When `# [Config]` omits `@state`, the graph uses LangGraph's `MessagesState`:
```python
messages: Annotated[list[AnyMessage], add_messages]
```
- **Incremental updates only**: Because `add_messages` appends new messages, your Python nodes should return **only the newly created message(s)**:
  ```python
  # Correct: return only the new message(s)
  return {"messages": [AIMessage(content="Validation passed")]}
  ```
- **Extra State fields are not auto-injected into prompts**: If you define `class State(MessagesState): score: int`, ordinary prompt nodes still pass only `state["messages"]` to the model. To show `score` to the model, return it from a `pyfunction` or format it into a message inside a `python` node.

### 5.2 Custom State & Reducers
Define any native LangGraph `TypedDict` or `MessagesState` subclass in Python:

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add
from langgraph.graph import MessagesState

# Option 1: Extend MessagesState (keeps chat history + adds custom fields)
class AgentState(MessagesState):
    attempts: int                           # Overwritten on each update
    logs: Annotated[list[str], add]         # Appended via operator.add

# Option 2: Pure computation State (no messages field; use python/monty nodes)
class CalcState(TypedDict):
    value: int
    events: Annotated[list[str], add]
```

---

## 6. Python API Integration & Mixing Native LangGraph

Beyond the `sgraph` CLI, you can embed SkilledGraph directly in any Python service using its **3 public functions**:

```python
from skilledgraph import parse_graph, build_graph, load_graph
```

### Pattern 1: Compile and Run Directly (`load_graph`)
```python
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from skilledgraph import load_graph

# Returns a 100% native LangGraph CompiledStateGraph
graph = load_graph(
    "my_workflow.md",
    model=my_langchain_model,                        # Optional chat model
    tools=[my_tool_1, my_tool_2],                    # Optional tools list
    state_schema=MyCustomState,                      # Optional override for @state
    compile_kwargs={"checkpointer": InMemorySaver()} # Forwarded to builder.compile()
)

result = graph.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"thread_id": "user-123"}}
)
```

### Pattern 2: Modify the Native Builder Before Compiling (`build_graph`)
Need native LangGraph features not expressed in Markdown syntax (such as **parallel fan-out / fan-in joins**, as in `examples/15-parallel-code-review/`)? Use `build_graph()` to get the native `StateGraph` builder, add native edges, and compile:

```python
from skilledgraph import build_graph

builder = build_graph("workflow.md", model=my_model)

for reviewer in ("Correctness", "Security", "Style"):
    builder.add_edge("Prepare", reviewer)
builder.add_edge(["Correctness", "Security", "Style"], "Synthesize")

graph = builder.compile()
```

### Pattern 3: Register Custom `@uses` Backends (`bindings`)
Want your own custom `@uses` prefix (e.g., `- **@uses**: my_rag:product_docs`)? Pass a `bindings` dict:

```python
from langchain_core.messages import HumanMessage
from skilledgraph import load_graph

def bind_my_rag(payload: str, *, base_dir, node, model=None):
    # payload is "product_docs"; node.prompt is the Markdown body text
    def run_node(state):
        docs = search_database(collection=payload, query=state["messages"][-1].text)
        return {"messages": [HumanMessage(content=f"Docs: {docs}\nTask: {node.prompt}")]}
    return run_node

graph = load_graph("workflow.md", model=my_model, bindings={"my_rag": bind_my_rag})
```

---

## 7. Top 10 Common Pitfalls (Troubleshooting Table)

| Symptom / Error Message | Why It Happened | How to Fix It |
| --- | --- | --- |
| **1. Wrote `# [node] Test` or indented `  - **@uses**: ...`, and it was sent as literal prompt text** | Directives are strictly case-sensitive and **must start at column 1**. | Use `# [Node] Test` and unindented `- **@uses**: ...` at column 1. |
| **2. `Unknown setting` or error when writing `- **@model**: ...` in `# [Config]`** | `# [Config]` only accepts `@host` and `@state`. Model settings belong to the Host environment, never the DSL. | Remove `@model`; configure models via `sgraph workflow.md -- --setup` or `SGRAPH_MODEL`. |
| **3. `Cannot bind 'python:tools.py:run'` (file error)** | Built-in file references require an explicit `./`, `../`, or absolute path prefix. | Change to `- **@uses**: python:./tools.py:run`. |
| **4. `Node 'X' needs @router: this execution binding has no implicit route-key protocol`** | A `python:...` or `request_input:...` node has conditional transitions (non-`@Default`) without a `@router`. | Add `- **@router**: python:./tools.py:my_router` to the node. |
| **5. `Node 'X' returned route 'Report'; legal keys: ('ready', 'missing')`** | Your `@router` or model returned the **target node name** (`Report`) instead of the **route key** (`ready`), or included extra text. | Return the route key on the left side of `->` (`'ready'`), with no extra commentary. |
| **6. Wrote `- @Default -> Fallback` inside a conditional table as a catch-all and got a parse error** | `@Default` is an unconditional edge and **cannot be mixed** with conditional keys. | Use **`@Otherwise`** for catch-all fallback rows (`- @Otherwise -> Fallback`). |
| **7. Wrote `- @End` and got a parse error** | `@End` is a target (right side of `->`), not a route key. | Write `- @Default -> @End`. |
| **8. Wrote `- **@tools**: [add]` inside `# [Node]` and got an error** | `@tools` is only valid inside `# [ToolNode]`. | Move tool execution into `# [ToolNode] ExecuteTools` and jump to it via `- @ToolCalls -> ExecuteTools`. |
| **9. A `pyfunction` returned `{"status": "ok"}`, but `state["status"]` was not updated** | `pyfunction` is a **material function**—its return value is converted into a `HumanMessage` for the LLM, not merged into `State` fields. | Use `- **@uses**: python:./file.py:fn` when you want to update `State` fields directly. |
| **10. Put `>>> note` or prompt text below `## [Transitions]` and got a parse error** | `## [Transitions]` must be the final section of a node. | Move all prompt text, `>>>` notes, and `- **@uses**` **above** `## [Transitions]`. |

---

## 8. 3-Step Authoring Checklist

Whenever you (or an AI coding assistant) create a new SkilledGraph workflow, run through these 3 steps:

1. **Step 1: Static syntax check**
   ```bash
   sgraph --check path/to/workflow.md
   ```
2. **Step 2: Offline branch verification**
   Use `--model-factory` with a deterministic offline `DemoModel` (or a `--demo` flag in your custom Host) to exercise every conditional branch and retry limit before spending API tokens.
3. **Step 3: Live LLM evaluation**
   Run against your real LLM provider to verify prompt adherence.

---

[← Previous: Step-by-Step Tutorial](02-STEP-BY-STEP_en.md) | [Tutorials Home](README_en.md)
