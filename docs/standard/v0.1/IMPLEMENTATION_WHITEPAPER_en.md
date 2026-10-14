# SkilledGraph v0.1 Implementation Whitepaper

> 2026-10-09: tool calling is implemented. The appended extensions update earlier allowlists, interfaces, and scope.

Status: current design and implementation contract. Date: 2026-10-09. The agreed M1–M5 scope is implemented and deterministically verified; see the [development guide](DEVELOPMENT_GUIDE_en.md). Input rules are in the [language specification](LANGUAGE_SPEC_en.md). Framework responsibilities and builtin policies are separate; a builtin policy is not automatically mandatory for all backends.

Reading order: §§1–4 cover architecture, data, and API; §§5–7 cover binding and execution ownership; §§8–11 cover builtin behavior; §§12–13 cover native extensions and deferred work.

Terms: Schema is a native structure definition; State is native graph execution state; Reducer is a native field-update merge function. Body is a statically extracted DSL string; model messages are call inputs/outputs. Neither automatically means persisted conversation history. Hardcode_Execution_Backend denotes code execution/adaptation such as python/pyfunction, not a model provider or Host.

## 1. Architecture and responsibilities

```text
DSL file
  → read-only parsing and static validation
  → GraphSpec
  → select schema, bind references and model dependencies
  → native StateGraph Builder
  → native compile()
  → native compiled graph; Host calls invoke/ainvoke/stream
```

| Component | Owns | Does not own |
| --- | --- | --- |
| Parser | Markdown context, structure, exact body, source locations, static edge checks | importing scripts, checking objects, model calls |
| Binding/building | native definitions, resources, nodes/edges, returning Builder | executing business nodes or file Host |
| Default Prompt | model invocation/update without uses | automatic tools or injecting all State fields |
| Hardcode_Execution_Backend | payload interpretation, code/result adaptation, body handling | whole-graph Schema or replacement scheduling |
| Host | model configuration, I/O, initial State, resources, graph lifecycle | changing syntax or mandatory custom runtime wrappers |
| LangGraph | State/reducers, scheduling, persistence, interrupts and streaming | interpreting SkilledGraph text/references |

The core compiles and binds graphs, without a second runtime. Host manages resources; native Checkpointer, Store, Context, Interrupt, and Streaming channels remain accessible. The basic chat Host is an independent [standard example](../../../examples/chat-host/README_en.md), installed from examples/chat-host/src/sgraph_chat_host rather than src/skilledgraph. It does not justify a general-purpose task-configuration language.

## 2. Read-only GraphSpec contract

parse_graph returns data only, preserving at least:

| Data | Required use |
| --- | --- |
| source path, original text, locations | relative paths and diagnostics |
| preamble, Config settings/locations | audit, Host/schema selection |
| node order, names, locations | entry and structural validation |
| settings, exact body, descriptions/locations | binding and review |
| transition format, source, keys/targets/locations | edge construction and diagnostics |

No imported functions, models, State instances, or compiled graphs belong in this representation. References remain original strings until binding. Original source differs from normalized body; rendered output alone is insufficient. Dataclass/dict representation, field names, and position conventions were implementation choices for the parser prototype; once selected, keep them consistent and documented without losing these uses.

## 3. Public API

The overall contract was provisionally confirmed; parse_graph, build_graph, and load_graph are now callable. Current runtime scope is described in [M3–M5](../../development/M3_M5_COMPLETION_en.md); M1 representation/diagnostics in its [report](../../development/M1_PARSER_en.md).

| API | Responsibility | Return |
| --- | --- | --- |
| parse_graph(path) | read and statically validate | GraphSpec |
| build_graph(path_or_spec, ...) | bind dependencies/schema, attach nodes and edges | native StateGraph Builder |
| load_graph(path_or_spec, ...) | same construction, then compile | native compiled graph |

build/load may import selected files but must not execute node functions, invoke models, or start @host. load adds no proprietary runtime wrapper.

```python
builder = build_graph(
    path_or_spec,
    state_schema=MyState,
    input_schema=MyInput,
    output_schema=MyOutput,
    context_schema=MyContext,
    model=my_model,
    bindings=my_bindings,
)
```

Parameters may be omitted when unused; actual capabilities need their dependencies. load takes the same parameters plus compile_kwargs, passed to native compile(). Use Builder for more complex construction. No framework config object or base class is required.

### 3.1 Schema selection

state_schema precedence: explicit argument → file @state → default message State. Omitted/None means no override. An overridden reference is not imported first, but its declaration stays in GraphSpec. Other schemas have no DSL settings; omission uses native defaults. context_schema describes structure; actual Context is supplied at execution.

