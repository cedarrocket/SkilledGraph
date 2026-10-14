# Five practical agents: implementation and acceptance

Date: 2026-10-09. Examples 12–16 use existing v0.1 DSL/public APIs, with no new keywords/compiler functionality. Each provides workflow, Python, synthetic data, README and offline demo.

| Example | Purpose | DSL | Python/Host |
| --- | --- | --- | --- |
| [12 Evidence](../../examples/12-evidence-assistant/README_en.md) | Retrieve notes with citations | ToolNode, loop, router, repairs | Retrieval registration, citation validation, State |
| [13 CSV](../../examples/13-csv-auditor/README_en.md) | Compute metrics/check reports | python, pyfunction, branches, failure | Decimal, JSON validation, three attempts |
| [14 Email](../../examples/14-email-assistant/README_en.md) | Policy drafts with approval | Classification table, request_input | Checkpointer and local saving; no sending |
| [15 Review](../../examples/15-parallel-code-review/README_en.md) | Three review perspectives | Prompts and report | Native fan-out/join, AST checks |
| [16 Digest](../../examples/16-batch-digest/README_en.md) | Isolated dynamic summaries | Python dispatch/local worker/pyfunction | Command/Send, reducer, isolation/sorting |

Inspired by official [workflow patterns](https://docs.langchain.com/oss/python/langgraph/workflows-agents), [email design](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) and [data agents](https://docs.langchain.com/oss/python/langgraph/sql-agent). Local notes/CSV avoid service/account dependencies.

## Deterministic coverage

**225 full tests passed**, including 15 new test_practical_agents cases and five CLI demos. Coverage includes real retrieval, bounded fake-citation retries/no evidence, exact CSV/malformed data/reports/attempt limits, three email policies/save/deny/resume, barrier-proven three-way concurrency with postjoin reports and isolated same-step inputs, dynamic worker isolation/removal/sorting/sync/async/empty batches. After prompt/demo edits, **94 targeted parser/practical tests passed**. Scripted models validate contracts, not intelligence.

Generic model-loading tests now cover the first eleven introductory examples. Advanced examples require their Hosts to register tools/State/edges/bindings. A prior parallel-interrupt assertion incorrectly assumed reply order; it now matches prompts without runtime changes.

## Live evidence

DeepSeek deepseek:deepseek-chat, temperature=0, timeout=60, max_tokens=1024, max_retries=0. Only provided synthetic data was sent; email approval saved a synthetic draft in a temporary directory. No actual notes/customer CSV/email/user source was read.

Latest flow contracts **5/5 passed**: retrieval/citations, validated CSV, classification/approval/saving, three parallel reviews and joined report, three workers and synthesis. [Consolidated latest results](PRACTICAL_AGENTS_LIVE_RESULTS.json): **13 calls, 4046 tokens**, collected across rounds, not a new all-example execution. Four actual rounds totaled **30 calls, 11785 tokens**:

| Round | Scope | Calls | Tokens | Record |
| --- | --- | ---: | ---: | --- |
| Initial | All five | 13 | 7706 | [INITIAL](PRACTICAL_AGENTS_LIVE_INITIAL_RESULTS.json) |
| Shortened outputs | CSV/review/digest | 9 | 2157 | [FOLLOWUP](PRACTICAL_AGENTS_LIVE_FOLLOWUP_RESULTS.json) |
| Source excerpts | Digest | 4 | 936 | [EVIDENCE](PRACTICAL_AGENTS_LIVE_EVIDENCE_RESULTS.json) |
| Final format | Digest | 4 | 986 | [FINAL_DIGEST](PRACTICAL_AGENTS_LIVE_FINAL_DIGEST_RESULTS.json) |

Intermediate records remain. Initial flow assertions passed, but human review found truncated review/digest output. Subsequent length limits and explicit finish_reason=length rejection corrected this. Follow-up calls ended normally; retained initial evidence/email records lack finish_reason, so the field is not covered for every final sample.

Content errors included recommending deletion before checking duplicate CSV rows, mentioning nonexistent dates, and assigning release/test owners or review/completion dates incorrectly. Prompts now require duplicate verification. Adding 600-character excerpts alone did not prevent misattribution; final output lists actions/sources and directly quotes names/dates. The inspected final error disappeared. These are prompt improvements, not general fact verification. Citation names, format and values do not validate every statement or recommendation. Results are limited samples.

## DSL assessment and reproduction

Serial steps, routing, tools, materials and approval are clear in Markdown; exact calculations/validation stay in Python, without business/JSON-schema syntax. Native channels support joins, Send and reducers, but advanced Hosts require LangGraph knowledge; complex parallelism is not achievable with only a few Markdown lines. No unfrozen semicolon syntax or reducer executor wrapper was added. Tool registration, shared versus isolated inputs, explicit joins/order, retry limits and grounded output remain important; no syntax blocker was found.

```bash
.venv/bin/sgraph examples/12-evidence-assistant/workflow_en.md -- --demo
.venv/bin/sgraph examples/14-email-assistant/workflow_en.md -- --demo --approval no
.venv/bin/sgraph examples/16-batch-digest/workflow_en.md -- --demo
.venv/bin/python -m unittest tests.test_practical_agents_en -v
export SGRAPH_MODEL=deepseek:deepseek-chat
export SGRAPH_API_KEY_FILE="$HOME/sys_prog/deepseek_api.txt"
export SGRAPH_TEMPERATURE=0
export SGRAPH_TIMEOUT=60
export SGRAPH_MAX_TOKENS=1024
export SGRAPH_MAX_RETRIES=0
export LANGSMITH_TRACING=false
.venv/bin/python examples/support/run_practical_live_en.py --run --output /tmp/practical-agents-results.json
```

Repeat --case to select examples; --run is mandatory, maximum eight calls/example. Mixed-purpose tests must not use coding-only plans; the runner rejects known Go endpoints as an advisory boundary, not a complete terms checker. Other models/custom real materials remain untested.
