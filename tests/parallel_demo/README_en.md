# Native parallel example

Run from the repository root; no model or key is needed:

```bash
.venv/bin/sgraph tests/parallel_demo/workflow_en.md
```

DSL provides nodes and native State. The Host obtains the native Builder through build_graph(), adds edges and compiles. No DSL parallel syntax is added.

```text
             ┌─ Left ──────────────┐
Start ───────┤                     ├─ Join ─ End
             └─ Right ─ RightLast ─┘
```

Left and Right each wait about 0.3 seconds in the same parallel super-step. RightLast waits another 0.1 seconds. `add_edge(["Left", "RightLast"], "Join")` waits for both paths. Join executes once and sees events merged by operator.add.

Output shows start/end times, overlap and results. Timing is illustrative; automated tests prove concurrency with barriers, independently of machine speed. Update order is not completion order.

Some transitions are intentionally omitted for native Host edges. Beginner DSL graphs should explicitly declare transitions and endings. test_parallel_en.py also tests asynchronous execution, native Command/Send dispatch and native errors when concurrent writes lack a reducer.
