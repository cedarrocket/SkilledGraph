# M3–M5: Default Execution, Host, and Compatibility

> Non-normative historical report. Current scope and run commands: [status](STATUS_en.md), [usage](USAGE_en.md).

Date: 2026-10-09. Agreed v0.1 scope was completed; deferred features and uncovered environments remained. M1/M2 reports describe earlier stages.

## Modules

execution owns Prompt/pyfunction input, material conversion, updates and text routing; binding owns object loading; building selects schemas/binds native nodes/edges; historical host module handles model/factory/input/replies (now independent example); cli/__main__ read-only select Host, forward path/argv, and provide check/command entry.

Host supplies model; APIs do not inspect model environment or launch Host. No proprietary runtime, plugin base class, or DSL configuration expressions.

## Route transport decision

Conditional builtin Prompt/pyfunction without router trims current AI text, looks up key, and returns native Command(update=new messages, goto=target). Original reply remains; key is neither State nor inferred from reducer-transformed history.

Builder does not install a duplicate conditional edge and declares possible destinations for native validation/visualization. Explicit router still uses native post-merge conditional edges. User Command continues alongside DSL edges.

This is builtin code policy, not a new user result protocol. A custom binding called pyfunction is not automatically wrapped/invoked. Arbitrary results are not keys.

Verified redacting reducers still route on original replies, sync/async concurrency does not mix keys, and checkpoint resume retains selected path. No mutable shared route slot/private State field.

## Execution details

Optional SystemMessage(body), history, new material; commit only new material/reply. Empty body still invokes. None/empty list contributes nothing; native messages preserve metadata; strings become HumanMessage; dict/list becomes JSON or str; other values str. Body/history/other fields are not automatically submitted as updates.

Construction checks model/messages; execution checks list/tuple history and AIMessage result. RunnableConfig passes through. Sync does not secretly run an event loop; async material requires ainvoke; async model requires ainvoke. Sync material runs directly in async policy, so blocking users must offload or use async.

Schemas/reducers stay unchanged. Native execution errors propagate, invalid keys raise RoutingError. Failure before update does not guarantee saving material/reply or transactional side effects.

## Host/CLI contract at this stage

sgraph and python -m skilledgraph are available. --check precedes file; remainder goes to Host, optionally separated with --. Custom Host wins; launcher does not prebuild.

Historical basic Host selects --model/--model-factory or SGRAPH equivalents, uses init_chat_model and provider extras, delegates other options to factory/custom Host. Explicit factory invocation does not change @state object-loading contract.

At this stage interactive requests started fresh State from entry; pipe read all stdin. Every new AI update, including route keys, was displayed. No token UI; native streaming remained accessible. Pure code without AI produced no text; custom Host owns business output.

Initial Host interrupts required native API/custom Host, without implicit saver/thread. This historical policy was later extended; see current interrupt report. Business failure returns 1, Ctrl-C 130, integer Host result becomes exit code; Python launch retains exceptions.

## Acceptance and limits

137 passed: 79 parse,24 build,20 model,14 Host/CLI. Nine complete examples ran with deterministic models/code. Also tested message streams, async streams, tags/callbacks, config/runtime, native interruptions, concurrency, and CLI subprocesses.

Editable install, commands, pipe, custom State Host, wheel, and outside-repository API/CLI passed. Without runtime dependencies, 79 parser tests passed and 26 runtime tests/modules skipped. Versions: Python 3.14.4, markdown-it-py 3.0.0, LangGraph 1.2.14, langchain-core 1.6.9, optional LangChain 1.4.4. Direct pins are not a full transitive lock.

This stage did not verify Python 3.11–3.13/Windows/macOS, live providers/credentials, arbitrary plugins or all persistence combinations. No real model calls, costs, availability or quality claims.

Private native RunnableCallable/coercion/branch inference are upgrade-sensitive; routing uses public Command. Native scheduler was neither modified nor copied. Future work follows actual compatibility needs, not implicit authorization of deferred features.
