# Multi-turn ReAct, retained history and compaction

An interactive looping Host with an explicit tool-loop agent demonstrates ongoing sessions and context compaction; it does not reproduce the complete pi harness.

```bash
# Scripted offline model: three turns with compaction
.venv/bin/sgraph examples/17-react-memory/workflow_en.md -- --demo --budget-chars 120
# Live interactive model: /exit or Ctrl+D ends the session
.venv/bin/sgraph examples/17-react-memory/workflow_en.md -- --budget-chars 6000
# Three specified turns; requires model configuration
.venv/bin/sgraph examples/17-react-memory/workflow_en.md -- \
  --turn 'My name is Lin. Please answer in English.' \
  --turn 'Use the tool to add 17 and 25.' \
  --turn 'What is my name?'
```

## Graph and Host responsibilities

```text
CheckBefore → [CompactBefore] → Agent ⇄ Tools
                                 ↓ no tool calls
                             CheckAfter → [CompactAfter] → End
Host reads another input and restarts at the first node on the same thread.
```

DSL defines checks, compaction, tools and termination. The Host creates InMemorySaver and a fixed thread_id, submitting only the new HumanMessage each turn. It does not resubmit all history or change the standard chat Host's single-run behavior. Sessions have separate threads by default; Python callers can explicitly share thread_id and checkpointer.

Agent uses a tool-bound model. Compaction uses an unbound model, optionally replaced through `create_graph(..., summarizer=...)`. Local `memory:compact` is a Hardcode_Execution_Backend binding handling that node's summary call and update. State and reducers are native Python, without executor wrapping.

## Compaction and reducer

Normal updates delegate to native add_messages, including ID-based edits and RemoveMessage. Compaction separates turns at actual user messages, preserves the latest `--keep-turns` turns (default 1), summarizes older turns and existing summaries, and submits a private Python compact update containing the complete old snapshot and replacement messages.

memory_reducer replaces history only when the snapshot matches exactly. Added messages or same-ID content changes reject stale replacement. Reducers perform neither model calls nor I/O. Summaries are HumanMessage reference material tagged `memory_summary`, not permanent SystemMessage instructions. Recent Human/AI/tool_calls/ToolMessage sequences remain complete. Pairing is checked before and after compaction; tool results can arrive in different order.

The budget estimates characters, including tool-call representations, not exact tokens. Checks run before and after responses. The only or preserved turns are never cut, so a huge input/tool result can still exceed context. Empty summaries, tool-calling summaries or nonshrinking replacements fail without changing history. No automatic retry, forced truncation or fact-recovery guarantee is provided.

Compaction is serial; snapshot replacement is not a commutative parallel merge. Hosts must serialize input on a thread; this is not a multi-client transaction mechanism. Repeated summaries are lossy. Reliable facts should be stored separately and validated.

InMemorySaver is process-local and retains old checkpoints. Compaction reduces effective model history, not old records or total checkpoint storage, and does not provide cross-process persistence. Database checkpoints, cleanup and interrupt UI belong to custom Hosts.

Offline and live results: [advanced reducer acceptance](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md).
