# Part 1: 10-Minute Quickstart

[中文](01-QUICKSTART_cn.md) | [English](01-QUICKSTART_en.md) | [Back to Tutorials Home](README_en.md) | [Next: Step-by-Step Tutorial →](02-STEP-BY-STEP_en.md)

This guide walks you through SkilledGraph's core mental model and helps you run your first Markdown workflow in 10 minutes. **Even if you don't have an LLM API key handy, you can run every step using the built-in offline demo model.**

---

## 1. Why SkilledGraph?

When building LLM workflows (for example, on top of LangGraph), two friction points show up immediately:
1. **Prompts buried in Python code**: Multi-paragraph system prompts stuffed inside Python string literals are painful to read, diff, and iterate on.
2. **Hard-to-read graph topology**: You have to jump across `add_node`, `add_edge`, and `add_conditional_edges` calls just to see how the workflow moves from step to step.

**SkilledGraph solves this through clean separation of concerns:**

```text
+------------------------+       +------------------------+
|     workflow.md        |       |      actions.py        |
|------------------------|       |------------------------|
| 1. Nodes (# [Node])    | <---> | 1. Load local data     |
| 2. Node Prompts        |       | 2. Validate outputs    |
| 3. Transitions (->)    |       | 3. Custom State schema |
+------------------------+       +------------------------+
            \                               /
             \                             /
              v                           v
        +---------------------------------------+
        |  Compiles to 100% Native LangGraph    |
        +---------------------------------------+
```

- **Markdown (`.md`)** handles two things: **what to tell the model (Prompt)** and **where to jump next (Transitions)**.
- **Python (`.py`)** handles what code does best: reading files, calling APIs, validating data, and managing the runtime environment (Host).

---

## 2. Installation

Create a virtual environment in the project root and install SkilledGraph with the `[chat]` extra (which includes the LangGraph runtime and interactive terminal Host):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[chat]'
```

Once installed, you have the `sgraph` CLI command (you can also use `python -m skilledgraph`).

Let's run a built-in pure computation workflow that requires no API key to verify your installation:

```bash
sgraph examples/09-state-only/workflow_en.md
```

If your terminal prints `{'value': 2, 'events': ['incremented', 'doubled']}`, your environment is ready!

---

## 3. Your First Workflow: Single-Node Assistant

Create a new file named `hello.md` with these 6 lines:

```markdown
# [Node] Assistant

You are a witty programmer assistant. Answer the user's question in one sentence.

## [Transitions]
- @Default -> @End
```

### Breaking down those 6 lines:
1. **`# [Node] Assistant`**: Declares a node named `Assistant`. **The first node declared in the file is always the entry point of the workflow.**
2. **The body text**: Becomes the `SystemMessage` sent to the LLM. Whenever a node does not declare a custom `@uses` execution backend, it defaults to calling the chat model once.
3. **`## [Transitions]`**: Declares where to go after this node finishes.
4. **`- @Default -> @End`**: `@Default` means an unconditional edge, and `@End` terminates the workflow path.

### Step 1: Static syntax check (`--check`)

Before running anything, let SkilledGraph validate your Markdown syntax:

```bash
sgraph --check hello.md
```

Output:
```text
OK: /path/to/hello.md (1 nodes)
```
> **Tip**: `--check` is read-only and instant. It never imports Python files or spends API tokens.

### Step 2: Offline test run (No API key needed)

The repository includes an offline echo model (`examples/support/demo_model_en.py`) that echoes the last message with a prefix so you can verify your graph wiring offline:

```bash
printf 'What is recursion?\n' | sgraph hello.md -- --model-factory python:./examples/support/demo_model_en.py:create
```
*(Note: When `hello.md` is in the repository root, `./examples/support/demo_model_en.py` resolves relative to `hello.md`. The `--` separates `sgraph` launcher options from arguments passed to the Host.)*

Output:
```text
[Assistant] Demo reply (2 input messages): What is recursion?
```
Why does it say `2 input messages`? Because SkilledGraph packaged the node's prompt body as the 1st message (`SystemMessage`) and combined it with your input (`HumanMessage`)!

---

