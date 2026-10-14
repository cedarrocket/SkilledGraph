# Live DeepSeek acceptance

These scripts are excluded from default offline unittest execution. Explicit `--run` enables live API calls. Tools use synthetic data, do not read user files and do not test MCP.

```bash
python -m pip install -e '.[deepseek]'
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=45
export SGRAPH_MAX_TOKENS=256
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python tests/live/run_deepseek_en.py --run
```

DEEPSEEK_API_KEY is the standard provider variable. A single-line key file avoids putting credentials into shell history. Keys are sent only to the configured authentication endpoint. Do not enable request-header debugging. Reports contain synthetic inputs, replies, parameters, usage, timing and errors, never keys.

Repeat `--case` to select cases; `--output` sets the report location. Default: docs/development/DEEPSEEK_LIVE_RESULTS.json. Returned model_name may differ from the requested alias. CLI child calls are excluded from in-process token totals.

```bash
.venv/bin/sgraph examples/01-assistant/workflow_en.md
printf 'Use the tool to add 17 and 25.\n' | .venv/bin/sgraph tests/live/demo/workflow_en.md
```

The demo Host binds actual tools and passes them to load_graph; DSL determines nodes and edges. run_chat shows AI responses, possibly empty lines for textless calls, but does not print ToolMessage. The acceptance script directly checks ToolMessages and call IDs.

Fifteen cases cover ordinary replies, two-node history, both list/table routing branches, pyfunction material, single/multiple/dependent multi-round tools, asynchronous calls, argument-error recovery, business exceptions, piped Host and standalone CLI. Exact assertions are controlled tests, not a guarantee of model compliance.

## OpenCode Go

```bash
.venv/bin/python tests/live/run_opencode_go_en.py --run
```

Reads existing ~/.local/share/opencode/auth.json, or `--auth-file`. Sends at most two synthetic coding cases with its own User-Agent and a session-stable x-opencode-session. Requires quota, writes no user configuration, and defaults to docs/development/OPENCODE_GO_LIVE_RESULTS.json. See [acceptance](../../docs/development/OPENCODE_GO_ACCEPTANCE_en.md).

## Practical agents, memory and terminal agent

`examples/support/run_practical_live_en.py --run` tests examples 12–16 with synthetic data and an eight-call limit per example. [Practical acceptance](../../docs/development/PRACTICAL_AGENTS_ACCEPTANCE_en.md) explains configuration/results. Offline tests: tests/test_practical_agents_en.py.

`tests/live/run_memory_en.py --run` tests synthetic names/preferences, retained history, compaction and actual tool loops, with at most eight calls. See [reducer acceptance](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md).

`tests/live/run_sgraph_agent_en.py --run` uses an isolated temporary workspace for live DeepSeek Responses tests: reading/Monty, denied Bash, exact approved synthetic writes/commands and post-compaction memory. Supports `--case` and `--reasoning-effort`; see [agent acceptance](../../docs/development/SGRAPH_AGENT_ACCEPTANCE_en.md).

Historical raw response JSON is shared and unmodified. Translated scripts require new explicit live runs to validate English prompts; historical reports do not imply those runs occurred.