Pass schemas unchanged: no default fields/reducers restored and no annotations rewritten. Host should respect file declarations unless intentionally overriding with state_schema.

Reducers are defined in Python and executed by LangGraph, not node/router Hardcode_Execution_Backend. No reducer wrapper, registry, or compatibility-repair layer is added. Builtin convenience behavior is primarily tested with message State; arbitrary reducers need not preserve it.

### 3.2 Model dependency

Host supplies the model. Default Prompt/pyfunction use LangChain chat models or compatible objects: invoke(messages), or ainvoke(messages), returning native model messages. No new model base class, mandatory structured output, or compatibility with every arbitrary Runnable return is implied.

Builder does not select models, read keys, set temperature, or launch Host. Pure Python graphs may omit models; required missing dependencies fail. User nodes may use other SDKs. Runtime config/provider compatibility needs tests; a synchronous model is not implicitly asynchronous.

## 4. Host and launcher

A file Host is an external synchronous function:

```python
def main(graph_path: Path, argv: list[str]) -> int | None:
    ...
```

The launcher parses read-only to select @host. Without one, it lazily imports standard chat Host sgraph_chat_host.host.main. Explicit file Hosts and --check do not import that example. It passes absolute DSL path and remaining argv. This is the graph path, not installation path; Host need not guess cwd or search argv. Integer is exit code; None is success.

Host supplies model/schema/resources, calls build/load, and handles initial State, output, and lifetimes. Launcher does not prebuild. No Host base class, plugin lifecycle, or I/O mapping protocol is required. Command is sgraph; arguments after the file go to Host, optionally separated by --. Standard Host selects model via --model/--model-factory or environment; see [usage](../../development/USAGE_en.md). Async applications organize their event loop inside the synchronous entry; a separate async Host protocol is undefined.

parse/build/load never start file Host. Model settings, pipes, and complex I/O remain outside Config.

### 4.1 Basic chat behavior

Read one input, run the graph from its first node, then exit. Terminal reads one line; pipe reads all stdin. EOF/blank terminal input does not run. Nodes within the execution still share/update State through the selected reducer. Host does not loop over new chats.

Display all replies from this run, including route-key replies, rather than final reply only. Displaying does not resubmit old content as next-run input.

Dynamic interrupt string interaction is now provided, as described below. Starting a new request at entry does not restrict native resume APIs. Compatibility requires tests; token streaming, display layout, and other event presentation are not frozen here.

## 5. Registry and unified binding

bindings maps execution names to Hardcode_Execution_Backend implementations. Initial builtins are python/pyfunction; later sections add request_input/monty. Partial mappings override/add named entries; unmentioned builtins remain. Unknown names fail, without fallback to python.

First colon separates registry name from opaque payload. Parser preserves the complete reference. Plain Prompt uses the supplied model and needs no prompt backend registration.

M2 selected ordinary binding functions:

```python
def bind(payload, *, base_dir, node, model=None):
    ...
    return callable
```

payload follows the prefix; base_dir is the graph directory; immutable NodeSpec holds name, settings, extracted body, and source spans. Model/dependencies are separate. These are binding resources, not extra required user-function parameters. Binding loads objects or creates closures/adapters; native execution later supplies State and supported runtime parameters. Do not confuse construction resources with runtime State. NodeSpec supersedes a narrower prompt-only sketch; it does not expose a mutable whole-graph builder.

uses/router share this entry; no bind_node/bind_router pair or required role parameter. Builder attaches the returned native callable/Runnable according to setting placement. Unified loading does not unify node-update and route-return contracts.

pyfunction adapts material functions, without a router protocol. Its model may select a route from the reply; that does not make its material function a router. This capability boundary is not a syntax-level prohibition on user extensions.

Custom bindings may close over existing Python objects rather than import files; deferred module-reference syntax must not block this channel. Do not invent universal Context/result-envelope classes. Host/State loaders are separate slots: overriding registry python does not change their loading. Revisit this arrangement only upon a concrete conflict, without premature configuration layers.

## 6. Builtin file references

```text
python:FILE:ENTRY
pyfunction:FILE:ENTRY
```

python may resolve a node callable, router, Schema, or Host entry depending on slot. Host/State loading does not use the replaceable node registry. pyfunction is currently a material-node adapter; other-slot behavior is undefined, not inferred from shared loading.

FILE begins ./ or ../ or is an OS-native absolute path. Bare names, module paths, shell quotes, env expansion, and ~ expansion are unsupported. Internal spaces remain; outer HWS is trimmed.

