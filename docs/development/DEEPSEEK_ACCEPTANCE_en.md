# Live DeepSeek environment acceptance

Date: 2026-10-09. Host environment settings implemented; final live **15/15 passed**, offline **170 tests passed**. MCP was not tested this round.

## Scope

Standard Host supports SGRAPH_API_KEY/API_KEY_FILE/BASE_URL/TEMPERATURE/TIMEOUT/MAX_TOKENS/MAX_RETRIES through LangChain init_chat_model. Provider-standard environment credentials remain valid. Keys are read only by Host, never placed in State/DSL/logs/reports or system environment. Factories manage their own configuration. No automatic OpenCode/auth.json loading or new DSL attributes. Tool Hosts explicitly bind tools and pass actual objects to load_graph.

Pinned integrations: langchain-deepseek 1.1.1, langchain-openai 1.7.0, langgraph 1.2.14, langchain-core 1.6.9, langchain 1.4.4; deepseek extra added. References: [integration](https://docs.langchain.com/oss/python/integrations/chat/deepseek), [tool calling](https://api-docs.deepseek.com/guides/tool_calls/). Provider configuration stays outside DSL.

## Final results

Requested deepseek:deepseek-chat; observed actual model_name deepseek-flash for every record, without promising future alias mapping. temperature=0, timeout=45, max_tokens=256, max_retries=0, tool recursion_limit=12.

| Case | Result | Requests | Seconds |
| --- | --- | ---: | ---: |
| Exact ordinary reply | Pass | 1 | 0.647 |
| Two-node history/actual input | Pass | 2 | 2.092 |
| List yes | Pass | 2 | 2.404 |
| List no | Pass | 2 | 2.048 |
| Table yes | Pass | 2 | 2.245 |
| Table no | Pass | 2 | 1.835 |
| Function material/save | Pass | 1 | 0.867 |
| Sync single tool | Pass | 2 | 2.003 |
| Two calls in one batch | Pass | 2 | 2.400 |
| Dependent two-round tools | Pass | 3 | 3.022 |
| Async tool loop | Pass | 2 | 2.303 |
| Argument validation/recovery | Pass | 3 | 4.293 |
| Business exception propagation | Pass | 1 | 1.188 |
| Piped standard Host | Pass | 1 | 1.366 |
| Standalone CLI configuration | Pass | 1 child | 2.809 |

26 in-process calls plus one CLI child. In-process usage: **5292 input, 608 output, 5900 total tokens**; child tokens uncollected/excluded. Times are end-to-end per case, not per-request latency or a benchmark.

[Raw results](DEEPSEEK_LIVE_RESULTS.json) contain synthetic input/output/calls/IDs/timing/usage. Checks enforce matching ToolMessage IDs, all results before the next AI response and a final answer without tool_calls. Single addition returned 42; add/multiply shared one batch with two results; dependent lookup returned 37 then add 5; async passed. Validation errors returned status=error and corrected arguments; business ValueError propagated.

## Earlier failures

[Initial round](DEEPSEEK_LIVE_INITIAL.json): **12/14**. The model rewrote SG_HISTORY_731 into SG_HISTORY_<answer>731</answer> instead of exact reproduction. A business ValueError propagated although the test expected automatic recovery.

[First retest](DEEPSEEK_LIVE_FOLLOWUP.json) still rewrote SG_HISTORY_SENTINEL and claimed not to receive prior output. Model statements are not evidence of actual message transmission. [History retest](DEEPSEEK_LIVE_HISTORY.json) used the natural-language animal blue whale and recorded actual second-call input, proving system/original human/prior AIMessage were present; the response correctly referred to the animal. Final full tests passed. No reply-cleaning or reducer changes hid the error; exact offline history tests still passed.

Error tests now distinguish recoverable parameter validation from default-propagating business errors. Live/offline regressions passed without altering ToolNode error policy. Special-marker compliance remains an observed model risk: temperature=0 does not ensure exact output, and invalid route diagnostics remain necessary. One controlled 15/15 does not establish arbitrary-task reliability.

## Boundaries and reproduction

170 offline tests passed. Parser-only base environment discovered 118, skipped 27, executed 91. Syntax compilation/live demo DSL checks passed. The current .venv inherited system-site-packages; pip check reported preexisting missing/conflicting packages such as cffi, stubs and google-auth/cachetools. These were not fixed or described as a clean environment; no new LangChain/DeepSeek conflicts were reported. Clean/cross-platform acceptance was still needed.

Across probes/retests/final runs/two CLI children, **60 known requests**, **12321 collected tokens**, excluding CLI usage. No cost estimate. No MCP, actual file tools/external writes, all providers, multimodel selection, long context or persistence was tested. All task material was synthetic.

See [instructions](../../tests/live/README_en.md), [runner](../../tests/live/run_deepseek_en.py), [Host](../../tests/live/demo/host_en.py) and [graph](../../tests/live/demo/workflow_en.md). Key-file paths keep secrets out of source. English scripts have translated prompts; historical JSON remains unmodified and does not constitute a new English live run.
