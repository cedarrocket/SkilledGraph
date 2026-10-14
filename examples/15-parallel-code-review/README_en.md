# Parallel code review from three perspectives

Review correctness, security and maintainability concurrently; after all branches finish, combine their findings and AST checks into a prioritized report. Source is analyzed as text and AST and is never executed.

```bash
.venv/bin/sgraph examples/15-parallel-code-review/workflow_en.md -- --demo
.venv/bin/sgraph examples/15-parallel-code-review/workflow_en.md -- --data /path/to/code.py
cat code.py | .venv/bin/sgraph examples/15-parallel-code-review/workflow_en.md
```

The default sample includes division by zero on an empty list and an untrusted shell command. Live mode sends the selected source to the model; choose files according to your data-sharing requirements.

```text
         ┌─ Correctness ─────┐
Start ───┼─ Security ────────┼─ Report ─ End
         └─ Maintainability ─┘
```

DSL defines instructions and Report termination. The Host adds multiple outgoing edges through build_graph() and waits using `add_edge(branches, "Report")`. No unimplemented semicolon syntax is used. Branch nodes intentionally omit transition tables for native Builder integration. The default message reducer merges three reports. Each reviewer sees the same initial input, without other branches' same-step outputs.

Useful for supplementary pre-commit review. Models may miss issues or report false positives, and AST call names do not prove vulnerabilities. This does not replace tests or professional review. The scripted demo verifies flow; live quality depends on the model.
