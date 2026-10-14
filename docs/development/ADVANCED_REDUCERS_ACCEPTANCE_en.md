# Advanced reducer and looping-memory acceptance

Date: 2026-10-09. Two runnable examples and 20 offline tests were added; **245 unittest tests passed** at this milestone. DSL syntax, compiler core and the standard Host's default execution remained unchanged.

## Looping ReAct and compaction

[17-react-memory](../../examples/17-react-memory/README_en.md) provides a multi-turn terminal Host, explicit tool loop, checks before invocation/after answering and memory:compact executor.

- InMemorySaver and a fixed thread_id retain State. Each turn submits only new messages and starts at the first node, without reappending history.
- Normal updates use add_messages. memory_reducer additionally accepts complete Python snapshot replacement, comparing IDs and content to reject stale overwrites of additions or edits.
- Nodes call the summarizer; the reducer only handles data. Old complete turns and previous summaries are compacted together. Recent N turns remain complete, including tool-call/result pairs.
- Sync and async execution work. Separate threads have no prior memory; rebuilt graphs sharing a checkpointer can continue the same thread.

This is a session demonstration, not the full pi product. Terminal editing, /exit, Ctrl+D/C and repeated --turn are supported. Interrupt UI, disk persistence and recovery commands are not automatic.

Character budgets are heuristic. A sole huge turn/preserved turns are not deleted. Empty, tool-calling or nonshrinking summaries fail without replacing history. New input submitted before failure remains checkpointed; failure is not whole-turn rollback. Summaries may lose facts, and old checkpoints retain originals. Replacement and append are not commutative concurrent operations. Compaction is serial; snapshots do not lock concurrent invokes. Hosts must serialize thread input.

## Other reducers

[18-reducer-lab](../../examples/18-reducer-lab/README_en.md) uses native parallel branches and a join without a model.

| Case | Verification | Constraint |
| --- | --- | --- |
| Versioned records | Highest version; compatible permutations, associativity and idempotence | One content per key/version; conflicts fail; no full historical audit |
| Event ID deduplication | Repeated events/submissions count once; total 8 | Stable IDs are business logic; differing values fail; no global exactly-once guarantee |
| Completed tasks | Sorted set union independent of order | List append is not set union |
| Overwrite | Single joined node clears buffer | Concurrent same-field resets fail with native InvalidUpdateError |
| Message edits/deletion | ID replacement, RemoveMessage, REMOVE_ALL_MESSAGES, invalid deletion | Native operations do not maintain business tool pairing automatically |

Reducers remain Python Annotated Schema. Hardcode_Execution_Backend executes nodes and is not a reducer registry.

## Tests and live evidence

[test_advanced_reducers_en.py](../../tests/test_advanced_reducers_en.py) covers all data operations, nondoubled multi-turn history, thread isolation, complete and unordered tool results, before/after compaction, repeated summaries, sync/async and rebuilt graphs, snapshot conflicts, orphan/incomplete tool messages, failed summaries, latest-two-turn preservation, huge single turns and both CLIs. Scripted summaries validate data flow, not intelligence.

[Historical raw results](ADVANCED_REDUCERS_LIVE_RESULTS.json): DeepSeek deepseek-chat, temperature=0, timeout=60, max_tokens=1024, max_retries=0, synthetic data only. Three turns supplied a name/Chinese preference/repeated background, requested 17+25, then asked for name/preference. Passed: one compaction, actual calculate result 42, final answer retained Lin and Chinese. **5 calls, 3806 tokens**, no length truncation. This limited sample does not establish universal retention.

```bash
.venv/bin/sgraph examples/17-react-memory/workflow_en.md -- --demo --budget-chars 120
.venv/bin/sgraph examples/18-reducer-lab/workflow_en.md
.venv/bin/python -m unittest tests.test_advanced_reducers_en -v
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=1024
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python tests/live/run_memory_en.py --run --output /tmp/react-memory-results.json
```

Live runs are opt-in and limited to eight requests. See official [memory/deletion/summary](https://docs.langchain.com/oss/python/langgraph/add-memory) and [State/reducers](https://docs.langchain.com/oss/python/langgraph/graph-api). Existing native integration supports these patterns; risks are strategy, merge properties and business constraints, without needing reducer syntax.