Split FILE/ENTRY at the last colon after the prefix, retaining other colons such as Windows drive letters. ENTRY is a nonempty simple Python identifier; loading gets the object, not a factory call. Dotted chains/call expressions are not parsed. Custom backends may interpret payload differently.

Resolve relative paths against the DSL directory without changing cwd. Parsing does not test existence/import. Binding loads selected resources and checks slot compatibility; errors do not trigger guessing or fallback. Python imports execute top-level code and must remain outside parsing. M2 caches by canonical absolute path, isolates same-basename files, and cleans failed imports; see [M2](../../development/M2_BUILDING_en.md). This is not a sandbox/permission system.

## 7. Execution and scheduling

No uses means default Prompt; uses transfers all execution ownership. Framework supplies resources/State and awaits results, without assembling an extra default invoke before/after the backend.

Body presence is not a backend-specific syntax error. Backends may use, ignore, or reject it; builtin python does not reject it. User functions need no prompt/model parameters.

Native merging occurs, then valid router, then table routing. Conditional nodes without router still require an explicit key source. Builtin model nodes look up the current reply and return native Command with update/target; they add no State field. External routers use native conditional edges. Do not use shared globals or concurrency-unsafe captured slots to transport route values.

## 8. Default Prompt

Default State is native message State with add_messages. Read all current messages, use static body as current instructions, call model once, and return only new AI message updates. Body is not saved; history is not resubmitted; other fields are not injected automatically.

Empty/description-only body still calls the model. Incompatible model input must fail explicitly. Natural-language requests do not automatically grant search/files/tools, nor add a ReAct loop. Message layout is execution policy, not parser behavior.

## 9. python backend

Resolve and execute a native callable/Runnable without automatic model invocation; user code may call models. Preserve native updates and special returns, not merely text material. Do not require state-only signatures. Actual config/runtime injection, async, and interrupts are subject to compatibility tests.

Body is allowed and may be ignored, without rewriting user arguments. Note-only nodes also execute. A custom backend rejecting body reports its own error.

Router uses merged State. Builtin python has no implicit conditional-key protocol; named conditional tables require router. Dict/string/Command.goto are not guessed as table keys and do not trigger model calls.

## 10. pyfunction backend

### 10.1 Normal sequence

1. Material function receives current State and returns a value, not necessarily full State.
2. Normalize it into material messages.
3. Optional nonempty body becomes SystemMessage, followed by history and material in order; omit empty SystemMessage.
4. Invoke model once.
5. Return only new material/reply messages; native reducer merges them.

This is builtin pyfunction policy, not parser/all-backend behavior. Material is not independently committed or reduced before model invocation. Current call sees history plus new material directly; custom reducer determines subsequent State. Body is not saved; history is not resubmitted. No failure atomicity, retry, or external-side-effect transaction guarantee is implied.

### 10.2 Material conversion

| Value | Handling |
| --- | --- |
| native message | retain role/content/metadata |
| nonempty native-message list | retain order and messages |
| string | HumanMessage |
| ordinary dict/data list | JSON if serializable, otherwise str; HumanMessage |
| other object | str; HumanMessage |
| None/empty list | no material; still invoke |

Empty string remains an empty message. Dict role/content does not imply message recognition or State updates. JSON is message text, not a DSL type or mandatory downstream protocol. Mixed non-message lists are data, without per-item role guessing.

Strings are sufficient for simple material. Native messages are recommended for roles, multimodality, or metadata but not mandatory for beginners. Other native message representations are not implicitly promised. JSON encoding/error details are implementation choices. Disabling material saving is deferred.

## 11. Default text routing

Without router, builtin Prompt/pyfunction conditional nodes require body instructions to output exactly one table key. Trim outer reply whitespace and look it up exactly; do not search prose, strip quotes/fences, require structure, or add a second invocation.

Original AI reply is committed unchanged; trimming only obtains the key. A user reducer's reply transformation must not replace the current-reply decision. Implementation returns Command(update=new messages, goto=target), without duplicate conditional-edge installation. Invalid keys fail.

M3–M5 verified invocation count, sync/async concurrency isolation, reducer-transformed replies, and checkpoint/resume. This policy does not impose a universal result envelope on custom callables; see [report](../../development/M3_M5_COMPLETION_en.md).

With router, model does not independently select a key; router reads merged State and may parse richer answers. No/unconditional table ends or follows its sole edge without guessing answer text.

