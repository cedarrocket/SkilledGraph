# LM Studio short-context briefing test agent

A small SkilledGraph agent tests whether the currently loaded local model understands CORE.md and generates a runnable graph with supporting Python. It is neither a chat application nor a general benchmark.

The briefing is local, excluded from Git. Default: docs/agent-guide/CORE.md. Other machines must provide `--core-file /path/to/CORE.md`. Missing files fail before connection.

## Run

Start LM Studio's local server and load a model. Default endpoint: http://127.0.0.1:1234; expected loaded context: 8192. Only already-loaded LLMs are selected. Multiple models require `--model`; nothing is guessed or loaded automatically.

```bash
.venv/bin/python tests/live/run_lmstudio_briefing_en.py --run \
  --output .local-docs/lmstudio-briefing-new-run
python -m skilledgraph tests/lmstudio_briefing/workflow_en.md -- --run \
  --model underdog-saluki-27b-1.0 --output .local-docs/lmstudio-briefing-new-run
```

Windows: use `.venv\Scripts\python.exe`. The output directory must be new or empty. `--help` makes no requests; `--run` enables real local inference. `--repairs 0` disables feedback repair. Default maximum: three requests (quiz, initial files, one repair). Every request receives the entire CORE independently, without accumulated history, RECIPES or EXTENSIONS.

`--transport json` requests JSON containing two file strings. `--transport files` requests two `### filename` headings and complete fences to reduce escaping. `--generation-only` skips the quiz for a separately recorded format comparison; passing this mode does not mean passing all ten quiz questions.

## Flow and validation

ReadCore → Probe → Generate → Validate; finish or retry once.

- Probe: ten multiple-choice language questions scored against fixed answers; malformed output is not manually repaired.
- Generate: workflow_en.md and actions_en.py with State, Python inspect/router, pyfunction Report, missing-material Ask and explicit End.
- Validate: Python syntax, restrictive AST checks, DSL static checks and native execution. Nonempty/empty numbers check routing, invocation counts, saved material and retained history.
- Execution uses an offline model double; the author model generates files. This tests rule understanding/code generation, not arithmetic or tool intelligence.
- Initial and repaired results are reported separately; generated files are not manually edited.

Two fixed filenames and fresh directories are used. File/network/subprocess imports and unnecessary constructions are prohibited. AST allowlists and subprocess timeouts are not a general Python sandbox; never use this validator for arbitrary generated code.

## API and budget

Uses [LM Studio native /api/v1/chat](https://lmstudio.ai/docs/developer/rest/chat) with explicit context_length, reasoning=off, temperature=0 and store=false. Native usage includes input_tokens and total_output_tokens. No forced JSON grammar decoding is applied.

Quiz output limit: 450 tokens; generation default: 1800. Hitting limits is recorded as possible truncation. Input plus reserved output must fit the loaded context. No model-load configuration changes, cloud models or keys are used. Only local HTTP endpoints are accepted; environment proxies are disabled.

Outputs include discovered models, CORE snapshot, all requests/raw responses, generated files, validation stdout/stderr and report.json, normally in ignored .local-docs. The CORE hash can be compared to docs/agent-guide/manifest.json.

A pass applies only to that model, quantization, context and task. Multiple-choice guesses and narrow generation tasks do not demonstrate full language capability or reliable arbitrary workflow generation.
