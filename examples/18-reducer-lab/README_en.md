# Concurrent business reducer laboratory

Run two native parallel branches without a model, testing three custom merges and Overwrite:

```bash
.venv/bin/sgraph examples/18-reducer-lab/workflow_en.md
.venv/bin/python -m unittest tests.test_advanced_reducers_en -v
```

- `records`: merge versioned records by business key, retaining the higher version and rejecting different content at the same version. The final ticket is version=2, resolved.
- `events`: deduplicate stable event IDs. Both branches return e1, which counts once; e1=3 and e2=5 total 8. Reusing an ID with a different value fails. Unlike additive deltas, repeated submission does not double counts. Stable IDs remain the application's responsibility; this is not execution-wide exactly-once behavior.
- `completed`: sorted set union, without duplicates or dependency on branch order.
- Report waits for both branches, snapshots merged results, then uses native `Overwrite({})` to clear the events buffer. The reducer does not reset a total to zero.

The Host configures parallel edges and joins through native build_graph APIs. State loads directly from Python Schema; there is no reducer DSL or Hardcode_Execution_Backend wrapper.

Commutativity, associativity and idempotence assume valid inputs: one content value per business key/version. Conflict checks cover values participating in the current maximum-version comparison, not a complete history of discarded lower-version conflicts. Full conflict audits require a version log and separate validation.

Overwrite bypasses reducers and does not resolve concurrent conflicts. LangGraph rejects two same-step Overwrites of the same field, so a single joined node performs cleanup. Custom reducers do not mutate input containers or read external clocks/services.

Additional tests cover message ID edits, RemoveMessage, removal of all messages, invalid deletion, snapshot conflicts and failed summaries: [acceptance](../../docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md).
