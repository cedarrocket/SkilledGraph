# sgraph_agent implementation and acceptance

Date: 2026-10-09. [sgraph_agent](../../sgraph_agent/README_en.md) is independent of demonstration models, uses actual APIs and provides ongoing sessions, tools, explicit permissions and node-driven compaction.

## Responsibilities

Existing DSL defines CheckContext/CompactContext/Agent/PermissionGate/ExecuteTools/CheckAfter/CompactAfter and transitions, without new node types/settings/routes/reducer syntax. The Host supplies model/workspace/InMemorySaver. Local bindings handle model, compaction, approval and execution. Native Annotated messages reducer applies complete snapshots; it has no model requests and is not wrapped/registered by Hardcode_Execution_Backend.

Permission calls native interrupt in a preceding node; Host recognizes kind=tool_permission, displays parameters and collects bool. Every Bash/write/edit needs exact approval. Restricted read/search/list validate paths; Monty has no callbacks. ExecuteTools invokes native ToolNode in request order, rechecks paths/fingerprints and returns paired results even for denial.

Optional built-in monty:FILE returns JSON State updates for nodes and route strings for routers. Only executor registration/implementation changed; parsing/scheduling remained unchanged. agent/monty are optional extras. Packaging supplies sgraph-agent and workflow.

## Offline coverage

At this milestone **272 full tests passed**, including **27 agent tests**. Subsequent terminal escaping, call IDs, search filtering, edit permissions, Bash codes, summary bounds, bounded JSON and empty tools changes passed the same 27-test regression.

Coverage includes actual filesystem/Monty and multi-call pairing; denied versus approved side effects and mixed batches; nonterminal denial, strict bool approval and repeated interrupts; private/escaping/symlink/hardlink/device/oversized paths; fingerprints/revalidation; unknown tools/extra parameters/empty IDs/budgets; sessions/compaction/isolation/unfinished checkpoints; Monty denied files/environment/process/network, CPU/memory/source/print/JSON bounds and actual node/message/router integration; escaped terminal/bidi controls; Bash timeout/output/process groups/exit codes/clean environment; real ChatOpenAI HTTP MockTransport serialization of calls/results/encrypted reasoning/store=False/no previous_response_id; DeepSeek stateless plaintext reasoning; offline --help.

Tests use temporary directories, never network. Full coverage requires agent extra; absent optional dependencies skip the module.

## Live Responses evidence

DeepSeek deepseek-flash at https://api.deepseek.com used the authorized key without recording credentials. Inputs/files/commands were synthetic in isolated directories.

[Four-case results](SGRAPH_AGENT_LIVE_RESULTS.json): reasoning_effort=none, timeout=60, max_output_tokens=2048, max_retries=0; **4/4 passed, 14 requests, 18776 tokens**.

| Case | Check |
| --- | --- |
| read_monty | Actual read_file; Monty sum(range(10))=45 |
| deny_bash | Permission triggered; denied-marker absent |
| approve_write_bash | Only exact approved.txt/approved and printf shell-ok approved; effects/results checked |
| memory | Three turns, two compactions, actual Python 42, retained Lin/Chinese preference |

LangChain 1.7.0 omitted reasoning without encrypted_content under store=False. Local AgentChatOpenAI now preserves DeepSeek plaintext content, removes server IDs and retains stateless settings. It depends on pinned private serializers and must be checked on upgrade.

[Thinking follow-up](SGRAPH_AGENT_THINKING_RESULTS.json): reasoning_effort=low, max_output_tokens=4096; read_monty passed with **2 requests, 2326 tokens** after adaptation. The initial four cases occurred before it; they are separate rounds.

Final summarization uses visible dialogue/tool records and rejects overbudget old history. [Final memory retest](SGRAPH_AGENT_MEMORY_FINAL_RESULTS.json) passed with one compaction, retained name/preference and actual calculation: **5 requests, 8387 tokens**. Monitored rounds totaled **21 requests, 29489 tokens**.

Installed CLI from /tmp also returned sum(range(100))=4950 with real Responses/Monty, **exit 0, two Agent calls**: [CLI record](SGRAPH_AGENT_CLI_RESULTS.json). Its unmonitored tokens are excluded from 29489.

These limited scenarios verify real execution/gates, not all instructions/models/platforms/threats. OpenAI used HTTP mocks, without a live OpenAI key. DeepSeek was live; Monty was actual local execution.

## Packaging/reproduction

Editable agent install/help/outside-project execution passed. Wheel contained workflow and skilledgraph/monty_execution.py without keys/reports or example runtime dependencies.

```bash
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=2048
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python tests/live/run_sgraph_agent_en.py --run --output /tmp/sgraph-agent-results.json
```

Explicit --run, at most eight calls/case, repeatable --case. Thinking needs --reasoning-effort low and sufficient output. The test preapproves only exact harmless synthetic operations, without a production global-approval option.

## Limits

Bash approval is not OS isolation. File filtering cannot identify every secret or provide transactional concurrent edits. Monty supports a subset, without arbitrary CPython libraries/fallback. Compaction is lossy/heuristic, old checkpoints remain, and no disk recovery/deletion protocol exists. State/effects are not whole-turn transactions/exactly-once; inspect effects after failure. This POSIX agent lacks automatic MCP/skills/plugins, streaming UI, background tasks and multiuser deployment. The standard Host remains single-run.

References: [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [DeepSeek Responses](https://api-docs.deepseek.com/guides/responses_api/), [Monty](https://github.com/pydantic/monty/blob/main/crates/monty-python/README.md). Raw records are original historical evidence; translation does not imply English live reruns.
