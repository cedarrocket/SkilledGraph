# SkilledGraph v0.1 Standard Documents

Version: v0.1. Updated: 2026-10-17. Current implementation and verification boundaries are in [status](../../development/STATUS_en.md); installation and execution in [usage](../../development/USAGE_en.md).

## Documents and authority

| Document | Scope | Readers |
| --- | --- | --- |
| [Language specification](LANGUAGE_SPEC_en.md) | structure, syntax, extraction, control flow, diagnostics | users, parser authors, auditors |
| [Implementation whitepaper](IMPLEMENTATION_WHITEPAPER_en.md) | responsibilities, public API, native access, default policies | framework/Host developers |
| [Development guide](DEVELOPMENT_GUIDE_en.md) | organization, contribution checks, compatibility | contributors, maintainers |

Language rules come from the specification; interfaces/default policies from the whitepaper. Development guide introduces no language rules. Usage and reports reference standards rather than establish alternatives. Correct contradictions explicitly, not by old proposals or accidental implementation behavior.

Must/must not denotes contract; recommended denotes guidance; deferred/undefined is not implemented support. Tool, request_input, and monty extension sections are part of the current contract.

## Positioning

SkilledGraph is a personal scripting tool. Markdown holds instructions and explicit flow; external code handles computation; native LangGraph retains State, reducers, scheduling, and advanced capabilities. Independent [standard chat Host](../../../examples/chat-host/README_en.md) is ready to run; advanced users obtain native builders/graphs.

It is not a general Agent Framework, full LangGraph API mirror, independent type system, expression language, or scheduler. Skill-like readability is not an Agent Skills/SKILL.md compatibility promise.

## Minimal example

```markdown
# [Node] Assistant
Answer the user's question.

## [Transitions]
- @Default -> @End
```

First node is entry; declaration order creates no implicit edges. Without @uses use default Prompt. Host supplies model, initial input, and resources. Configure a model, save as hello.md, and run sgraph hello.md.

See [examples](../../../examples/README_en.md), [fixtures](../../../tests/fixtures/language/README_en.md), and [usage](../../development/USAGE_en.md).

## Change management

Changes to accepted inputs, interfaces, or observable behavior require matching standards/examples/tests and explicit compatibility notes. Default backend internals may evolve, but observable changes must still be recorded rather than hidden as implementation details.


Experimental `@trace` is part of this standard. See the language specification and implementation whitepaper. Tutorials are unchanged in this revision.


Subgraph file references and hierarchical traces are included in this standard revision. See the extension sections and [example 19](../../../examples/19-subgraphs/README_en.md).