```markdown
# [Node] Evaluate
Check whether available material is sufficient.
Return only enough if sufficient, otherwise insufficient; no additional text.

## [Transitions]
- enough -> Report
- insufficient -> Ask
```

This is a fragment; full programs are in [examples](../../../examples/README_en.md). The earlier proposal for simultaneous answer/private key was withdrawn.

## 12. Native extension boundaries

Supply native schemas before building, edit Builder after building, and compile yourself. load returns native graph for native APIs. Do not rebuild merging, hide runtime wrappers, swallow interrupts, or lose parameters/async in convenience adapters.

Native goto and DSL edges both apply. Do not cancel declared edges or prohibit table-external jumps by default. Same-target behavior must be tested natively, not silently promised deduplicated. @End ends only its DSL path. Declared conditional tables still require their routing contract.

Schemas can replace fields/reducers and invalidate conveniences; no automatic repair. Message-free code graphs remain valid; model dependencies need explicit checks/adaptation.

Background: [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), [add_messages](https://reference.langchain.com/python/langgraph/graph/message/add_messages), [models](https://docs.langchain.com/oss/python/langchain/models). Unpinned external versions are not automatic compatibility promises.

## 13. Deferred features and implementation choices

Direct output-Schema declarations remain a future direction, perhaps through a special reference analogous to router. No initial keyword/signature/phase is defined, and field names do not automatically infer routing or updates. Output Schema differs from State Schema.

File-level backend selection, module references, disabling material saving, and other language-deferred features remain deferred. M2 established binding/NodeSpec/import lifetimes; CLI and selected native combinations are tested. Wider provider/persistence and exception/retry combinations need actual tests, not a premature plugin protocol.

## Tool execution extension (2026-10-09)

build/load add tools=None: a sequence of BaseTool or Python callables convertible by LangChain tool, not MCP server configuration. Binding registers actual tool names and rejects duplicates, without invoking tools/models. NodeSpec.kind defaults to Node; ToolNode headers set ToolNode.

Host supplies a tool-bound model AND executable tools. Framework neither bind_tools nor reselects models. Prompt/pyfunction invoke the supplied model. Multi-model selection is deferred.

ToolNode becomes native langgraph.prebuilt.ToolNode(selected_tools) through add_node, not backend file loading. Preserve native multiple calls, async, ToolMessage IDs, State/Config/Runtime injection, Command, and error defaults; no manual stringification or pyfunction wrapping. A messages channel is required; body is ignored.

Tables containing @ToolCalls/@Otherwise become native conditional edges reading merged State. Their builtin model nodes return updates only, avoiding an additional text-routing Command/double jump. Router native signature injection remains; matched tool signals bypass router.

Host owns MCP connections, async sessions, and disposal. Compatible BaseTool objects use the same graph; this does not certify every adapter/lifecycle. This extension round did not test MCP. Sync/async depends on tool capabilities.

The complete offline example is examples/10-tool-calling/workflow_en.md and its Host. Scripted model emits real tool_calls; real add executes without network/keys. Real model uses base_model.bind_tools([add]) and tools=[add]. Basic Host adds no tool-loader CLI; custom Host uses @host.

## Basic Host connection extension (2026-10-09)

Environment-based options are in [usage](../../development/USAGE_en.md). host_config is pure configuration: explicit key files, no environment mutation, no Config/Node additions. Native integrations still read provider-standard variables. Factory owns all configuration and takes precedence. Optional DeepSeek integration is provided; OpenCode configuration/credential-store inheritance is not.

## One-shot Host and MCP verification (2026-10-09)

Basic Host now reads once and exits. MCP needs no new syntax/runtime: example Host uses langchain.mcp.MCPAdapter, keeps sessions alive until graph.ainvoke completes, then closes stdio child processes. Integration is optional and beta. Local MCP + DeepSeek is tested; remote HTTP is outside the claim. See [MCP report](../../development/MCP_ACCEPTANCE_en.md).

## Dynamic interrupts and terminal editing (2026-10-09)

No syntax change. Host main compiles with InMemorySaver; run_chat generates a fresh thread_id per invocation. Consume native updates interruptions, display values, read strings with prompt-toolkit, map interrupt IDs to replies, and resume with Command until completion/another interrupt. Resume data is not automatically messages; nodes/reducers decide.

Simultaneous interruptions receive separate answers and one combined resume; repeated interruptions repeat the process. EOF cancels with code 1, without partial answers; empty string is valid. CLI handles Ctrl-C as 130. Pipe exhaustion does not auto-resume. Static breaks, typed forms, and cross-process recovery belong to custom Host/native APIs. Reusing run_chat requires a checkpointer.

PromptSession retains process-local editing/history, not persistent history. Injected streams without file descriptors use readline for tests. Node/routing semantics are unchanged. Native interrupt re-execution still applies; authors must manage pre-interrupt side effects. Scope is in [interrupt acceptance](../../development/HOST_INTERRUPT_ACCEPTANCE_en.md).

## Builtin request_input (2026-10-09)

`- **@uses**: request_input:prompt text` uses existing references, not new settings/kinds. Split first colon; later colons/pipes remain text. One physical line, nonempty payload. If it starts with double quote, backend JSON-decodes a string: quotes removed, \n newline, escaped quote decoded. Invalid/unclosed JSON or empty string fails binding. Parser preserves source and does not decode/execute; quotes cannot make multiline settings.

Directly interrupt(prompt string), without a universal envelope. Basic Host collects strings; other Hosts handle native interruption. Resume must be string, including intentional empty string; other types fail rather than stringify. Return one new HumanMessage update for the selected reducer; no history resubmission, model call, prompt persistence, or body use. Body presence is allowed. Builder requires messages; users still choose reducer.

Update completes only after resume; then router/table runs. Ordinary named keys require explicit router; reply is not automatically a key. Sync/async, native checkpointer/thread_id, replay, and registry override remain supported.

Complete example: examples/11-interrupt/workflow_en.md. Long prompts may be one long line; use JSON strings for line breaks:

```markdown
# [Node] AskUser
- **@uses**: request_input:"Please supply:\n1. Output format\n2. Target audience"

## [Transitions]
- @Default -> @End
```

## First-run configuration (2026-10-09)

No DSL change. host_setup owns user configuration and wizard; host_locales selects Chinese/English from locale identifiers; terminal supplies shared PromptSession. Host still creates models, runs graphs, and dispatches arguments. Without explicit CLI/environment model, load one saved OpenAI-compatible profile; absent profile prompts in terminal or fails in pipes. --setup configures and exits.

Support base URL, model ID, Chat Completions/Responses ChatOpenAI modes, key, and static default_headers. Saved model is openai:MODEL_ID; chat extra includes langchain-openai. SGRAPH_HEADERS_JSON validates string-to-string headers without echoing invalid values. Explicit model/factory ignores saved connection; SGRAPH options override a selected profile.

No API probing, provider/subscription login adapters, or OAuth management. Read locale identifiers, never setlocale. Store local JSON with plaintext credentials, POSIX mode 0600, and atomic replacement. Secret input/history are hidden; --check/parsing never configures. Directory/platform scope is in [wizard report](../../development/HOST_SETUP_ACCEPTANCE_en.md).

## OpenCode Go session headers (2026-10-09)

Model creation for the recognized Go base URL adds missing client identity/random session headers. ID is sgraph-harness-agent-<UUID>, reused for the same model. Basic Host creates one model per run, so parallel nodes, tool loops, and resume share it. Factory is untouched; custom Hosts reusing models across conversations manage their own boundary.

Explicit case-insensitive headers win; saved config is unchanged; non-Go URLs get no Go identity. This is connection policy, not State/DSL. See [Go report](../../development/OPENCODE_GO_ACCEPTANCE_en.md).

## Optional monty backend (2026-10-09)

`- **@uses**: monty:./program_en.py` uses existing references. Payload is explicit relative/absolute file path without :ENTRY; final expression is result. Binding reads but does not execute. Runtime passes JSON state, converting Pydantic messages with model_dump(mode="json"). Node returns update dict/None; router returns string; other types fail. Native merge and existing key lookup still apply.

Optional skilledgraph[monty] pins pydantic-monty 1.1.0. No model/body, native API/Config/Runtime objects, Command, host callbacks, mounts, or CPython fallback. Reducers remain schema-defined.

Each fresh Monty execution: source ≤20000 bytes, input ≤1 MiB, heap 32 MiB, execution 1 second, recursion depth 100, total sleep ≤0.1 seconds. Input/return JSON serialization is capped at 1 MiB, preventing unlimited shared-object expansion. Print is captured, not terminal output or update. Errors propagate; full CPython modules/syntax are not implied. Native graphs may schedule the synchronous callable in async threads; no custom scheduler.

Example program:

```python
{"value": state["value"] * 2}
```

Router example:

```python
"ready" if state["value"] > 0 else "missing"
```

The actual [sgraph_agent](../../../sgraph_agent/README_en.md) implements permissions, sessions, and context through its Host/bindings; it does not alter ordinary nodes or basic Host defaults.
