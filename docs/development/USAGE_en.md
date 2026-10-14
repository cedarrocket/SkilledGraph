# Using SkilledGraph v0.1

SkilledGraph compiles Markdown into native LangGraph graphs. An ordinary node calls the model once; @uses selects a Hardcode_Execution_Backend for code. Host owns complex I/O, model options, and resource lifetimes.

Basic chat Host is an independent [example](../../examples/chat-host/README_en.md), namespace sgraph_chat_host, source examples/chat-host/src. Default launcher selects it only without @host; parse/build APIs do not import it. Reuse model/terminal helpers from sgraph_chat_host.host or their _en counterparts, not removed skilledgraph.host/terminal modules.

## Install and run offline

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[chat]'
```

Parser-only: -e .; native code or supplied model: -e '.[runtime]'. chat includes native runtime and LangChain model initialization; install the desired provider integration separately.

No service/key needed:

```sh
sgraph examples/09-state-only/workflow_en.md
printf 'Hello\n' | sgraph examples/01-assistant/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

The first uses its file Host to output value=2 and two events. The second is a scripted echo demonstrating plumbing, not LLM intelligence.

## A few Markdown lines

Save hello.md:

```markdown
# [Node] Assistant
Be concise and answer the user's question.

## [Transitions]
- @Default -> @End
```

Read-only syntax check:

```sh
sgraph --check hello.md
```

For a real model, install its LangChain integration and replace provider:model with its actual identifier; configure its key/local service:

```sh
export SGRAPH_MODEL='provider:model'
sgraph hello.md
```

Host uses [init_chat_model](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model). Alternatively select --model provider:model for one run.

Terminal reads one line, runs once from entry, and exits; EOF/blank line exits. Pipe input is one complete message, including newlines, e.g. cat input.txt | sgraph hello.md. Output is `[node] reply` for all AI replies, including route keys. prompt-toolkit supports arrows, Home/End/Delete, common Emacs keys, and process-local history. Enter submits, Ctrl-D exits empty input, Ctrl-C cancels. Dedicated multiline editing and persistent history are absent.

Basic Host uses InMemorySaver and a new thread_id per run. Dynamic interrupt values are displayed; string replies resume the same execution via Command. Nodes decide how to use resume values; they do not automatically become messages. Simultaneous interrupts map by ID; successive interrupts can resume repeatedly. JSON prompts are possible, but complex forms, typed replies, static breaks, and process-independent recovery require custom Host. Pipe interruption errors; EOF while answering returns 1 without an empty reply; intentional Enter produces a valid empty string.

Offline interaction:

```bash
python -m skilledgraph examples/11-interrupt/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

After initial input, answer Resume>; Report then runs and exits. Reusing run_chat requires an enabled checkpointer. Native resume restarts the interrupted node; authors must manage earlier side effects. See [interrupt documentation](https://docs.langchain.com/oss/python/langgraph/interrupts).

## Material and routing

Companion tools_en.py:

```python
def prepare(state):
    return "Record A: 12; record B: 8."
```

```markdown
# [Node] Report
- **@uses**: pyfunction:./tools_en.py:prepare
Summarize the current material.

## [Transitions]
- @Default -> @End
```

pyfunction receives State. Material, body, and history go to model; new material and reply enter messages, body does not. None/empty list adds no material but still invokes. Return native LangChain messages to control roles.

python runs native nodes without automatic model calls and allows State updates/Command. @router reads merged State and returns a table key. Relative paths use DSL directory. See [examples](../../examples/README_en.md).

## Load and extend in Python

```python
from skilledgraph import parse_graph, build_graph, load_graph
spec = parse_graph("examples/09-state-only/workflow_en.md")
graph = load_graph(spec)
result = graph.invoke({"value": 0, "events": []})
```

parse imports nothing; build returns Builder; load returns compiled graph. Neither runs @host. Supply model, schemas, context_schema, bindings, and tools; load additionally forwards compile_kwargs.

Reducers are native Python schema annotations selected by state_schema/@state, without backend wrapping. Pure code graphs need no messages; Prompt/pyfunction do. User reducers own resulting semantics.

Model interface is invoke(messages, config=...) -> AIMessage; async needs ainvoke. Native chat models fit; results are not guessed into messages.

Bindings use bind(payload, *, base_dir, node, model=None), returning native Callable/Runnable. Node is immutable NodeSpec. Overriding registry python does not change Host/Schema loaders. See [M2](M2_BUILDING_en.md) for caching/contract.

## Custom model or Host

Use a zero-argument factory for temperature/provider options/client construction, without syntax changes. Example my_model_en.py:

```python
import os
from langchain.chat_models import init_chat_model

