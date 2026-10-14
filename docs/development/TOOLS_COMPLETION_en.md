# Tool-calling Implementation and Acceptance

Date: 2026-10-09. Ordinary tools completed; MCP sessions/transports and multi-model selection were outside this round.

## Implementation

Language: [tool extension](../standard/v0.1/LANGUAGE_SPEC_en.md); execution/API: [whitepaper](../standard/v0.1/IMPLEMENTATION_WHITEPAPER_en.md).

Parser/spec support ToolNode, @tools, special conditions, literal fences and positions. tool_selection is runtime-independent; tool_execution/building bind supplied tools and native ToolNode, detect merged messages and attach prioritized conditional edges. Special-condition model nodes return updates without text-routing Command.

Existing binding signature is unchanged; compiler neither bind_tools nor opens MCP. [Workflow](../../examples/10-tool-calling/workflow_en.md) and [Host](../../examples/10-tool-calling/host_en.py) are complete.

## Acceptance

160 passed: original137 +6 parsing +17 runtime tests; ten complete examples.

Coverage: full sync loop, multiple calls, mixed async/sync tools, named/empty sets, unknown/duplicate tools, callable conversion, messages requirement, ignored body, signal-before-router, async router, ordinary-key-before-fallback, non-forgeable literal signal, no implicit edges, missing fallback, checkpoint/resume, native Command, python/pyfunction output, ToolNode router, post-reducer detection, no premature invocation/rebinding, and native unknown-call errors.

Minimal asyncio.to_thread hung at shutdown in the local sandbox after tools returned correctly. Authorized outside-sandbox tests completed; no product changes/skips hid it. Versions match M3–M5.

Live models, MCP adapters/services/lifetimes, platforms, and all advanced combinations were not yet verified. Interface compatibility is not integration acceptance.
