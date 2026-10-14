# Local knowledge-base answers with citations

Ask questions about local Markdown notes. The model retrieves excerpts and cites sources; Python validates citation names. Answers should acknowledge missing evidence. Failed validation allows at most three correction rounds.

```bash
.venv/bin/sgraph examples/12-evidence-assistant/workflow_en.md -- --demo
printf 'What must happen before release, and when should we roll back?' | .venv/bin/sgraph examples/12-evidence-assistant/workflow_en.md
.venv/bin/sgraph examples/12-evidence-assistant/workflow_en.md -- --data /path/to/notes --input 'Your question'
```

Live mode uses environment variables or the standard Host's saved connection; the model must support tool calling. Search reads only top-level `.md` files in the selected directory, skips symbolic links, and returns at most four keyword-matched excerpts of at most 4000 characters each. Default materials are synthetic release policies. Matched user-selected notes are sent to the model.

Flow: Research → (ToolCalls) SearchNotes → Research → Verify → finish / correction / unverified notice. DSL declares every edge. State adds `attempts` and `validation`; messages use the native reducer.

Useful for policies, project notes and personal knowledge bases. Keyword search lacks semantic retrieval. Validation proves only that a cited name occurred in search results, not that every claim is supported. Treating retrieved text as reference material is not comprehensive prompt-injection protection.