def create():
    return init_chat_model(os.environ["SGRAPH_MODEL"], temperature=0)
```

```sh
sgraph hello.md -- --model-factory python:./my_model_en.py:create
```

SGRAPH_MODEL_FACTORY is also accepted. Explicit CLI selection overrides both environment selectors; environment-only factory precedes SGRAPH_MODEL. Factory path uses graph directory. Model lasts through Host execution; builder does not close it automatically.

For business I/O or non-message input, define synchronous Host:

```python
from pathlib import Path
from skilledgraph import load_graph

def main(graph_path: Path, argv: list[str]) -> int | None:
    graph = load_graph(graph_path)
    print(graph.invoke({"value": 0, "events": []}))
    return 0
```

Select at file start:

```markdown
# [Config]
- **@host**: python:./host_en.py:main
- **@state**: python:./state_en.py:State
```

Launcher passes absolute file path and remaining arguments; sgraph graph.md -- --custom value yields ["--custom", "value"]. Host builds, returns int/None, and manages async internally. Do not recursively call CLI to load the same Host.

## Tests and support

```sh
python -m unittest discover -s tests -v
```

Deterministic acceptance uses scripted models without paid services. Scope/versions/limits: [M3–M5](M3_M5_COMPLETION_en.md). Deferred syntax includes file-level backends, modules, output Schema, failure routes, and retries.

## Tools

```bash
python -m skilledgraph examples/10-tool-calling/workflow_en.md
```

Expect tool: 5 and final ai: Result is 5. Scripted model emits requests; native add executes.

Real models are bound by custom Host:

```python
bound_model = base_model.bind_tools([add])
graph = load_graph(graph_path, model=bound_model, tools=[add])
result = graph.invoke({"messages": [HumanMessage(content="What is 2 + 3?")]})
```

This fragment assumes prepared imports/objects; [complete Host](../../examples/10-tool-calling/host_en.py).

Declare `# [ToolNode] ExecuteTools` with @tools all/[add]. Ordinary Node cannot declare @tools. Model routes @ToolCalls to execution, @Otherwise to final answer/end; execution explicitly returns to model. There is no implicit loop/return.

Compatible MCP tools use tools parameter; Host owns connection, credentials, and async lifetimes. Initial tool-extension acceptance did not include MCP; later local acceptance is below. Async tools need ainvoke/astream. Full rules: [specification](../standard/v0.1/LANGUAGE_SPEC_en.md); scope: [tool report](TOOLS_COMPLETION_en.md).

## Environment connection options

These are Host configuration, not DSL attributes:

| Variable | Meaning |
| --- | --- |
| SGRAPH_MODEL / SGRAPH_MODEL_FACTORY | model selector or factory |
| SGRAPH_API_KEY | explicit key |
| SGRAPH_API_KEY_FILE | one-line key file, mutually exclusive with direct key; ~ expanded; relative to graph |
| SGRAPH_BASE_URL | integration base_url |
| SGRAPH_TEMPERATURE | finite nonnegative float |
| SGRAPH_TIMEOUT | finite positive seconds |
| SGRAPH_MAX_TOKENS | positive integer |
| SGRAPH_MAX_RETRIES | nonnegative integer |

Unset options do not replace integration defaults. Without explicit key, provider variables such as DEEPSEEK_API_KEY remain native. No automatic key search or OpenCode configuration/credential import. Factory owns connection and does not automatically receive these options; provider-specific options can be implemented there.

Install deepseek extra and set:

