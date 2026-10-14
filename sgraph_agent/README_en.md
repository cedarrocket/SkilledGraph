# sgraph_agent: a usable terminal ReAct agent

An independent personal terminal assistant orchestrated by SkilledGraph DSL with actual models/tools, without scripted replies. It provides ongoing conversation, tool execution, permissions and compaction in a pi-like workflow, rather than reproducing the entire product.

## Install and start

```bash
python -m pip install -e '.[agent]'
.venv/bin/sgraph-agent-en \
  --model deepseek-flash \
  --base-url https://api.deepseek.com \
  --key-file "$HOME/sys_prog/deepseek_api.txt" \
  --reasoning-effort none \
  --workspace /path/to/your/project
```

Set workspace to your project. Try reading project documentation, searching TODOs, computing with Python or editing and validating a file. Reads/computation run automatically; every write/edit/Bash call asks permission.

Alternatively use `python -m sgraph_agent.host_en` or `sgraph sgraph_agent/workflow_en.md -- ...`. Without an explicit model, saved standard Host connection settings apply. Explicit --model/SGRAPH_MODEL uses arguments/environment without mixing saved credentials. --base-url/--key-file override. Missing configuration invokes the existing wizard. --api defaults to responses, also accepts chat; saved API mode does not override this choice. Supply your own IDs/endpoints/keys for compatible providers; credentials never enter DSL.

Observed DeepSeek Responses model IDs were deepseek-flash/deepseek-v4-pro. Existing deepseek-chat configuration is not silently replaced or downgraded to Chat. See [historical acceptance](../docs/development/SGRAPH_AGENT_ACCEPTANCE_en.md).

```bash
.venv/bin/sgraph-agent-en --model deepseek-flash --base-url https://api.deepseek.com \
  --key-file "$HOME/sys_prog/deepseek_api.txt" --reasoning-effort none \
  --workspace . --prompt 'Read README_en.md, then calculate sum(range(100)) using Python'
```

Nonterminal mode allows restricted reads/Python but denies every permission-requiring call. Piped text is not interpreted as approval. There is no --yes/unlimited default authorization.

## Sessions and graph

/exit exits; /clear starts a session; /status shows thread/message/compaction counts. The prompt-toolkit terminal edits input. Process-local InMemorySaver retains each session; turns submit only new HumanMessage and restart at the first node on the same thread. No disk persistence/cross-process recovery.

[workflow_en.md](workflow_en.md):

```text
CheckContext → [CompactContext] → Agent
                                   │ tool calls
                              PermissionGate → ExecuteTools → CheckContext
                                   │ no tool calls
                              CheckAfter → [CompactAfter] → End
Host reads another message on the same thread.
```

ExecuteTools is a local executor using native ToolNode. It runs only approved calls with matching fingerprints, serially in request order. Denied calls still return paired ToolMessages; original AI tool_calls remain. Denying one call does not lose another result. Permission runs in a separate preceding node, without executing tools before replayed interrupts.

## Tools and permissions

| Tool | Function | Default policy |
| --- | --- | --- |
| read_file | UTF-8 numbered/ranged reads | Workspace-only; file ≤1 MiB; output ≤12000 characters |
| list_files | List files/directories | Automatic; scan ≤2000 entries/directory; return ≤500 |
| search_files | Literal substring search | Automatic; ≤500 traversed entries, depth <8, ≤50 matches; skips dependency/cache/build directories |
| python | Monty subset with optional data dict | Automatic; no mounts, network or callbacks |
| write_file | Create/replace UTF-8 | Approval every time; parent must exist |
| edit_file | Replace unique exact old_text | Approval every time; no fuzzy patches |
| bash | Normal-user Bash | Approval for every command |

Payloads include workspace, tool, complete arguments, call ID and reason. The Host accepts explicit affirmation only; empty/negative replies deny. Approval binds the exact call, not a turn/session, and cannot survive changed arguments/path conditions.

File tools use POSIX dir-fd/O_NOFOLLOW/regular-file checks; reject escapes, symlinks, hard links and devices; hide common private paths such as .git/.aws/.ssh/.codex/.agents/.env*, auth.json, credentials, deepseek_api.txt, *.key and *.pem. List/search apply the same filtering. This cannot detect secrets in arbitrary normal files. Workspace/content selection is the user's responsibility. External concurrent edits can race; this is not a collaborative transaction system.

**Bash is not an OS sandbox.** Approved commands have the running user's file/network/process permissions, including outside workspace (which is only cwd). Bash does not inherit API-key environment variables, starts without profiles and closes stdin. Default timeout is 10 seconds, maximum 30; output limit is 16000 bytes. Timeout/overflow kills the process group. This is not comprehensive memory/disk/side-effect isolation and cannot guarantee killing descendants that leave the group.

## Monty

Pinned pydantic-monty 1.1.0 creates a fresh execution per call. Only JSON data is passed: no host objects, mounts, callbacks or CPython fallback. Limits: code 20000 UTF-8 bytes, input 1 MiB, bounded host JSON serialization (including shared-object expansion), heap 32 MiB, execution 1 second, recursion 100. print is captured with a limit. Supported syntax/modules are the Monty subset; arbitrary CPython imports/pip installation are unavailable.

Optional built-in Hardcode_Execution_Backend `@uses monty:./program.py` exposes JSON state and uses the final expression as a State-update dictionary; routers return strings. It calls no model and handles neither reducers nor native Command. See the [whitepaper](../docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md).

## Context and execution boundaries

--context-budget defaults to 12000, using history JSON characters/2 as a heuristic, including tool arguments/reasoning blocks but excluding system/tool schemas. Reserve space for those and output. At 70%, old complete turns may be compacted while retaining --keep-turns (default 1). Dedicated compaction nodes summarize visible dialogue/tool records, excluding encrypted reasoning as evidence, then apply a native Python reducer snapshot replacement. Reducers do not call models or manage executors.

Overbudget old history, empty/tool-calling/incomplete/nonshrinking summaries stop without replacement. When only retained turns remain overbudget, execution stops before model invocation instead of splitting tools; shorten input, increase budget or /clear. Summaries are lossy. Old checkpoints retain originals.

Responses uses store=False and no previous_response_id; client State defines effective history. OpenAI encrypted reasoning round-trips are supported. DeepSeek plaintext reasoning adapts stateless serialization in responses_en.py using private langchain-openai 1.7.0 APIs; dependency upgrades require retesting. Other compatible endpoints/models have not been live-validated.

Default limits: 16 Agent calls/turn, 8 calls/tool batch, and a finite graph recursion limit. Summarizer calls are counted separately. Failures do not imply whole-turn rollback; approved side effects may already exist. Crash recovery provides no exactly-once effects. Unfinished checkpoints cannot be overwritten by a new turn; inspect effects and /clear.

No streaming-token UI, automatic MCP/skills loading, remote search, background tasks or multiprocess persistence is provided.

## Modules and verification

- workflow_en.md: flow/prompts; graph_en.py: model/compaction bindings.
- memory_en.py: Schema/checks/snapshot reducer; policy_en.py: approval/filtering.
- tools_en.py/filesystem_en.py/shell_en.py: tools/local limits.
- connection_en.py/responses_en.py: API compatibility; host_en.py: terminal sessions.

See [acceptance](../docs/development/SGRAPH_AGENT_ACCEPTANCE_en.md) for tests, live observations and limitations. Chinese affirmative aliases remain supported in English mode. Shared package __main__ remains the original compatibility entry; use the explicit English entry above.
