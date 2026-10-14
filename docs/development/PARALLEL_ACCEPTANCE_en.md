# Native Parallelism and Fan-out Acceptance

Date: 2026-10-09. No new DSL parallel syntax. Static fan-out is configured through build_graph and native edges; dynamic dispatch through Python Command/Send. Parallel field updates need native reducers; missing reducers are not repaired.

Join follows actual topology: separate incoming edges are not universally an all-branch barrier. The example uses add_edge(["Left", "RightLast"], "Join") to wait for unequal-length branches once.

## Verification

191/191 unittest passed. Four tests cover threading.Barrier(2) real synchronous overlap, asyncio.Barrier(2) async overlap, three Send inputs to one Worker with merged results, and native InvalidUpdateError on unreduced concurrent writes.

The [CLI example](../../tests/parallel_demo/workflow_en.md) exits normally. Observed Left/Right start around0.001s and finish0.301s; RightLast finishes0.401s; Join runs around0.402s; overlap=True. These are observations, not performance guarantees.

No model API, Prompt changes, or Host semantic changes. Background: [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api).
