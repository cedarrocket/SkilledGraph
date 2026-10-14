# Standard chat Host separated from DSL core

Date: 2026-10-09. Organization, imports and packaging changed; semantics/default Host behavior did not.

- src/skilledgraph/: read-only parsing, GraphSpec, diagnostics, file binding, execution, native building and thin launcher.
- examples/chat-host/src/sgraph_chat_host/: standard chat Host, connections, setup, locales and terminal editing.
- examples/chat-host/host_en.py and workflow_en.md: explicit file Host example.
- sgraph_agent/: independent ongoing-session agent explicitly reusing Host configuration/terminal modules.

Core host, host_config, host_setup, host_locales and terminal modules were removed. The independent package is bundled for default usability, without a Host base class or new DSL settings.

Without @host, CLI lazily imports sgraph_chat_host.host.main. File references receive the absolute graph path and remaining arguments. --check parses only. parse/build/load never import the standard Host. Old skilledgraph.host*/terminal imports are removed; examples/tests/live runners use sgraph_chat_host. Existing graph commands, profile paths, environment variables, sessions, single execution and dynamic resumption remain compatible.

runtime no longer depends on prompt-toolkit; terminal-oriented extras retain it.

## Verification

52 Host/config/setup/boundary tests and **273 full tests passed**. Parser inventory included 18 workflow examples plus the new nineteenth standard Host example. Fresh-process tests blocked sgraph_chat_host imports while exercising parse/build/load/--check/custom Hosts. Host --help and explicit-file piped echo passed. Editable installation/wheel checks confirmed all new Host modules, absence of old core Host modules and packaged agent workflow. An extracted wheel tested default selection from /tmp using mocks, without API calls.

```bash
.venv/bin/python -m unittest discover -s tests -q
```

A sandbox async hang was stopped; outside-sandbox offline regression passed. Initial count 18 was updated to 19. No live model or MCP network tests were performed in this round.
