# Host interrupts and terminal editing acceptance

Date: 2026-10-09. The standard Host gained native interrupt support and editable input without DSL parser changes. prompt-toolkit 3.0.52 supplied editing; at this milestone it was included with runtime/chat/deepseek/mcp extras (later separated from runtime).

main compiles with InMemorySaver. Each run_chat creates a new thread_id, reads one initial input and runs until completion. Dynamic interrupt() displays a serializable prompt, collects string replies and sends an ID-to-reply mapping through Command(resume=...). The Host does not append HumanMessage automatically; the request_input executor does. Resumption continues the same execution and then exits.

PromptSession provides arrows, Delete, Home/End, Emacs bindings and process-local history. Ctrl+C exits 130; Ctrl+D on an empty line means EOF. EOF during an interrupt exits 1 without submitting an incomplete reply set; an intentional empty reply is valid. Pipes cannot automatically resume. Static breakpoints require a custom Host; durable recovery, typed forms and multiline editing were excluded.

## Verification

**180/180 tests passed**, including 26 Host tests. The eleventh example passed parsing/CLI. Tests cover repeated interrupts in one node with one subsequent model call, parallel ID matching, ToolNode interruptions retaining tool_call_id, EOF/empty/pipe behavior, new threads for separate runs and static-breakpoint rejection. A POSIX PTY ran the actual CLI: abXd, two left arrows, Delete, then c produced abcd at the next node and exited normally.

All tests were local and deterministic. The sandbox run encountered an existing async-thread shutdown hang; the unsandboxed run passed. An initial example-count assertion still expected 10; updating to 11 fixed it.

```bash
.venv/bin/sgraph examples/11-interrupt/workflow_en.md -- --model-factory python:../support/demo_model_en.py:create
```

Enter a request, then reply at Resume>; Report echoes it and exits without a key/network. For a real model omit the factory and configure SGRAPH_MODEL. Native nodes restart from the beginning on resumption, so pre-interrupt side effects must tolerate replay. See [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) and [prompt-toolkit editing](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html).

## request_input addition

The built-in `request_input:prompt text` replaced example 11's external Python reference. Its parameter is passed to interrupt; a leading double quote selects JSON string decoding, allowing escaped newlines/quotes on one physical setting line. Body text is ignored, no model is called, and string replies become HumanMessage updates for the reducer.

Seven test_request_input_en.py cases cover raw text, parser opacity, empty/invalid binding parameters, nonstring replies, async resumption, router access to merged replies and the messages-channel requirement. Final **187/187 passed**. The PTY now exercises request_input directly. No global interrupt envelope or mandatory Host protocol was added; custom Hosts retain native resumption APIs.