```bash
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
python -m skilledgraph examples/01-assistant/workflow_en.md
```

See [live entry](../../tests/live/README_en.md) and [DeepSeek report](DEEPSEEK_ACCEPTANCE_en.md).

## Local MCP

The [stdio example](../../tests/mcp_demo/README_en.md) starts/cleans its own service without global configuration. With provider setup, pipe a request to tests/mcp_demo/workflow_en.md. Scope: [MCP acceptance](MCP_ACCEPTANCE_en.md).

## Text input without Python

```markdown
# [Node] AskUser
- **@uses**: request_input:Please specify the output format.

## [Transitions]
- @Default -> @End
```

request_input does not call model: native interrupt carries payload; string resume creates HumanMessage. Body is ignored. Long text is one physical line; JSON strings permit escaped line breaks, e.g. request_input:"First line\nSecond line", not physical multiline. Backend decodes, not parser. Reply is not an implicit key; router is needed. API-only input graphs need no model, but standard Host still configures one.

## First-run wizard

Install chat extra, including langchain-openai. Interactive use with no CLI/environment model/factory or saved config launches setup. Or run --setup explicitly; it configures and exits. Automatic initial setup continues the current graph.

Collect:

1. Base URL, e.g. https://api.openai.com/v1; not full /chat/completions or /responses endpoint.
2. Provider's model ID; no enumeration.
3. Chat Completions or Responses mode.
4. Hidden key; Enter reuses SGRAPH_API_KEY/FILE or OPENAI_API_KEY without copying environment credentials to disk. Unauthenticated local service can use not-needed.
5. Optional hidden static header JSON, e.g. {"X-Session-ID":"your-session"}; Enter skips. SGRAPH_HEADERS_JSON replaces saved headers as a whole.

Language order: SGRAPH_LANGUAGE, LC_ALL, LC_MESSAGES, LANG. Chinese locale chooses Chinese; others English. With no variables, inspect Python's system locale without setlocale or installed-OS-locale requirements. Explicit zh/en overrides. Original language-selection tests ran on Linux; subsequent Windows scope is separately reported.

Path precedence: SGRAPH_HOST_CONFIG; otherwise XDG_CONFIG_HOME/skilledgraph/host.json; Windows APPDATA when no XDG; fallback ~/.config/skilledgraph/host.json. Entered credentials/headers are plaintext, mode 0600 on POSIX; Windows relies on user-directory access. Secret input is excluded from history. EOF/Ctrl-C leaves existing file unchanged. Saved profile is explicitly marked unverified; no connection check occurs.

Explicit CLI model/factory overrides environment; any explicit selector prevents reading saved gateway/key. Only when saved model is selected do SGRAPH options override saved parameters. Provider variables remain native; factory owns everything. --setup replaces profile without running graph or using current selection. Pipes never launch wizard or consume graph input for setup; missing config errors.

Scope: OpenAI-style Chat Completions/Responses and static headers. OpenCode Zen may use different protocols; follow [endpoint table](https://opencode.ai/docs/zen/), limited here to those two modes. No subscription OAuth/auth/login/config import. The initial wizard did not generate sessions; the subsequent Go extension below does. External use rights are not certified. Complex integration uses factory/custom Host.

### OpenCode Go supplement

Send own User-Agent and stable x-opencode-session per [Go docs](https://opencode.ai/docs/go/). Static example:

```json
{"User-Agent":"skilledgraph/0.1.0.dev0","x-opencode-session":"your-conversation-id"}
```

For https://opencode.ai/zen/go/v1, basic Host now adds missing identity and sgraph-harness-agent-<UUID> session automatically. Each startup creates one model/new session; all node/tool/resume calls reuse it.

Explicit case-insensitive headers win. Remove a saved static session to enable automatic generation. Custom Hosts reusing a model across conversations own boundaries; factory is untouched. Generated headers are not saved or sent to other URLs. Tested glm-5.3-flash uses this base, Chat Completions, and that exact ID. Ordinary coding requests/tool loops passed; other models need their own protocol and tests. See [Go acceptance](OPENCODE_GO_ACCEPTANCE_en.md).
