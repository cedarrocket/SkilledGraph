# Reusable subgraph and execution trace

`workflow_en.md` mounts the same `review_en.md` twice, as InitialReview and FinalReview. Each file uses its own default MessagesState. Shared messages carry the drafts and reviews; no schema override or Host is declared in the child.

Offline demo (scripted responses, no API or quality claim):

```bash
printf 'Explain how to check a mathematical claim.\n' | .venv/bin/sgraph examples/19-subgraphs/workflow_en.md -- --model-factory python:./model_en.py:create
```

For a real configured model, omit `--model-factory` and its argument. The standard chat Host prints nested replies once, with labels such as `InitialReview / Examine`. Trace metadata goes to stderr; the model does not automatically receive it. Child @End returns to the parent. The child file can also run independently with the same command pattern.

A custom Host can supply `TraceRecorder` to load_graph and explicitly save JSONL or include render() in the next planning round. Rebuild after changing graph files; an active compiled graph is fixed. Arbitrary additive reducers can re-add child input at the return boundary; use native Python adapters when transformations are needed.
