# LM Studio / 8k briefing acceptance

Date: 2026-10-13. [Test agent](../../tests/lmstudio_briefing/README_en.md). Baseline ba49197; CORE SHA256: d865afc47fab3c6171f88c6f5b9e8660f1858ed524e1e4e11989a282f032bcce.

## Environment and method

Authorized local endpoint: http://127.0.0.1:1234. The only loaded LLM was underdog-saluki-27b-1.0 (ConwayResearch, 27B, IQ2, architecture=qwen35), context_length=8192. Tests used the loaded instance rather than guessing a model from its informal description.

/api/v1/chat used temperature=0, reasoning=off, store=false. Every request received complete CORE as system input, without RECIPES/EXTENSIONS, constrained JSON decoding or manual edits. Quiz limit: 450 output tokens; generation: 1800. A separate subprocess with a fixed offline model validated files; the tested model did not grade itself.

## Quiz and JSON delivery

**8/10 correct.** q1 incorrectly claimed @uses python invokes the model automatically when body text exists; q8 incorrectly allowed @state without explicit Config. Initial file JSON lacked a closing brace, so extraction failed. Feedback repair also omitted it. Neither was manually repaired. This group failed first on delivery format; invalid JSON does not itself prove a DSL runtime error.

| Request | Input tokens | Output tokens | Seconds |
| --- | ---: | ---: | ---: |
| Quiz | 3372 | 55 | 59.27 |
| Initial files | 3379 | 258 | 62.13 |
| Repair | 3417 | 348 | 84.18 |

## Complete fenced files

Same CORE, task, model and inference settings, but two named file fences instead of nested JSON. This group skipped the quiz and cannot be reported as quiz success.

**First generation passed without repair.** Original workflow.md/actions.py passed syntax, restrictive AST checks, DSL parsing, native building and both branches:

| Input | Route/result | Model calls | Messages |
| --- | --- | ---: | ---: |
| numbers=[1,2,3] | ready → Report → sum:6 | 1 | 3: input, material, answer |
| numbers=[] | missing → Ask → request material | 1 | 2: input, answer |

Inspect did not invoke a model; router read merged status; pyfunction saved material. Some rules missed in the quiz were used correctly in code, so these measurements are not interchangeable.

3395 input tokens, 281 output tokens, 73.46 seconds, approximately 4.47 tokens/s. No output limit was hit; input plus 1800 reserved tokens fit 8192 without trimming CORE. Four valid requests totaled **13563 input and 942 output tokens**. Another format comparison was cancelled because the harness still contained a JSON-only system constraint; request and ABORTED marker remain, excluded from success/failure and without full usage. Correcting that constraint produced the valid second group.

## Records and reproduction

Ignored local directories preserve all requests and responses:

- .local-docs/lmstudio-briefing-8k-20261013: first group and report.json.
- .local-docs/lmstudio-briefing-8k-files-20261013: cancelled invalid comparison and ABORTED.json.
- .local-docs/lmstudio-briefing-8k-files-control-20261013: valid group, report, original generated files in attempt-1 and independent validation.

```bash
.venv/bin/python tests/live/run_lmstudio_briefing_en.py --run \
  --transport files --output .local-docs/lmstudio-briefing-next
```

Default allows one repair; --repairs 0 tests first generation only, --transport json selects JSON, and --generation-only skips the quiz.

## Scope

Complete CORE fits this configured 8k instance with under 3.5k input tokens and output headroom. It generated a runnable State/routing/material graph, but did not demonstrate complete rule mastery. Fenced delivery plus programmatic checks/feedback is preferable for this case.

No independent reasoning, tools/MCP generation, parallelism, complex reducers, cross-platform generation or randomized task set was tested. Context, model and CORE were unchanged. One success does not establish reliability for arbitrary 8k models/tasks. AST allowlist and timeout apply to this narrow task, not arbitrary code. Offline checks validate framework behavior, not answer quality. Added scripts passed syntax/CLI, a valid reference and wrong-route/dangerous-import checks; framework code was unchanged and its full suite was not rerun at this historical milestone.
