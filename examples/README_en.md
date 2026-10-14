# v0.1 examples

The independent [standard chat Host](chat-host/README_en.md) supplies models, input, setup and interrupt resumption outside the DSL core. Eighteen workflow groups use that Host or explicit custom Hosts.

Examples follow the [language specification](../docs/standard/v0.1/LANGUAGE_SPEC_en.md), include actual Python references and avoid undefined module imports. Parsing/end-to-end acceptance uses deterministic offline models. Execution contracts: [whitepaper](../docs/standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md); installation/CLI: [usage](../docs/development/USAGE_en.md); parser: [M1](../docs/development/M1_PARSER_en.md).

| Example | Behavior | Requirements |
| --- | --- | --- |
| [01 assistant](01-assistant/workflow_en.md) | Single Prompt, explicit end | Chat State/model |
| [02 chain](02-chain/workflow_en.md) | Two nodes retain history | Message merge/model |
| [03 list routing](03-routing-list/workflow_en.md) | Model text selects branch | Trimmed exact key |
| [04 table routing](04-routing-table/workflow_en.md) | Equivalent pipe-table form | Table parser |
| [05 Python router](05-python-router/workflow_en.md) | State update then router | Native Schema/python/model |
| [06 pyfunction](06-pyfunction/workflow_en.md) | Materials plus body invoke model | Material conversion/model |
| [07 custom State](07-custom-state/workflow_en.md) | Replace message merge | Native Schema/model |
| [08 native jump](08-native-jump/workflow_en.md) | Command goto plus Default | Command/message reducer |
| [09 State-only](09-state-only/workflow_en.md) | Calculation without messages | Schema/python, no model |
| [10 tools](10-tool-calling/workflow_en.md) | Explicit ToolNode loop | Custom Host/scripted model/actual add |
| [11 interrupt](11-interrupt/workflow_en.md) | Input pause/resumption | Host/checkpointer/model |
| [12 evidence](12-evidence-assistant/README_en.md) | Retrieval/citation checks | Tools/Python |
| [13 CSV](13-csv-auditor/README_en.md) | Metrics/report correction | pyfunction/Schema/router |
| [14 email](14-email-assistant/README_en.md) | Classification/approval/draft | Table/request_input/checkpointer |
| [15 review](15-parallel-code-review/README_en.md) | Three parallel perspectives | Native Builder/model |
| [16 digest](16-batch-digest/README_en.md) | Dynamic isolated tasks/sorted output | Command/Send/reducer/local worker |
| [17 memory](17-react-memory/README_en.md) | Multi-turn ReAct/compaction | Custom reducer/checkpointer/looping Host |
| [18 reducer lab](18-reducer-lab/README_en.md) | Version/dedup/set/reset merges | Annotated/Builder/Overwrite, no model |

## Expected behavior

01 calls the model once and saves its new AIMessage. 02 invokes Analyze then Report; Report sees initial input and Analyze output. Static node bodies are not saved as history.

03/04 select enough or insufficient. Test doubles verify each branch because real model decisions are nondeterministic. One successor is selected by exact trimmed response text; the original response is still reduced into history.

05 Inspect does not call a model. Nonempty messages set status=ready and append explanatory material; empty messages set missing. Router sees **merged** status and selects Report/RequestMaterial, each invoking once. Schema loads before building; Python returns new messages, not the whole history.

06 prepare(state) returns a string converted to HumanMessage. pyfunction combines it with body/history for one model invocation, then reduces material and answer into State. Body text is not saved. Conversion/order belong to executor implementation, not parser logic.

07 omits a messages reducer to select native replacement. After Analyze submits a message, Report sees only that message; default history is not restored.

08 native Command targets Extra while DSL Default targets Report. Both run Python and append messages without model calls; order is unspecified. Branch @End does not cancel other branches. Extra intentionally lies outside the table and is allowed, following [native static-edge/Command behavior](https://docs.langchain.com/oss/python/langgraph/graph-api#command).

09 starts with {"value":0,"events":[]}, increments to 1 then doubles to 2, merging incremented/doubled through operator.add. No messages/model are needed. Its custom Host runs directly; 01–07 need a configured model, 08 uses native APIs. See [execution acceptance](../docs/development/M3_M5_COMPLETION_en.md) and [native State](https://docs.langchain.com/oss/python/langgraph/graph-api#state).

Simple pyfunction material can be a string. For role/content/metadata control, return native messages:

```python
from langchain_core.messages import HumanMessage

def prepare(state):
    return HumanMessage(content="Record A: amount 12. Record B: amount 8.")
```

Message objects/lists preserve roles, metadata and order. Strings become HumanMessage. Ordinary dictionaries/data lists become JSON when serializable, otherwise strings; other objects become strings, all with HumanMessage role. role/content dictionaries are not automatically recognized as messages. These are material, not State-field updates. None/empty list adds nothing but still invokes; empty string produces an empty message.

11 request_input passes its text to native interrupt(), collects a Host reply, saves it as HumanMessage, and Report reads it. Nonrecommended missing-transition fixtures live in [language fixtures](../tests/fixtures/language/README_en.md), not beginner examples.

## Practical agents and advanced reducers

12–16 each provide --demo with scripted models and actual tools/state updates. Live mode uses environment/saved connections; --model, --input and per-example options are documented. support/practical_en.py is a CLI helper, not a DSL protocol. Patterns reference official [workflows](https://docs.langchain.com/oss/python/langgraph/workflows-agents), [email](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) and [data tools](https://docs.langchain.com/oss/python/langgraph/sql-agent); no search/mail/database accounts are required for demos. See [practical acceptance](../docs/development/PRACTICAL_AGENTS_ACCEPTANCE_en.md) for usage/quality limits.

17's separate looping Host leaves standard single-run behavior unchanged. 18 demonstrates pure-code concurrent merging. Their 20 tests and live three-turn memory run are in [reducer acceptance](../docs/development/ADVANCED_REDUCERS_ACCEPTANCE_en.md).

Use workflow_cn.md for Chinese, workflow_en.md for English. Unsuffixed originals remain compatibility entries. Tests and historical acceptance dates/counts retain their original scope; see the localization report for new verification.
