# Dynamic batch document summaries

Split documents on a standalone `---` line, create one Send task per document, summarize separately, and merge action descriptions and unknowns in document order. The final list does not reassign owners or dates: source excerpts are supplied for human checking. Suitable for meeting notes, daily reports and multi-document summaries.

```bash
.venv/bin/sgraph examples/16-batch-digest/workflow_en.md -- --demo
.venv/bin/sgraph examples/16-batch-digest/workflow_en.md -- --data /path/to/batch.md
cat batch.md | .venv/bin/sgraph examples/16-batch-digest/workflow_en.md
```

Input is document text, not a directory. Workers receive only their own document. Native RemoveMessage removes the original batch so final synthesis does not reread all source text. Each result retains an evidence excerpt of at most 600 characters; this is not complete fact checking. `results` uses native operator.add and is explicitly sorted by index after merging; parallel completion order is not document order.

Dispatch uses `@uses python` and returns `Command(goto=[Send(...)])`. Summarize uses the Host's local `worker:summary` executor, which combines node text and isolated input for synchronous or asynchronous model calls. Report uses pyfunction. worker is a local binding, not a new DSL keyword. Native Python provides dynamic dispatch; transition tables still express single-target edges.

Useful for map-reduce when document count is unknown before execution. Each document must fit model context. Splitting uses delimiters, not a tokenizer. There is no automatic concurrency limit or persistent intermediate storage: custom Hosts should set native max_concurrency or limit batches. Summaries can omit or misunderstand relationships. A live run inferred a release owner as a test owner; output was therefore narrowed to action descriptions and sources, with names and dates shown as direct quotations instead of automatic assignments.