## 4. Connecting a Real LLM

Want a real LLM to answer? You don't need to change a single character in `hello.md`—**in SkilledGraph, model configuration belongs to the Host environment, never hardcoded inside the Markdown DSL.**

Here are the two easiest ways to connect a model:

### Option A: Interactive Setup Wizard (Recommended)

Simply run:

```bash
sgraph hello.md
```

If no model is configured yet, an interactive setup wizard launches automatically (you can also re-run it anytime with `sgraph hello.md -- --setup`):
1. **API Base URL**: e.g., `https://api.openai.com/v1`, or any OpenAI-compatible `/v1` endpoint (DeepSeek, OpenRouter, Ollama, LM Studio).
2. **Model ID**: e.g., `gpt-4o-mini`, `deepseek-chat`, etc.
3. **API Mode**: Usually `chat_completions` (or `responses` for OpenAI's Responses API).
4. **API Key**: Hidden input (enter `not-needed` for unauthenticated local servers).

Your profile is saved to `~/.config/skilledgraph/host.json` (mode `0600` on POSIX). Run `sgraph hello.md` again, type your question at the `Input>` prompt, and press Enter!

### Option B: Environment Variables

You can also configure connections via environment variables:

```bash
export SGRAPH_MODEL="openai:gpt-4o-mini"
export SGRAPH_BASE_URL="https://api.openai.com/v1"
export SGRAPH_API_KEY="sk-xxx"
export SGRAPH_TEMPERATURE=0

sgraph hello.md
```

---

## 5. Chaining Two Nodes: Multi-Step Pipeline

Now let's chain two nodes together in `chain.md`: first analyze the user's question, then condense the analysis into a slogan.

```markdown
# [Node] Analyze

List the 3 most important points about the user's question.

## [Transitions]
- @Default -> Summarize

# [Node] Summarize

Condense the points above into a punchy slogan under 15 words.

## [Transitions]
- @Default -> @End
```

### Three Core Rules to Remember:

1. **Declaration order ≠ execution order**:
   `Analyze` runs first because it is the first node in the file. However, it moves to `Summarize` **only because we wrote `- @Default -> Summarize`**, not because `Summarize` is written below it!
2. **Conversation history is automatically inherited (default `MessagesState`)**:
   - When `Analyze` runs, the model receives: `[SystemMessage(Analyze prompt), HumanMessage(user question)]`.
   - `Analyze`'s `AIMessage` reply is appended to `State.messages`.
   - When `Summarize` runs next, the model receives: `[SystemMessage(Summarize prompt), HumanMessage(user question), AIMessage(Analyze reply)]`.
3. **Node prompts never pollute message history**:
   `Analyze`'s system prompt is only used during `Analyze`'s call and is **not** saved into `State.messages`. When execution reaches `Summarize`, the system prompt cleanly switches to `Summarize`'s body text.

Verify this behavior right now with Example 02:

```bash
printf 'Analyze the pros and cons of remote work\n' | sgraph examples/02-chain/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

Output:
```text
[Analyze] Demo reply (2 input messages): Analyze the pros and cons of remote work
[Report] Demo reply (3 input messages): Demo reply (2 input messages): Analyze the pros and cons of remote work
```
Notice how `Analyze` saw 2 messages, while `Report` saw 3 messages (including `Analyze`'s output)!

---

## 6. Summary & What's Next

You now know the fundamental skeleton of SkilledGraph:
- `# [Node] Name` defines a node whose body is its `SystemMessage`.
- `## [Transitions]` defines outgoing edges (`- @Default -> Target` or `@End`).
- `sgraph --check` validates syntax; `sgraph workflow.md` executes the graph.

Next, what if your workflow needs to:
- **Branch conditionally** based on the model's decision or Python validation?
- **Load local files or database records in Python** before calling the model (`pyfunction`)?
- **Call tools in a loop** (`ToolNode`)?
- **Pause execution to ask the human user for confirmation** (`request_input`)?

Continue to **[Part 2: Step-by-Step Practical Tutorial (02-STEP-BY-STEP_en.md)](02-STEP-BY-STEP_en.md)**!
